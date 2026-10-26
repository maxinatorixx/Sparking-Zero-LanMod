"""Explicit LAN principal mapping: no game calls or platform account mutation."""
import copy
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest

from ingame_client import GameBridge
from lan_identity import LAN_PROTOCOL, principal, translate_request, validate_peer_request
from native_search import NativeSearchRPC, parse_session_command, SESSION_PARTITION
from native_sessions import NativeSessionDirectory
import test_native_session_bridge as fixture
import test_native_session_transport as transport_fixture
from test_native_sessions_v2 import A, B, create, data, member, request

CAPS = {"native_lan_identity": 1}
CREATE = b"CREATE3 1 42 2 -1 7 2 0 1 3 0 3 616263 61 62 3132372e302e302e313a34303030 0 0 0 0\n"


class LANIdentityTests(unittest.TestCase):
    def test_translation_owned_copy_preserves_secondary_and_classic_partition(self):
        parsed = parse_session_command(CREATE)["request"]
        original = copy.deepcopy(parsed)
        translated = translate_request(parsed, A)
        self.assertEqual(parsed, original)
        self.assertEqual(SESSION_PARTITION["protocol"], 3)
        self.assertEqual(translated["partition"]["protocol"], LAN_PROTOCOL)
        self.assertEqual(translated["native_data"]["member"]["identity_hex"], [principal(A).hex(), "62"])
        update = parse_session_command(CREATE.replace(b"CREATE3", b"UPDATESETTINGS3").replace(b" 0 0 0 0\n", b" 0 0 0\n"))["request"]
        mapped = translate_request(update, B)
        self.assertEqual(mapped["native_member"]["identity_hex"], mapped["native_data"]["member"]["identity_hex"])

    def test_server_peer_binding_spoof_and_namespace_mixing(self):
        directory = NativeSessionDirectory()
        native = data()
        classic = request("create", native_data=native, attributes={str(i): v for i, v in enumerate(native["numeric"])})
        validate_peer_request(directory, A, classic)
        mapped = translate_request(classic, A)
        validate_peer_request(directory, A, mapped)
        with self.assertRaisesRegex(ValueError, "this connection"):
            validate_peer_request(directory, B, mapped)
        wrong_partition = copy.deepcopy(mapped);wrong_partition["partition"]["protocol"] = 3
        with self.assertRaisesRegex(ValueError, "namespace"):
            validate_peer_request(directory, A, wrong_partition)
        wrong_identity = copy.deepcopy(mapped);wrong_identity["native_data"]["member"] = member("classic")
        with self.assertRaisesRegex(ValueError, "namespace"):
            validate_peer_request(directory, A, wrong_identity)

    def test_hello4_requires_binding_capability_and_pins_process(self):
        with tempfile.TemporaryDirectory() as folder:
            rpc = NativeSearchRPC(Path(folder) / "runtime.lua", A)
            rpc.transport_ports = (31001, 31002)
            try:
                def hello():
                    sock = socket.create_connection(("127.0.0.1", rpc.port), timeout=2)
                    sock.sendall(f"HELLO4 {A}\n".encode())
                    value = sock.makefile("rb").readline()
                    sock.close()
                    return value
                self.assertEqual(hello(), b"UNAVAILABLE4\n")
                self.assertTrue(rpc.bind_lan_identity(B, CAPS))
                rpc.transport_ports = (31001, 31001)
                self.assertEqual(hello(), b"UNAVAILABLE4\n")
                self.assertFalse(rpc.lan_session_mode)
                rpc.transport_ports = (31001, 31002)
                self.assertEqual(hello(), f"READY4 31001 31002 szlan:{B}\n".encode())
                self.assertFalse(rpc.bind_lan_identity(A, CAPS))
                self.assertEqual(hello(), b"UNAVAILABLE4\n")
            finally:
                rpc.close()

    def test_bootstrap_retry_before_binding_and_disconnect_after_binding(self):
        with tempfile.TemporaryDirectory() as folder:
            rpc = NativeSearchRPC(Path(folder) / "runtime.lua", A)
            try:
                self.assertFalse(rpc.bind_lan_identity(B, {}))
                bridge = GameBridge.__new__(GameBridge)
                bridge.native_rpc, bridge.native_pending, bridge.native_session_pending = rpc, set(), {}
                bridge.native_disconnect()  # Startup connection failure before welcome.
                self.assertFalse(rpc.lan_invalid)
                self.assertTrue(rpc.bind_lan_identity(B, CAPS))
            finally:
                rpc.close()
            rpc = NativeSearchRPC(Path(folder) / "runtime2.lua", A)
            try:
                self.assertTrue(rpc.bind_lan_identity(B, CAPS))
                rpc.invalidate_lan_identity()
                self.assertFalse(rpc.bind_lan_identity(B, CAPS))
                self.assertIsNone(rpc._lan_identity())
            finally:
                rpc.close()


class LANBridgeTests(unittest.TestCase):
    setUp = fixture.NativeSessionBridgeTests.setUp
    tearDown = fixture.NativeSessionBridgeTests.tearDown

    def bridge4(self, identity):
        root = Path(self.folder.name) / identity
        root.mkdir()
        (root / "SzeroLAN.json").write_text(json.dumps({"server_host": "127.0.0.1",
            "server_port": self.server.port, "name": identity, "native_search": True}))
        bridge = GameBridge(root, root / f"lan_runtime_{identity*32}.lua")
        stop = threading.Event()
        thread = threading.Thread(target=bridge.run, args=(stop,), daemon=True)
        thread.start()
        self.bridges.append((bridge, stop, thread))
        self.assertTrue(fixture.until(lambda: bridge.native_session_capability))
        sock = socket.create_connection(("127.0.0.1", bridge.native_rpc.port), timeout=5)
        reader = sock.makefile("rb")
        self.connections.append((sock, reader))
        sock.sendall(f"HELLO4 {identity*32}\n".encode())
        ready = reader.readline().split()
        self.assertEqual(ready[:3], [b"READY4", str(bridge.client.game_port).encode(), str(bridge.client.proxy_port).encode()])
        self.assertEqual(ready[3], bridge.native_rpc._lan_identity())
        return bridge, sock, reader

    def test_same_platform_identity_distinct_lan_principals_create_search_join_and_poll(self):
        a, sa, ra = self.bridge4("a")
        b, sb, rb = self.bridge4("b")
        self.assertNotEqual(a.native_rpc._lan_identity(), b.native_rpc._lan_identity())
        sa.sendall(CREATE)
        self.assertEqual(ra.readline(), b"RESULT3 1 PREPARED\n")
        first = ra.readline();sid = first.split()[1]
        sa.sendall(b"ACK3 1\n")
        self.assertEqual(ra.readline(), b"RESULT3 1 COMMITTED\n")
        sb.sendall(b"SEARCH3 1 0 42 0 0 0 0 0 255\n")
        self.assertEqual(rb.readline(), b"RESULT3 1 OK\n")
        found = rb.readline()
        own_a, own_b = a.native_rpc._lan_identity().hex().encode(), b.native_rpc._lan_identity().hex().encode()
        self.assertIn(own_a, found)
        self.assertNotIn(own_b, found)
        sb.sendall(b"JOIN3 2 " + sid + b" 61 62 3132372e302e302e313a34303031 0 0 0\n")
        self.assertEqual(rb.readline(), b"RESULT3 2 PREPARED\n")
        joined = rb.readline()
        self.assertIn(own_a, joined);self.assertIn(own_b, joined)
        sb.sendall(b"ACK3 2\n")
        self.assertEqual(rb.readline(), b"RESULT3 2 COMMITTED\n")
        self.assertTrue(fixture.until(lambda: a.native_rpc.session_snapshot and own_b in a.native_rpc.session_snapshot))
        sa.sendall(b"POLL3 2\n")
        self.assertEqual(ra.readline(), b"RESULT3 2 OK\n")
        snapshot = ra.readline()
        self.assertIn(own_a, snapshot);self.assertIn(own_b, snapshot)
        live = next(iter(self.server.native_sessions.sessions.values()))
        identities = [m["identity_hex"] for m in live.native_members.values()]
        self.assertEqual({pair[1] for pair in identities}, {"62"})
        self.assertEqual(len({pair[0] for pair in identities}), 2)
        self.assertEqual(live.partition[1], LAN_PROTOCOL)
        self.assertFalse(self.server.matches)

    def test_lan_prepare_cancel_routes_abort_and_reconnect_refuses_binding_swap(self):
        bridge, sock, reader = self.bridge4("a")
        sock.sendall(CREATE)
        self.assertEqual(reader.readline(), b"RESULT3 1 PREPARED\n")
        reader.readline()
        sock.sendall(b"CANCEL3 1\n")
        self.assertEqual(reader.readline(), b"RESULT3 1 CANCELLED\n")
        self.assertFalse(self.server.native_sessions.sessions)
        old = bridge.client
        old.close()
        self.assertTrue(fixture.until(lambda: bridge.client is not None and bridge.client is not old
            and bridge.client.connected.is_set()))
        self.assertTrue(bridge.native_rpc.lan_invalid)
        self.assertIsNone(bridge.native_rpc._lan_identity())

    def test_server_tcp_rejects_spoof_without_identity_payload_logs_and_classic_isolation(self):
        sock = socket.create_connection(("127.0.0.1", self.server.port), timeout=5)
        reader = sock.makefile("rb")
        self.connections.append((sock, reader))
        def operation(message, expected):
            sock.sendall((json.dumps(message) + "\n").encode())
            for _ in range(64):
                value = json.loads(reader.readline())
                if value["event"] == expected:
                    return value
            self.fail("missing server reply")
        welcome = operation({"op": "hello", "version": 2, "name": "WirePeer"}, "welcome")
        self.assertEqual(welcome["capabilities"]["native_lan_identity"], 1)
        native = data("private-platform-primary")
        original = request("create", native_data=native,
            attributes={str(i): v for i, v in enumerate(native["numeric"])})
        spoof = translate_request(original, A)
        self.assertNotEqual(welcome["client_id"], A)
        with self.assertLogs("szero_lan", level="INFO") as logs:
            error = operation({"op": "native_session", "request": spoof}, "native_session_error")
            self.assertIn("this connection", error["message"])
            created = operation({"op": "native_session", "request": original}, "native_session_result")
        self.assertEqual(len(self.server.native_sessions.sessions), 1)
        text = "\n".join(logs.output)
        self.assertNotIn("private-platform-primary", text)
        self.assertNotIn("private-platform-primary".encode().hex(), text)
        self.assertNotIn("szlan:", text)
        b, sb, rb = self.bridge4("b")
        sb.sendall(b"SEARCH3 1 0 1234 0 0 0 0 0 255\n")
        self.assertEqual(rb.readline(), b"RESULT3 1 EMPTY\n")
        self.assertIn(created["session"]["session_id"], self.server.native_sessions.sessions)


class LANTransportTests(unittest.TestCase):
    setUp = transport_fixture.NativeSessionTransportTests.setUp
    tearDown = transport_fixture.NativeSessionTransportTests.tearDown
    connect = transport_fixture.NativeSessionTransportTests.connect

    def operation(self, client, operation, **fields):
        payload = translate_request(request(operation, **fields), client.client_id.hex())
        client.send("native_session", request=payload)
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            event = client.events.get(timeout=4)
            if event.get("event") in ("native_session_result", "native_session_error"):
                self.assertEqual(event["event"], "native_session_result", event)
                self.assertEqual(event["request_id"], payload["request_id"])
                return event
        self.fail("missing LAN session result")

    def test_four_clients_two_lan_sessions_bidirectional_udp_isolation(self):
        pairs = [self.connect("LAN-" + str(i)) for i in range(4)]
        clients = [pair[0] for pair in pairs]
        # Every client starts from the SAME platform primary and persona.
        original = data("identical-platform-primary-and-persona")
        native = copy.deepcopy(original)
        session_ids = []
        for index in (0, 2):
            session = self.operation(clients[index], "create", native_data=native,
                attributes={str(i): value for i, value in enumerate(native["numeric"])})["session"]
            session_ids.append(session["session_id"])
        for guest, sid in ((1, session_ids[0]), (3, session_ids[1])):
            self.operation(clients[guest], "join", session_id=sid, native_member=native["member"])
        self.assertEqual(native, original)
        self.assertEqual(len(set(session_ids)), 2)
        self.assertEqual(len(self.server.native_sessions.sessions), 2)
        primaries = []
        for session in self.server.native_sessions.sessions.values():
            self.assertEqual(len(session.members), 2)
            self.assertEqual(session.partition[1], LAN_PROTOCOL)
            for owner, entry in session.native_members.items():
                self.assertEqual(entry["identity_hex"][0], principal(owner).hex())
                self.assertEqual(entry["identity_hex"][1], original["member"]["identity_hex"][1])
                primaries.append(entry["identity_hex"][0])
        self.assertEqual(len(set(primaries)), 4)
        for client in clients:
            self.assertTrue(transport_fixture.until(lambda: client.assignment and client.assignment.get("native")))
        for sender, receiver, payload in ((0, 1, b"LAN-pair1-forward"), (1, 0, b"LAN-pair1-backward"),
                                          (2, 3, b"LAN-pair2-forward"), (3, 2, b"LAN-pair2-backward")):
            client, game = pairs[sender]
            game.sendto(payload, ("127.0.0.1", client.proxy_port))
            received, source = pairs[receiver][1].recvfrom(256)
            self.assertEqual(received, payload)
            self.assertEqual(source[1], pairs[receiver][0].proxy_port)
            # The sender and both unrelated-session clients receive nothing.
            for unrelated in range(4):
                if unrelated != receiver:
                    with self.assertRaises(socket.timeout):
                        pairs[unrelated][1].recvfrom(256)
        self.assertFalse(self.server.matches)
        self.assertFalse(self.server.waiting)


if __name__ == "__main__":
    unittest.main()
