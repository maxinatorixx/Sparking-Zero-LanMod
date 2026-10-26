"""Opt-in real Docker TCP/UDP smoke; never launches the game."""
import json
import errno
import os
import queue
import socket
import subprocess
import time
import unittest
import uuid
from unittest import mock
from urllib.request import Request, urlopen

from lan_identity import translate_request
from szero_lan import LobbyClient
from test_native_sessions_v2 import data, member, request

# Exercise the exact supported minimum and punctuation through real MariaDB.
TEST_SECRETS = {"ARENA_ADMIN_TOKEN": "a!", "ARENA_DB_PASSWORD": "d!",
                "ARENA_DB_EDITOR_PASSWORD": "e!"}


def account_container_options():
    return ["--tmpfs", "/data:size=512m,uid=10001,gid=10001", "--tmpfs", "/logs:size=16m,uid=10001,gid=10001"] + [part for key, value in TEST_SECRETS.items() for part in ("-e", key + "=" + value)]


def unused_tcp_udp_port():
    # A free TCP ephemeral port can already be occupied by an unrelated UDP
    # socket. Retry selection, and close BOTH probes even on bind failure.
    # This checks availability; Docker publication still has its normal race.
    for _ in range(16):
        with socket.socket() as tcp, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            tcp.bind(("127.0.0.1", 0))
            port = tcp.getsockname()[1]
            try:
                udp.bind(("127.0.0.1", port))
            except OSError as error:
                if error.errno == errno.EADDRINUSE:
                    continue
                raise
            return port
    raise RuntimeError("Could not find an unused paired TCP/UDP test port")


class PortSelectionTests(unittest.TestCase):
    def test_occupied_udp_port_retries_and_closes_every_probe(self):
        probes = [mock.MagicMock() for _ in range(4)]
        for probe in probes:
            probe.__enter__.return_value = probe
        probes[0].getsockname.return_value = ("127.0.0.1", 12345)
        probes[1].bind.side_effect = OSError(errno.EADDRINUSE, "occupied UDP")
        probes[2].getsockname.return_value = ("127.0.0.1", 23456)
        with mock.patch.object(socket, "socket", side_effect=probes):
            self.assertEqual(unused_tcp_udp_port(), 23456)
        for probe in probes:
            probe.__exit__.assert_called_once()

    def test_other_bind_error_is_not_hidden(self):
        probes = [mock.MagicMock() for _ in range(2)]
        for probe in probes:
            probe.__enter__.return_value = probe
        probes[1].bind.side_effect = OSError(errno.EACCES, "denied")
        with mock.patch.object(socket, "socket", side_effect=probes):
            with self.assertRaises(OSError) as raised:
                unused_tcp_udp_port()
        self.assertEqual(raised.exception.errno, errno.EACCES)
        for probe in probes:
            probe.__exit__.assert_called_once()


@unittest.skipUnless(os.getenv("SZERO_DOCKER_TEST_IMAGE"), "Docker smoke image not selected")
class ContainerTests(unittest.TestCase):
    def test_nonroot_readonly_container_native_session_and_udp_relay(self):
        name="szero-smoke-"+uuid.uuid4().hex
        clients, games=[],[]
        port=unused_tcp_udp_port()
        started=False
        succeeded=False
        try:
            subprocess.run(["docker","run","--detach","--rm","--name",name,
                "--read-only","--cap-drop=ALL","--security-opt=no-new-privileges:true",
                "--tmpfs","/tmp:size=64m","-p",f"127.0.0.1:{port}:27150/tcp",
                "-p",f"127.0.0.1:{port}:27150/udp",*account_container_options(),os.environ["SZERO_DOCKER_TEST_IMAGE"]],
                check=True,capture_output=True,text=True,timeout=30)
            started=True
            deadline=time.monotonic()+65
            while True:
                try:
                    with socket.create_connection(("127.0.0.1",port),timeout=.5) as ready:
                        ready.sendall(b'{"op":"hello","version":2,"name":"Container readiness"}\n')
                        with ready.makefile("rb") as stream:
                            if json.loads(stream.readline()).get("event") != "welcome":
                                raise OSError("Docker proxy ready before application")
                        break
                except (OSError, ValueError):
                    if time.monotonic()>deadline:
                        self.fail("Container server did not start")
                    time.sleep(.1)
            for index in range(2):
                game=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
                game.bind(("127.0.0.1",0));game.settimeout(3);games.append(game)
                client=LobbyClient("127.0.0.1",port,"Docker fixture"+str(index),game_port=game.getsockname()[1])
                clients.append(client)
                self.assertTrue(client.connected.wait(5) and client.udp_ready.wait(5))
            clients[0].send("lan_backend_service",request={"request_id":"service-1","path":"/user/login.php","body":{}})
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                event=clients[0].events.get(timeout=5)
                if event.get("event")=="lan_backend_service":
                    self.assertEqual(event["state"],"ok")
                    self.assertEqual(event["body"]["res"],0)
                    self.assertIs(type(event["body"]["res"]),int)
                    self.assertTrue(event["body"]["session_code"].startswith("szlan-"))
                    break
            else:
                self.fail("No Docker backend response")
            def operation(client,payload):
                payload=translate_request(payload,client.client_id.hex())
                client.send("native_session",request=payload)
                deadline=time.monotonic()+5
                while time.monotonic()<deadline:
                    event=client.events.get(timeout=5)
                    if event.get("event") in ("native_session_result","native_session_error"):
                        self.assertEqual(event["event"],"native_session_result",event)
                        return event
                self.fail("No Docker session response")
            native=data("same")
            created=operation(clients[0],request("create",native_data=native,
                attributes={str(i):v for i,v in enumerate(native["numeric"])}))["session"]
            joined=operation(clients[1],request("join",session_id=created["session_id"],native_member=member("same")))["session"]
            self.assertEqual(len(joined["members"]),2)
            deadline=time.monotonic()+4
            while not all(c.assignment for c in clients) and time.monotonic()<deadline:
                time.sleep(.02)
            self.assertTrue(all(c.assignment for c in clients))
            for sender,receiver in ((0,1),(1,0)):
                payload=b"docker-lan-"+str(sender).encode()
                games[sender].sendto(payload,("127.0.0.1",clients[sender].proxy_port))
                self.assertEqual(games[receiver].recvfrom(100)[0],payload)
            identity=subprocess.run(["docker","exec",name,"id","-u"],check=True,capture_output=True,text=True)
            self.assertEqual(identity.stdout.strip(),"10001")
            succeeded=True
        finally:
            for client in clients:
                client.close()
            for game in games:
                game.close()
            if started:
                logs=subprocess.run(["docker","logs","--tail","20",name],capture_output=True,text=True,timeout=5)
                if not succeeded:
                    print(logs.stdout+logs.stderr)
                subprocess.run(["docker","stop","--time","2",name],capture_output=True,timeout=10)

    def test_mariadb_web_accounts_rank_persistence_and_admin_game_restart(self):
        name = "szero-account-smoke-" + uuid.uuid4().hex
        volume = name + "-data"
        game_port, web_port, db_port = unused_tcp_udp_port(), unused_tcp_udp_port(), unused_tcp_udp_port()
        started = False
        succeeded = False
        base = "http://127.0.0.1:" + str(web_port)

        def http(path, body=None, token=""):
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = "Bearer " + token
            req = Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
            with urlopen(req, timeout=5) as response:
                return json.load(response)

        def account(action, **fields):
            with socket.create_connection(("127.0.0.1", game_port), timeout=3) as connection:
                connection.settimeout(5)
                connection.sendall((json.dumps(dict(op="account", version=2, action=action, **fields))+"\n").encode())
                with connection.makefile("rb") as stream:
                    result = json.loads(stream.readline(65537))
                    self.assertEqual(stream.read(1), b"")
                    return result

        def native_profile(token, updates=()):
            # Exercise the actual authenticated game endpoint and backend
            # request path, including profile ownership and login/card reload.
            with socket.create_connection(("127.0.0.1", game_port), timeout=3) as connection:
                connection.settimeout(5)
                with connection.makefile("rb") as stream:
                    def send(value):
                        connection.sendall((json.dumps(value)+"\n").encode())
                    send(dict(op="hello", version=2, name="body-selected-name-ignored",
                              account_token=token))
                    welcome = json.loads(stream.readline(65537))
                    self.assertEqual(welcome["event"], "welcome")
                    self.assertTrue(welcome["account"]["authenticated"])
                    serial = 0
                    def service(path, body):
                        nonlocal serial
                        serial += 1
                        request_id = f"service-{serial}"
                        send(dict(op="lan_backend_service", request=dict(
                            request_id=request_id, path=path, body=body)))
                        for _ in range(20):
                            event = json.loads(stream.readline(65537))
                            if event.get("event") == "lan_backend_service" and event.get("request_id") == request_id:
                                self.assertEqual(event["state"], "ok")
                                self.assertEqual(event["body"]["res"], 0)
                                return event["body"]
                        self.fail("No native backend response on authenticated game port")
                    service("/user/login.php", {})
                    for path, body in updates:
                        service(path, body)
                    login = service("/user/login.php", {})
                    card = service("/user/get_player_card.php", {"target": "self"})
                    return login, card

        def ready():
            deadline = time.monotonic() + 65
            while True:
                try:
                    http("/api/status")
                    with socket.create_connection(("127.0.0.1", game_port), timeout=.5) as sock:
                        sock.sendall(b'{"op":"hello","version":2,"name":"readiness"}\n')
                        with sock.makefile("rb") as stream:
                            assert json.loads(stream.readline())["event"] == "welcome"
                    return
                except (OSError, ValueError, AssertionError):
                    if time.monotonic() > deadline:
                        raise AssertionError("Mono-container services failed readiness")
                    time.sleep(.2)

        def docker_python(source):
            return subprocess.run(["docker", "exec", name, "python", "-c", source], check=True, capture_output=True, text=True, timeout=15).stdout

        try:
            subprocess.run(["docker", "volume", "create", volume], check=True, capture_output=True, timeout=10)
            opts = [part for key, value in TEST_SECRETS.items() for part in ("-e", key+"="+value)]
            subprocess.run(["docker", "run", "--detach", "--name", name, "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges:true",
                "--tmpfs", "/tmp:size=64m", "--tmpfs", "/logs:size=16m,uid=10001,gid=10001", "-v", volume+":/data",
                "-p", f"127.0.0.1:{game_port}:27150/tcp", "-p", f"127.0.0.1:{web_port}:8080/tcp", "-p", f"127.0.0.1:{db_port}:3306/tcp",
                *opts, os.environ["SZERO_DOCKER_TEST_IMAGE"]], check=True, capture_output=True, timeout=30)
            started = True
            ready()
            self.assertTrue(http("/api/status")["setup_required"])
            admin = http("/api/register", {"username":"admin", "password":"fixture-password", "admin_token":TEST_SECRETS["ARENA_ADMIN_TOKEN"]})
            other = http("/api/register", {"username":"fighter", "password":"fixture-password"})
            http("/api/profile", {"display_name":"Capsule Champion", "avatar":"capsule", "banner":"blue"}, admin["token"])
            profile = http("/api/login", {"username":"admin", "password":"fixture-password"})["profile"]
            self.assertEqual(profile["display_name"], "Capsule Champion")
            game_login = account("login", username="admin", password="fixture-password")
            self.assertEqual(game_login["state"], "ok")
            self.assertEqual(game_login["profile"]["display_name"], "Capsule Champion")
            self.assertEqual(account("me", token=game_login["token"]), game_login)
            native_updates = (
                ("/user/update_player_rank.php", {"player_rank": 7}),
                ("/user/update_proficiency_rank.php", {
                    "character_id": "fixture-goku", "character_proficiency_rank": 3}),
            )
            native_login, native_card = native_profile(game_login["token"], native_updates)
            for card in (native_login["player_card"], native_card["player_card"]):
                self.assertEqual(card["player_rank"], 7)
                self.assertEqual(card["character_id"], "fixture-goku")
                self.assertEqual(card["character_proficiency_rank"], 3)
            other_native, other_card = native_profile(other["token"])
            self.assertEqual(other_native["player_card"]["player_rank"], 0)
            self.assertEqual(other_card["player_card"]["character_proficiency_rank"], 0)
            # Independent DB connection proves the endpoint committed to the
            # MariaDB table rather than merely holding a game-process cache.
            docker_python("from account_store import AccountStore; s=AccountStore.from_env(); assert s.get_native_state(1)=={'player_rank':7,'character_id':'fixture-goku','proficiency':{'fixture-goku':3}}; assert s.get_native_state(2)=={}; s.close()")
            self.assertEqual(http("/api/rankings?mode=dp")["rankings"][0]["rating"], 1000)
            self.assertTrue(http("/api/status")["ranking"]["automatic_result_sync"])
            docker_python("from account_store import AccountStore; s=AccountStore.from_env(); assert s.record_ranked_report('b'*32,1,2,0,2,2)=='pending'; assert s.record_ranked_report('b'*32,1,2,1,2,1)=='recorded'; assert s.record_ranked_report('b'*32,1,2,1,2,1)=='recorded'; r={x['id']:x for x in s.rankings('dp')}; assert r[1]['rating']==984 and r[1]['losses']==1; assert r[2]['rating']==1016 and r[2]['wins']==1; s.close()")

            # Trusted fixture invokes the server-only result service, never a
            # public player result endpoint. This tests persistence, not native
            # game-result capture or acceptance.
            docker_python("from account_store import AccountStore; s=AccountStore.from_env(); assert s.record_result('fixture-match','single',1,2,1); assert not s.record_result('fixture-match','single',1,2,1); s.close()")
            with socket.create_connection(("127.0.0.1", db_port), timeout=3) as db:
                self.assertEqual(db.recv(128)[4], 10)  # MariaDB protocol handshake through published port.
            docker_python("import os,pymysql; c=pymysql.connect(host='127.0.0.1',user='arena_editor',password=os.environ['ARENA_DB_EDITOR_PASSWORD'],database='arena'); q=c.cursor(); q.execute('SELECT COUNT(*) FROM accounts'); assert q.fetchone()[0]==2; c.close()")
            self.assertIn("log", http("/api/admin/logs", token=admin["token"]))
            before = docker_python("from pathlib import Path; print(sorted(str(p.name) for p in Path('/proc').iterdir() if p.name.isdigit() and (p/'cmdline').read_bytes().split(bytes([0]))[1:2]==[b'szero_lan.py']))")
            http("/api/admin/restart", {}, admin["token"])
            deadline = time.monotonic()+10
            while time.monotonic()<deadline:
                after = docker_python("from pathlib import Path; print(sorted(str(p.name) for p in Path('/proc').iterdir() if p.name.isdigit() and (p/'cmdline').read_bytes().split(bytes([0]))[1:2]==[b'szero_lan.py']))")
                if after != before and after.strip() != "[]":
                    break
                time.sleep(.2)
            self.assertNotEqual(before, after)
            ready()
            subprocess.run(["docker", "restart", "--time", "12", name], check=True, capture_output=True, timeout=30)
            ready()
            self.assertEqual(http("/api/me", token=admin["token"])["profile"]["display_name"], "Capsule Champion")
            ranks = http("/api/rankings?mode=single")["rankings"]
            self.assertEqual([r["rating"] for r in ranks], [1016,984])
            self.assertEqual([r["games"] for r in ranks], [1,1])
            self.assertEqual(http("/api/me", token=other["token"])["profile"]["username"], "fighter")
            restored_login = account("me", token=game_login["token"])
            self.assertEqual(restored_login["token"], game_login["token"])
            self.assertEqual(restored_login["profile"]["display_name"], "Capsule Champion")
            single = next(rank for rank in restored_login["profile"]["ranks"] if rank["mode"] == "single")
            self.assertEqual((single["rating"], single["games"]), (1016, 1))
            restored_native, restored_card = native_profile(game_login["token"])
            for current,old in ((restored_native['player_card'],native_login['player_card']),
                                (restored_card['player_card'],native_card['player_card'])):
                self.assertEqual({k:v for k,v in current.items() if k not in ('lan_rankings','match_result_list')},
                                 {k:v for k,v in old.items() if k not in ('lan_rankings','match_result_list')})
            native_rows=restored_card['player_card']['match_result_list']
            for period in (1,2):
                rows=[r for r in native_rows if r['type']==period]
                self.assertEqual((sum(r['match'] for r in rows),sum(r['win'] for r in rows)),(2,1))
            dp=http('/api/rankings?mode=dp')['rankings']
            self.assertEqual([r['rating'] for r in dp],[1016,984])
            self.assertEqual([r['games'] for r in dp],[1,1])
            docker_python("from account_store import AccountStore; s=AccountStore.from_env(); assert s.record_ranked_report('b'*32,1,2,0,2,2)=='recorded'; r={x['id']:x for x in s.rankings('dp')}; assert r[1]['games']==1 and r[1]['losses']==1 and r[2]['wins']==1; s.close()")
            other_native, other_card = native_profile(other["token"])
            self.assertEqual(other_native["player_card"]["player_rank"], 0)
            self.assertEqual(other_card["player_card"]["character_proficiency_rank"], 0)
            docker_python("from account_store import AccountStore; s=AccountStore.from_env(); assert s.get_native_state(1)=={'player_rank':7,'character_id':'fixture-goku','proficiency':{'fixture-goku':3}}; assert s.get_native_state(2)=={}; s.close()")
            succeeded = True
        finally:
            if started:
                if not succeeded:
                    logs = subprocess.run(["docker", "logs", "--tail", "50", name], capture_output=True, text=True, timeout=5)
                    print(logs.stdout+logs.stderr)
                subprocess.run(["docker", "stop", "--time", "10", name], capture_output=True, timeout=15)
                subprocess.run(["docker", "rm", name], capture_output=True, timeout=10)
            subprocess.run(["docker", "volume", "rm", volume], capture_output=True, timeout=10)
