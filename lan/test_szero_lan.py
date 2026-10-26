import asyncio
import json
from pathlib import Path
import queue
import socket
import tempfile
import threading
import time
import unittest

from szero_lan import (
    ACK, DATA, HEADER, MAGIC, MAX_PAYLOAD, REGISTER, ZERO,
    GameServer, LobbyClient, load_config, packet, unpack, write_runtime,
)


def until(predicate, seconds=3):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def event(client, name, seconds=3):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            value = client.events.get(timeout=0.1)
            if value["event"] == name:
                return value
        except queue.Empty:
            pass
    raise AssertionError(f"missing {name}")


class WireTests(unittest.TestCase):
    def test_bounds_and_malformed_frames(self):
        client = bytes(range(16))
        for payload in (b"", b"\x00\xff", b"x" * MAX_PAYLOAD):
            encoded = packet(DATA, client, ZERO, payload)
            self.assertEqual(unpack(encoded), (DATA, client.hex(), ZERO.hex(), payload))
            for broken in (encoded[:-1], encoded + b"x", encoded[:10]):
                self.assertIsNone(unpack(broken))
        self.assertIsNone(unpack(HEADER.pack(MAGIC, 99, client, ZERO, 0)))
        with self.assertRaises(ValueError):
            packet(DATA, client, ZERO, b"x" * (MAX_PAYLOAD + 1))

    def test_simple_config_and_atomic_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = Path(folder) / "client.json"
            cfg.write_text('{"server_host":"localhost"}', encoding="utf-8")
            self.assertEqual(load_config(cfg)["server_port"], 27150)
            cfg.write_text('{"server_host":"localhost","slot":0}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(cfg)
            path = Path(folder) / "lan_runtime.lua"
            write_runtime(path, None)
            self.assertIn("active=false", path.read_text())
            revision = write_runtime(path, dict(match_id="a" * 32, join_order=1, game_port=34500, proxy_port=34501))
            self.assertIn("join_order=1", path.read_text())
            self.assertIn('match_id="' + "a" * 32 + '"', path.read_text())
            self.assertIn(revision, path.read_text())
            with self.assertRaises(ValueError):
                write_runtime(path, dict(match_id='"; bad', join_order=1, game_port=34500, proxy_port=34501))
            self.assertNotIn("server_host", path.read_text())
            self.assertFalse(path.with_name(path.name + ".tmp").exists())

    def test_bind_requires_specific_lan_address(self):
        self.assertEqual(GameServer("0.0.0.0", 27150).host, "0.0.0.0")
        for host in ("224.0.0.1", "8.8.8.8"):
            with self.assertRaises(ValueError):
                GameServer(host, 27150)

    def test_adapter_status_is_bounded_and_correlated(self):
        with tempfile.TemporaryDirectory() as folder:
            client = LobbyClient.__new__(LobbyClient)
            client.runtime_path = Path(folder) / "lan_runtime_ab12.lua"
            client.runtime_revision = "current"
            client.assignment = {"match_id": "a" * 32}
            client.state_lock = threading.Lock()
            client.adapter_status = None
            client.events = queue.Queue(maxsize=128)
            client.stop = threading.Event()
            path = client.runtime_path.with_suffix(".status.json")
            report = dict(version=1, revision="stale", match_id="a" * 32,
                          stage="commands_issued", detail="Waiting for battle entry", world="Menu")
            for malformed in ('{', '[]', 'x' * 8193, json.dumps(report)):
                path.write_text(malformed)
                client.read_adapter_status()
                self.assertIsNone(client.adapter_status)
            report["revision"] = "current"
            path.write_text(json.dumps(report))
            client.read_adapter_status()
            self.assertEqual(client.adapter_status, report)
            self.assertEqual(client.events.get_nowait()["event"], "adapter_status")
            client.read_adapter_status()
            self.assertTrue(client.events.empty(), "unchanged report must not flood logs/UI")
            report["match_id"] = "b" * 32
            path.write_text(json.dumps(report))
            client.read_adapter_status()
            self.assertEqual(client.adapter_status["match_id"], "a" * 32)


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.clients, self.games = [], []
        self.started = threading.Event()
        self.error = None

        def run():
            asyncio.set_event_loop(self.loop)
            try:
                self.server = self.loop.run_until_complete(GameServer("127.0.0.1", 0).start())
            except BaseException as exc:
                self.error = exc
                self.started.set()
                return
            self.started.set()
            self.loop.run_forever()
            self.loop.close()

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        self.assertTrue(self.started.wait(3))
        if self.error:
            raise self.error

    def tearDown(self):
        for client in self.clients:
            client.close()
        for game in self.games:
            game.close()
        if not self.error:
            asyncio.run_coroutine_threadsafe(self.server.close(), self.loop).result(3)
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(3)
        self.assertFalse(self.thread.is_alive())

    def client(self, name, runtime_path=None):
        game = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        game.bind(("127.0.0.1", 0))
        game.settimeout(1)
        self.games.append(game)
        host = "localhost" if len(self.clients) % 2 == 0 else "127.0.0.1"
        client = LobbyClient(host, self.server.port, name, runtime_path=runtime_path,
                             game_port=game.getsockname()[1])
        self.clients.append(client)
        self.assertTrue(client.connected.wait(2))
        self.assertTrue(client.udp_ready.wait(2))
        return client, game

    def test_six_clients_two_simultaneous_matches_and_waiting_lobby(self):
        pairs = [self.client(f"Player {i}") for i in range(6)]
        for client, _ in pairs[:4]:
            client.send("queue")
        assignments = [event(client, "match_start") for client, _ in pairs[:4]]
        self.assertEqual(assignments[0]["match_id"], assignments[1]["match_id"])
        self.assertEqual(assignments[2]["match_id"], assignments[3]["match_id"])
        self.assertNotEqual(assignments[0]["match_id"], assignments[2]["match_id"])
        self.assertEqual({a["join_order"] for a in assignments[:2]}, {0, 1})
        self.assertEqual({a["join_order"] for a in assignments[2:]}, {0, 1})

        pairs[4][0].send("create", name="Next tournament table")
        self.assertTrue(until(lambda: pairs[4][0].state and pairs[4][0].state["lobby"]))
        room = pairs[4][0].state["lobby"]
        pairs[5][0].send("join", lobby_id=room)
        self.assertTrue(until(lambda: pairs[5][0].state and pairs[5][0].state["lobby"] == room))

        for sender, receiver in ((0, 1), (1, 0), (2, 3), (3, 2)):
            client, game = pairs[sender]
            for data in (b"", b"\x00\xffhello", bytes(range(256)), b"x" * MAX_PAYLOAD):
                game.sendto(data, client.local.getsockname())
                received, origin = pairs[receiver][1].recvfrom(65535)
                self.assertEqual(received, data)
                self.assertEqual(origin, pairs[receiver][0].local.getsockname())
        self.assertTrue(until(lambda: all(c.game_packets_sent == 4 and c.game_packets_received == 4
                                         for c, _ in pairs[:4])))

        # Frames containing another lobby's match ID must not reach that lobby.
        wrong = packet(DATA, pairs[0][0].client_id,
                       bytes.fromhex(assignments[2]["match_id"]), b"wrong-match")
        pairs[0][0].udp.send(wrong)
        pairs[2][1].settimeout(0.15)
        with self.assertRaises(socket.timeout):
            pairs[2][1].recvfrom(65535)

    def test_game_status_file_reaches_client_events_for_current_match(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = Path(folder) / "lan_runtime_a.lua"
            a, _ = self.client("Alice", runtime)
            b, _ = self.client("Bob")
            a.send("queue"); b.send("queue")
            match = event(a, "match_start")
            event(b, "match_start")
            report = dict(version=1, revision=a.runtime_revision, match_id=match["match_id"],
                          stage="commands_issued", detail="Waiting for battle entry", world="Menu")
            runtime.with_suffix(".status.json").write_text(json.dumps(report))
            self.assertEqual(event(a, "adapter_status")["match_id"], match["match_id"])
            self.assertIn(a.runtime_revision, runtime.read_text())
            a.send("finish")
            event(a, "match_end")
            self.assertTrue(until(lambda: a.adapter_status is None))
            a.read_adapter_status()
            self.assertIsNone(a.adapter_status, "old status must not reappear after match end")
            a.close()  # Close before TemporaryDirectory removes the runtime path.

    def test_wildcard_bind_accepts_loopback_client(self):
        server = asyncio.run_coroutine_threadsafe(GameServer("0.0.0.0", 0).start(), self.loop).result(3)
        try:
            client = LobbyClient("127.0.0.1", server.port, "Wildcard")
            self.clients.append(client)
            self.assertTrue(client.connected.wait(2))
            self.assertTrue(client.udp_ready.wait(2))
            self.assertEqual(server.host, "0.0.0.0")
            client.close()
        finally:
            asyncio.run_coroutine_threadsafe(server.close(), self.loop).result(3)

    def test_background_client_uses_game_config_and_game_commands(self):
        from ingame_client import GameBridge
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            runtime = root / "lan_runtime_unique.lua"
            (root / "SzeroLAN.json").write_text(json.dumps(dict(
                server_host="localhost", server_port=self.server.port, name="In-game player")))
            bridge = GameBridge(root, runtime)
            stop = threading.Event()
            thread = threading.Thread(target=bridge.run, args=(stop,), daemon=True)
            thread.start()
            try:
                self.assertTrue(until(lambda: bridge.client and bridge.client.connected.is_set()))
                self.assertTrue(until(lambda: bridge.ui_path.exists()))
                bridge.command_path.write_text(json.dumps(dict(serial=1, op="create")))
                self.assertTrue(until(lambda: bridge.client.state and bridge.client.state["lobby"]))
                room = bridge.client.state["lobby"]
                other, _ = self.client("Other")
                other.send("join", lobby_id=room)
                other.send("ready", value=True)
                bridge.command_path.write_text(json.dumps(dict(serial=2, op="ready", value=True)))
                self.assertTrue(until(lambda: bridge.client.assignment is not None))
                self.assertIn("match_id=", runtime.read_text())
                # Re-reading a command must not duplicate it.
                self.assertEqual(bridge.last_command, 2)
                self.assertEqual(bridge.client.name, "In-game player")
            finally:
                stop.set(); thread.join(7)
                self.assertFalse(thread.is_alive())

    def test_lobby_waiting_list_rotates_to_next_ready_pair(self):
        clients = [self.client(f"Participant {i}")[0] for i in range(4)]
        clients[0].send("create", name="Finals")
        self.assertTrue(until(lambda: clients[0].state and clients[0].state["lobby"]))
        room = clients[0].state["lobby"]
        for client in clients[1:]:
            client.send("join", lobby_id=room)
            self.assertTrue(until(lambda: client.state and client.state["lobby"] == room))
        for client in clients[:2]:
            client.send("ready", value=True)
        first = [event(c, "match_start") for c in clients[:2]]
        for client in clients[2:]:
            client.send("ready", value=True)
        self.assertTrue(until(lambda: clients[3].state and
                             sum(p["ready"] for l in clients[3].state["lobbies"]
                                 if l["id"] == room for p in l["players"]) == 2))
        clients[0].send("finish")
        second = [event(c, "match_start") for c in clients[2:]]
        self.assertNotEqual(first[0]["match_id"], second[0]["match_id"])
        self.assertEqual(second[0]["match_id"], second[1]["match_id"])
        self.assertTrue(until(lambda: clients[0].assignment is None))

    def test_disconnect_cancels_match_and_cleans_membership(self):
        a, _ = self.client("Alice")
        b, _ = self.client("Bob")
        a.send("queue")
        b.send("queue")
        event(a, "match_start")
        event(b, "match_start")
        a.close()
        event(b, "match_end")
        self.assertTrue(until(lambda: b.state and b.state["connected"] == 1
                             and b.assignment is None))
        b.send("leave")
        self.assertTrue(until(lambda: b.state and not b.state["lobbies"]))

    def test_unpaired_client_cannot_forward_game_packets(self):
        client, game = self.client("Unpaired")
        client.send("queue")
        self.assertTrue(until(lambda: client.state and client.state["queued"]))
        client.udp.send(packet(DATA, client.client_id, ZERO, b"unpaired"))
        game.settimeout(0.15)
        with self.assertRaises(socket.timeout):
            game.recvfrom(65535)
        client.send("leave")
        self.assertTrue(until(lambda: client.state and not client.state["queued"]))

    def test_malformed_control_requests_do_not_break_server(self):
        client, _ = self.client("Player")
        client.send("join", lobby_id=[])
        self.assertIn("lobby", event(client, "error")["message"])
        client.send("create", name="Valid lobby")
        self.assertTrue(until(lambda: client.state and client.state["lobby"]))
        client.send("ready", value="yes")
        self.assertIn("true or false", event(client, "error")["message"])
        client.send("list")
        self.assertEqual(event(client, "state")["connected"], 1)


if __name__ == "__main__":
    unittest.main()
