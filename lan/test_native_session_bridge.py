"""Actual helper IPC -> GameBridge -> TCP directory, without launching game."""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
import unittest

from ingame_client import GameBridge
from szero_lan import GameServer
from setup_launcher import probe_native_server


def until(predicate):
    deadline = time.monotonic()+5
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.01)
    return False


class NativeSessionBridgeTests(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.ready = threading.Event()
        self.failure = None
        def run():
            asyncio.set_event_loop(self.loop)
            try:
                self.server = self.loop.run_until_complete(GameServer("127.0.0.1", 0).start())
            except BaseException as exc:
                self.failure = exc
            self.ready.set()
            if self.failure is None:
                self.loop.run_forever()
            self.loop.close()
        self.server_thread = threading.Thread(target=run, daemon=True)
        self.server_thread.start()
        self.assertTrue(self.ready.wait(5))
        if self.failure:
            raise self.failure
        self.folder = tempfile.TemporaryDirectory()
        self.bridges, self.connections = [], []

    def tearDown(self):
        for sock, reader in self.connections:
            reader.close()
            sock.close()
        for bridge, stop, thread in self.bridges:
            stop.set()
            thread.join(5)
            self.assertFalse(thread.is_alive())
        asyncio.run_coroutine_threadsafe(self.server.close(), self.loop).result(5)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.server_thread.join(5)
        self.folder.cleanup()

    def bridge(self, identity):
        root = Path(self.folder.name)/identity
        root.mkdir()
        (root/"SzeroLAN.json").write_text(json.dumps({"server_host": "127.0.0.1",
            "server_port": self.server.port, "name": identity, "native_search": True}))
        bridge = GameBridge(root, root/f"lan_runtime_{identity*32}.lua")
        stop = threading.Event()
        thread = threading.Thread(target=bridge.run, args=(stop,), daemon=True)
        thread.start()
        self.bridges.append((bridge, stop, thread))
        self.assertTrue(until(lambda: bridge.native_session_capability))
        sock = socket.create_connection(("127.0.0.1", bridge.native_rpc.port), timeout=5)
        reader = sock.makefile("rb")
        self.connections.append((sock, reader))
        sock.sendall(f"HELLO3 {identity*32}\n".encode())
        self.assertEqual(reader.readline(), f"READY3 {bridge.client.game_port} {bridge.client.proxy_port}\n".encode())
        return bridge, sock, reader

    def test_native_query_create_join_refresh_and_leave_complete_bridge_path(self):
        a, sa, ra = self.bridge("a")
        b, sb, rb = self.bridge("b")
        sa.sendall(b"CREATE3 1 42 2 -1 7 2 0 1 3 0 3 616263 61 62 3132372e302e302e313a34303030 0 0 0 0\n")
        self.assertEqual(ra.readline(), b"RESULT3 1 PREPARED\n")
        descriptor = ra.readline()
        sid = descriptor.split()[1]
        self.assertEqual(self.server.native_sessions.sessions, {})
        sa.sendall(b"ACK3 1\n")
        self.assertEqual(ra.readline(), b"RESULT3 1 COMMITTED\n")
        self.assertTrue(until(lambda: len(self.server.native_sessions.sessions) == 1))
        sb.sendall(b"SEARCH3 1 0 42 0 0 0 0 0 255\n")
        self.assertEqual(rb.readline(), b"RESULT3 1 OK\n")
        self.assertEqual(rb.readline().split()[1], sid)
        sb.sendall(b"JOIN3 2 "+sid+b" 63 64 3132372e302e302e313a34303031 0 0 0\n")
        self.assertEqual(rb.readline(), b"RESULT3 2 PREPARED\n")
        joined = rb.readline()
        self.assertIn(f"127.0.0.1:{b.client.game_port}".encode().hex().encode(), joined)
        self.assertIn(f"127.0.0.1:{b.client.proxy_port}".encode().hex().encode(), joined)
        sb.sendall(b"ACK3 2\n")
        self.assertEqual(rb.readline(), b"RESULT3 2 COMMITTED\n")
        self.assertTrue(until(lambda: a.native_rpc.session_snapshot and
                             a.native_rpc.session_snapshot.count(b" 61 62 ") == 1 and
                             b" 63 64 " in a.native_rpc.session_snapshot))
        sa.sendall(b"POLL3 2\n")
        self.assertEqual(ra.readline(), b"RESULT3 2 OK\n")
        refreshed = ra.readline()
        self.assertIn(b" 61 62 ", refreshed)
        self.assertIn(b" 63 64 ", refreshed)
        self.assertIn(f"127.0.0.1:{a.client.game_port}".encode().hex().encode(), refreshed)
        self.assertIn(f"127.0.0.1:{a.client.proxy_port}".encode().hex().encode(), refreshed)
        self.assertFalse(self.server.native_search.pending)
        self.assertFalse(self.server.matches)
        sb.sendall(b"LEAVE3 3\n")
        self.assertEqual(rb.readline(), b"RESULT3 3 OK\n")
        self.assertTrue(until(lambda: len(next(iter(self.server.native_sessions.sessions.values())).members) == 1))
        sa.sendall(b"LEAVE3 3\n")
        self.assertEqual(ra.readline(), b"RESULT3 3 OK\n")
        self.assertTrue(until(lambda: not self.server.native_sessions.sessions))

    def test_reconnect_preserves_both_native_local_ports(self):
        bridge, _, _ = self.bridge("a")
        old = bridge.client
        ports = old.game_port, old.proxy_port
        old.close()
        self.assertTrue(until(lambda: bridge.client is not None and bridge.client is not old
                             and bridge.client.connected.is_set() and bridge.native_session_capability))
        self.assertEqual((bridge.client.game_port, bridge.client.proxy_port), ports)
        self.assertEqual(bridge.native_rpc.transport_ports, ports)

    def test_native_launcher_server_capability_preflight(self):
        probe_native_server({"server_host": "127.0.0.1", "server_port": self.server.port})

    @unittest.skipUnless(os.environ.get("SZERO_SESSION_V3_IPC_EXE"), "compiled session-v3 fixture not selected")
    def test_actual_compiled_native_worker_ownership_and_cancellation(self):
        self.assertTrue(os.environ.get("WINEPREFIX"), "select a disposable Wine test prefix")
        for identity, mode in zip("abcd", ("create", "cancel", "cancel-stage", "search")):
            with self.subTest(mode=mode):
                bridge, sock, reader = self.bridge(identity)
                # The compiled production worker opens its own IPC connection.
                # Release the setup connection first; success close must NOT
                # revoke another native operation or a committed membership.
                reader.close()
                sock.close()
                self.connections.remove((sock, reader))
                endpoint = "Z:"+str(bridge.native_rpc.endpoint).replace("/", "\\")
                result = subprocess.run(["wine", os.environ["SZERO_SESSION_V3_IPC_EXE"],
                    endpoint, identity*32, mode], capture_output=True, text=True, timeout=40)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertIn("V3 fixture mode="+mode, result.stdout)
                owner = bridge.client.client_id.hex()
                if mode == "create":
                    self.assertIn("cache=1", result.stdout)
                    self.assertTrue(self.server.native_sessions.has_membership(owner))
                else:
                    self.assertIn("cache=0", result.stdout)
                    self.assertTrue(until(lambda: not self.server.native_sessions.has_membership(owner)))
                self.assertFalse(self.server.native_search.pending)
                self.assertFalse(self.server.matches)

    @unittest.skipUnless(os.environ.get("SZERO_SESSION_V3_IPC_EXE"), "compiled session-v3 fixture not selected")
    def test_compiled_quickmatch_search_then_create_or_join_same_session(self):
        """Actual C handoff/worker, synthetic native factory and title decision."""
        owners = []
        for identity, action in (("7", "create"), ("8", "join")):
            bridge, sock, reader = self.bridge(identity)
            reader.close()
            sock.close()
            self.connections.remove((sock, reader))
            endpoint = "Z:" + str(bridge.native_rpc.endpoint).replace("/", "\\")
            with self.assertLogs("szero_lan", level="INFO") as captured:
                result = subprocess.run(["wine", os.environ["SZERO_SESSION_V3_IPC_EXE"],
                    endpoint, identity*32, "quickmatch"], capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertIn(f"V3 quickmatch action={action} search_count={int(action == 'join')}", result.stdout)
            owners.append(bridge.client.client_id.hex())
            self.assertTrue(any(f"action={action}" in line and "state=committed" in line
                                for line in captured.output))
        session_id = self.server.native_sessions.memberships[owners[0]]
        self.assertEqual(self.server.native_sessions.memberships[owners[1]], session_id)
        self.assertEqual(len(self.server.native_sessions.sessions), 1)
        self.assertEqual(len(self.server.native_sessions.sessions[session_id].members), 2)
        self.assertFalse(self.server.matches)  # Not an actual game or combat test.

    @unittest.skipUnless(os.environ.get("SZERO_SESSION_V3_IPC_EXE"), "compiled session-v3 fixture not selected")
    def test_compiled_lan_quickmatch_same_native_identity_isolated_local_views(self):
        """HELLO4 and actual C projection; native factory/title remain synthetic."""
        owners = []
        committed_id = None
        for identity, action in (("5", "create"), ("6", "join")):
            bridge, sock, reader = self.bridge(identity)
            reader.close()
            sock.close()
            self.connections.remove((sock, reader))
            endpoint = "Z:" + str(bridge.native_rpc.endpoint).replace("/", "\\")
            result = subprocess.run(["wine", os.environ["SZERO_SESSION_V3_IPC_EXE"],
                endpoint, identity*32, "quickmatch-lan"], capture_output=True,
                text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertIn(f"V3 quickmatch action={action} search_count={int(action == 'join')}", result.stdout)
            owner = bridge.client.client_id.hex()
            owners.append(owner)
            session_id = self.server.native_sessions.memberships[owner]
            if committed_id is None:
                committed_id = session_id
            self.assertEqual(session_id, committed_id)
            self.assertIn(f"V3 LAN session={session_id} own=1", result.stdout)
            if action == "join":
                self.assertIn("peer=1 copy=0 self=0", result.stdout)
                self.assertIn("V3 native join flags=40 code=0", result.stdout)
        self.assertEqual(len(self.server.native_sessions.sessions), 1)
        session = self.server.native_sessions.sessions[committed_id]
        self.assertEqual(len(session.members), 2)
        principals = [member["identity_hex"][0]
                      for member in session.native_members.values()]
        self.assertEqual(len(set(principals)), 2)
        self.assertTrue(all(bytes.fromhex(value).startswith(b"szlan:") for value in principals))
        self.assertFalse(self.server.matches)

    @unittest.skipUnless(os.environ.get("SZERO_SESSION_V3_IPC_EXE"), "compiled session-v3 fixture not selected")
    def test_borrowed_view_create_empty_and_payload_reach_native_cache(self):
        """Observed40B view -> actual C capture -> TCP -> synthetic native cache."""
        for mode, identity in (("create-view-empty", "a"), ("create-view", "b")):
            with self.subTest(mode=mode):
                bridge, sock, reader = self.bridge(identity)
                reader.close(); sock.close()
                self.connections.remove((sock, reader))
                endpoint = "Z:"+str(bridge.native_rpc.endpoint).replace("/", "\\")
                result = subprocess.run(["wine", os.environ["SZERO_SESSION_V3_IPC_EXE"],
                    endpoint, identity*32, mode], capture_output=True, text=True, timeout=40)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertIn(f"V3 fixture mode={mode} cache=1", result.stdout)
                self.assertIsNotNone(self.server.native_sessions.describe_membership(bridge.client.client_id.hex()))
                self.assertFalse(self.server.matches)

    @unittest.skipUnless(os.environ.get("SZERO_SESSION_V3_IPC_EXE"), "compiled session-v3 fixture not selected")
    def test_inline64_room_stream_reaches_native_cache(self):
        self.assertTrue(os.environ.get("WINEPREFIX"), "select a disposable Wine test prefix")
        bridge, sock, reader = self.bridge("8")
        reader.close()
        sock.close()
        self.connections.remove((sock, reader))
        endpoint = "Z:"+str(bridge.native_rpc.endpoint).replace("/", "\\")
        result = subprocess.run(["wine", os.environ["SZERO_SESSION_V3_IPC_EXE"],
            endpoint, "8"*32, "create-inline64"], capture_output=True, text=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn("V3 fixture mode=create-inline64 cache=1", result.stdout)
        membership = self.server.native_sessions.describe_membership(bridge.client.client_id.hex())
        self.assertIsNotNone(membership)
        self.assertFalse(self.server.matches)  # Synthetic cache handoff, not gameplay.

    @unittest.skipUnless(os.environ.get("SZERO_SESSION_V3_IPC_EXE"), "compiled session-v3 fixture not selected")
    def test_observed_quickmatch_embedded_stream_reaches_native_cache(self):
        self.assertTrue(os.environ.get("WINEPREFIX"), "select a disposable Wine test prefix")
        bridge, sock, reader = self.bridge("9")
        reader.close()
        sock.close()
        self.connections.remove((sock, reader))
        endpoint = "Z:"+str(bridge.native_rpc.endpoint).replace("/", "\\")
        result = subprocess.run(["wine", os.environ["SZERO_SESSION_V3_IPC_EXE"],
            endpoint, "9"*32, "create-embedded"], capture_output=True, text=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn("V3 fixture mode=create-embedded cache=1", result.stdout)
        self.assertTrue(self.server.native_sessions.has_membership(bridge.client.client_id.hex()))
        self.assertFalse(self.server.matches)  # Cache handoff is not a battle.

    @unittest.skipUnless(os.environ.get("SZERO_SESSION_V3_IPC_EXE"), "compiled session-v3 fixture not selected")
    def test_compiled_join_match_and_invalid_native_ownership_fail_stop(self):
        self.assertTrue(os.environ.get("WINEPREFIX"), "select a disposable Wine test prefix")
        first_session = None
        for identity, mode in zip("abcdef", ("create", "join", "match", "match", "bad-pair", "abort-not-ready")):
            with self.subTest(mode=mode, identity=identity):
                bridge, sock, reader = self.bridge(identity)
                reader.close()
                sock.close()
                self.connections.remove((sock, reader))
                endpoint = "Z:"+str(bridge.native_rpc.endpoint).replace("/", "\\")
                args = ["wine", os.environ["SZERO_SESSION_V3_IPC_EXE"], endpoint, identity*32, mode]
                if mode == "join":
                    args.append(first_session)
                result = subprocess.run(args, capture_output=True, text=True, timeout=40)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                owner = bridge.client.client_id.hex()
                if identity == "a":
                    first_session = self.server.native_sessions.memberships[owner]
                if identity == "b":
                    self.assertEqual(self.server.native_sessions.memberships[owner], first_session)
                    self.assertEqual(len(self.server.native_sessions.sessions[first_session].members), 2)
                if mode in ("bad-pair", "abort-not-ready"):
                    self.assertIn("cache=0", result.stdout)
                    self.assertTrue(until(lambda: not self.server.native_sessions.has_membership(owner)))
                else:
                    self.assertIn("cache=1", result.stdout)
        self.assertEqual(len(self.server.native_sessions.sessions), 2)
        self.assertEqual(sorted(len(session.members) for session in self.server.native_sessions.sessions.values()), [2, 2])
