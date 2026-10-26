"""Real loopback search/cancel path; no game or production service involved."""
import asyncio
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest

from ingame_client import GameBridge
from native_search import parse_command
from szero_lan import GameServer

LINE = b"BEGIN 1 42 1 123 0 -5 0 2 3 4 5\n"
COMPOUND_LINE = b"BEGIN2 1 42 1 123 0 -5 1 41 2 -9 43 4 17 2 3 4 5\n"


def until(predicate):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


class NativeSearchWireTests(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.started = threading.Event()
        self.failure = None
        self.connections = []

        def run():
            asyncio.set_event_loop(self.loop)
            try:
                self.server = self.loop.run_until_complete(GameServer("127.0.0.1", 0).start())
            except BaseException as exc:
                self.failure = exc
                self.started.set()
                return
            self.started.set()
            self.loop.run_forever()
            self.loop.close()

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        self.assertTrue(self.started.wait(3))
        if self.failure:
            raise self.failure

    def tearDown(self):
        for sock, stream in self.connections:
            stream.close()
            sock.close()
        asyncio.run_coroutine_threadsafe(self.server.close(), self.loop).result(3)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(3)

    def connect(self):
        sock = socket.create_connection(("127.0.0.1", self.server.port), timeout=3)
        sock.settimeout(3)
        stream = sock.makefile("rb")
        self.connections.append((sock, stream))
        sock.sendall(b'{"op":"hello","version":2,"name":"Native fixture"}\n')
        welcome = json.loads(stream.readline())
        self.assertEqual(welcome["capabilities"]["native_search"], 1)
        json.loads(stream.readline())  # broadcast
        return sock, stream, welcome["client_id"]

    def exchange(self, sock, stream, message):
        sock.sendall(json.dumps(message).encode() + b"\n")
        return json.loads(stream.readline())

    def test_begin_pending_cancel_and_mutual_exclusion(self):
        sock, stream, owner = self.connect()
        result = self.exchange(sock, stream, {"op": "native_search", "request": parse_command(LINE)})
        self.assertEqual(result["state"], "pending")
        self.assertEqual(self.server.native_search.pending[owner]["query"]["filters"][0]["value"], -5)
        self.assertEqual(self.exchange(sock, stream, {"op": "queue"})["event"], "error")
        session = {"version": 1, "request_id": "test", "op": "create", "attributes": {},
                   "partition": {"build": "e" * 64, "protocol": 1, "mode": 0}}
        self.assertEqual(self.exchange(sock, stream, {"op": "native_session", "request": session})["event"],
                         "native_session_error")
        self.assertFalse(self.server.waiting)
        result = self.exchange(sock, stream, {"op": "native_search", "request": {"op": "cancel", "id": 2}})
        self.assertEqual(result["state"], "cancelled")
        self.assertIn(owner, self.server.native_search.pending)
        self.exchange(sock, stream, {"op": "native_search", "request": {"op": "cancel", "id": 1}})
        self.assertNotIn(owner, self.server.native_search.pending)
        self.assertEqual(self.server.matches, {})

    def test_control_disconnect_clears_pending(self):
        sock, stream, owner = self.connect()
        self.exchange(sock, stream, {"op": "native_search", "request": parse_command(LINE)})
        stream.close()
        sock.close()
        self.assertTrue(until(lambda: owner not in self.server.native_search.pending))

    def test_helper_through_game_bridge_to_server_and_back(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "SzeroLAN.json").write_text(json.dumps({"server_host": "127.0.0.1",
                "server_port": self.server.port, "name": "Bridge fixture", "native_search": True}))
            bridge = GameBridge(root, root / ("lan_runtime_" + "a" * 32 + ".lua"))
            stop = threading.Event()
            thread = threading.Thread(target=bridge.run, args=(stop,), daemon=True)
            thread.start()
            helper = None
            try:
                self.assertTrue(until(lambda: bridge.native_capability))
                helper = socket.create_connection(("127.0.0.1", bridge.native_rpc.port), timeout=3)
                helper.settimeout(3)
                helper.sendall(("HELLO " + "a" * 32 + "\n").encode())
                self.assertEqual(helper.recv(100), b"READY\n")
                helper.sendall(COMPOUND_LINE)
                self.assertEqual(helper.recv(100), b"PENDING 1\n")
                self.assertEqual(len(self.server.native_search.pending), 1)
                captured = next(iter(self.server.native_search.pending.values()))
                self.assertEqual(captured["query"]["compound_filters"],
                                 parse_command(COMPOUND_LINE)["query"]["compound_filters"])
                helper.sendall(b"CANCEL 1\n")
                self.assertEqual(helper.recv(100), b"CANCELLED 1\n")
                self.assertTrue(until(lambda: not self.server.native_search.pending))
                self.assertEqual(self.server.matches, {})
            finally:
                if helper:
                    helper.close()
                stop.set()
                thread.join(4)
                self.assertFalse(thread.is_alive())
                self.assertFalse(bridge.native_rpc.endpoint.exists())

    def test_config_is_strict_opt_in(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "SzeroLAN.json"
            config.write_text('{"server_host":"localhost"}')
            self.assertIsNone(GameBridge(root, root / "lan_runtime_1.lua").native_rpc)
            for value in (1, "true", None):
                config.write_text(json.dumps({"server_host": "localhost", "native_search": value}))
                with self.assertRaisesRegex(ValueError, "must be true or false"):
                    GameBridge(root, root / "lan_runtime_1.lua")
            config.write_text('{"server_host":"localhost","native_search":true}')
            with self.assertRaisesRegex(ValueError, "instance-scoped"):
                GameBridge(root, root / "lan_runtime_1.lua")


if __name__ == "__main__":
    unittest.main()
