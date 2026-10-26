"""Actual compiled Win64 worker -> real bridge -> eight-member TCP session.

Native allocation/JSON ownership callbacks are synthetic, not game acceptance.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import unittest

from ingame_client import GameBridge
from lan_identity import principal
import test_native_session_bridge as bridge_fixtures

until = bridge_fixtures.until


class MultiCompiledBridgeTests(unittest.TestCase):
    setUp = bridge_fixtures.NativeSessionBridgeTests.setUp
    tearDown = bridge_fixtures.NativeSessionBridgeTests.tearDown

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
        self.assertTrue(until(lambda: bridge.native_session_capability
            and bridge.native_rpc.multi_capability and bridge.native_rpc.multi_proxy_ports))
        return bridge

    def run_native(self, bridge, identity, mode, sid=None):
        executable = os.environ["SZERO_SESSION_V3_IPC_EXE"]
        endpoint = "Z:"+str(bridge.native_rpc.endpoint).replace("/", "\\")
        arguments = ["wine", executable, endpoint, identity*32, mode]
        if sid is not None:
            arguments.append(sid)
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn(f"V3 fixture mode={mode} cache=1", result.stdout)
        return result.stdout

    @unittest.skipUnless(os.environ.get("SZERO_SESSION_V3_IPC_EXE"), "compiled multi-session fixture not selected")
    def test_two_player_quickmatch_keeps_search_then_create_join_on_multi_transport(self):
        peers = [self.bridge(identity) for identity in "ab"]
        for identity, bridge, action in zip("ab", peers, ("create", "join")):
            output = self.run_native(bridge, identity, "quickmatch-multi")
            self.assertIn(f"V3 quickmatch action={action}", output)
        session = self.server.native_sessions.describe_membership(peers[0].client.client_id.hex())
        self.assertEqual(session["capacity"], 2)
        self.assertEqual(session["partition"]["protocol"], 5)
        self.assertEqual(len(session["members"]), 2)

    @unittest.skipUnless(os.environ.get("SZERO_SESSION_V3_IPC_EXE"), "compiled multi-session fixture not selected")
    def test_eight_compiled_native_peers_join_leave_and_rejoin(self):
        self.assertTrue(os.environ.get("WINEPREFIX", "").startswith("/tmp/szero-"))
        bridges = [self.bridge(identity) for identity in "12345678"]
        self.run_native(bridges[0], "1", "tournament-multi")
        own = bridges[0].client.client_id.hex()
        sid = self.server.native_sessions.memberships[own]
        for index, bridge in enumerate(bridges[1:], 2):
            self.run_native(bridge, str(index), "tournament-join-multi", sid)
            self.assertEqual(len(self.server.native_sessions.sessions[sid].members), index)
            self.assertEqual(self.server.native_sessions.sessions[sid].partition[1], 5)
        self.assertTrue(until(lambda: all(b.native_rpc.session_snapshot and
            b.native_rpc.session_snapshot.startswith(b"SESSION4 ") and
            principal(bridges[-1].client.client_id.hex()).hex().encode() in b.native_rpc.session_snapshot
            for b in bridges)))
        # Direct leave uses the same real IPC and server-owned membership path.
        departing = bridges[3]
        pinned = departing.client.remote_proxy(bridges[0].client.client_id.hex())
        with socket.create_connection(("127.0.0.1", departing.native_rpc.port), timeout=5) as sock:
            with sock.makefile("rb") as reader:
                sock.sendall(f"HELLO5 {'4'*32}\n".encode())
                self.assertTrue(reader.readline().startswith(b"READY5 "))
                sock.sendall(b"LEAVE3 50\n")
                self.assertEqual(reader.readline(), b"RESULT3 50 OK\n")
        self.assertTrue(until(lambda: len(self.server.native_sessions.sessions[sid].members)==7))
        self.run_native(departing, "4", "tournament-rejoin-multi", sid)
        self.assertEqual(len(self.server.native_sessions.sessions[sid].members), 8)
        self.assertEqual(departing.client.remote_proxy(bridges[0].client.client_id.hex()), pinned)
        self.assertFalse(self.server.matches)
        self.assertFalse(self.server.native_search.pending)


if __name__ == "__main__":
    unittest.main()
