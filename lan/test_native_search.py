import copy
from pathlib import Path
import socket
import tempfile
import time
import unittest

from native_search import MAX_LINE, NativeSearchRegistry, NativeSearchRPC, parse_command, validate_request

LINE = b"BEGIN 1 42 1 18446744073709551615 4 -2147483648 0 2 3 4 5\n"


class RegistryTests(unittest.TestCase):
    def test_exact_query_pending_idempotence_and_cancel(self):
        registry = NativeSearchRegistry()
        request = parse_command(LINE)
        original = copy.deepcopy(request)
        self.assertEqual(registry.handle("a", request)["state"], "pending")
        request["query"]["filters"].clear()
        self.assertEqual(registry.pending["a"], original)
        self.assertEqual(registry.handle("a", original)["state"], "pending")
        changed = copy.deepcopy(original)
        changed["query"]["compatibility"] += 1
        self.assertEqual(registry.handle("a", changed)["error"], "already_searching")
        self.assertEqual(registry.handle("a", dict(original, id=2))["error"], "already_searching")
        self.assertEqual(registry.handle("a", {"op": "cancel", "id": 2})["state"], "cancelled")
        self.assertIn("a", registry.pending)
        registry.handle("a", {"op": "cancel", "id": 1})
        self.assertNotIn("a", registry.pending)
        self.assertEqual(registry.handle("a", dict(original, id=2))["state"], "pending")
        registry.handle("a", {"op": "cancel", "id": 1})
        self.assertEqual(registry.pending["a"]["id"], 2)
        registry.disconnect("a")
        self.assertFalse(registry.pending)

    def test_connection_isolation_and_compound_rejection(self):
        registry = NativeSearchRegistry()
        request = parse_command(LINE)
        registry.handle("a", request)
        registry.handle("b", request)
        registry.handle("a", {"op": "cancel", "id": 1})
        self.assertIn("b", registry.pending)
        request["query"]["compound_count"] = 1
        result = registry.handle("c", request)
        self.assertEqual(result["error"], "unsupported_compound_query")
        self.assertNotIn("c", registry.pending)

    def test_parser_strict_bounds(self):
        self.assertEqual(parse_command(b"CANCEL 3\n"), {"op": "cancel", "id": 3})
        for line in (b"CANCEL 0\n", b"CANCEL 2147483648\n", b"CANCEL 01\n", b"CANCEL 1 \n",
                     LINE[:-1], LINE.replace(b" 4 -", b" 5 -"), LINE.replace(b" 0 2 3", b" 17 2 3"),
                     b"x" * MAX_LINE + b"\n", b"BEGIN 1 42 0 0 2 3 4\n", b"CANCEL \xff\n"):
            with self.subTest(line=line), self.assertRaises(ValueError):
                parse_command(line)
        request = parse_command(LINE)
        for value in (True, 0, -1, 2**31):
            with self.assertRaises(ValueError):
                validate_request(dict(request, id=value))
        with self.assertRaises(ValueError):
            validate_request(dict(request, owner="spoof"))

    def test_begin2_preserves_compound_pairs_without_evaluation(self):
        line = b"BEGIN2 7 42 1 9 2 -3 2 1 0 4 2 1 -5 3 3 6 4 4 7 8 9 10 11\n"
        request = parse_command(line)
        expected = [{"first": {"key": "1", "comparison": 0, "value": 4},
                     "second": {"key": "2", "comparison": 1, "value": -5}},
                    {"first": {"key": "3", "comparison": 3, "value": 6},
                     "second": {"key": "4", "comparison": 4, "value": 7}}]
        self.assertEqual(request["query"]["compound_filters"], expected)
        self.assertEqual(request["query"]["distance"], 8)
        self.assertEqual(request["query"]["field_4e"], 11)
        registry = NativeSearchRegistry()
        self.assertEqual(registry.handle("a", request)["state"], "pending")
        request["query"]["compound_filters"][0]["first"]["value"] = 99
        self.assertEqual(registry.pending["a"]["query"]["compound_filters"], expected)
        self.assertEqual(registry.handle("a", {"op": "cancel", "id": 6})["state"], "cancelled")
        self.assertIn("a", registry.pending)

    def test_begin2_zero_count_and_legacy_missing_pairs(self):
        modern = parse_command(LINE.replace(b"BEGIN ", b"BEGIN2 "))
        self.assertEqual(modern["query"]["compound_filters"], [])
        self.assertEqual(NativeSearchRegistry().handle("a", modern)["state"], "pending")
        old = parse_command(LINE.replace(b" 0 2 3 4 5\n", b" 1 2 3 4 5\n"))
        self.assertNotIn("compound_filters", old["query"])
        self.assertEqual(NativeSearchRegistry().handle("a", old)["error"], "unsupported_compound_query")

    def test_compound_malformed_and_count_mismatch_rejected(self):
        valid = parse_command(b"BEGIN2 1 0 0 1 1 0 1 2 4 -1 0 0 0 0\n")
        for change in (None, {}, [], [None], [{"first": {}}],
                       [{"first": {"key": "1", "comparison": 5, "value": 1},
                         "second": {"key": "2", "comparison": 0, "value": 2}}]):
            request = copy.deepcopy(valid)
            request["query"]["compound_filters"] = change
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_request(request)
        for line in (b"BEGIN2 1 0 0 1 0 0 0 0\n", b"BEGIN2 1 0 0 17 0 0 0 0\n",
                     b"BEGIN2 1 0 0 0 1 0 1 2 0 2 0 0 0 0\n",
                     b"BEGIN2 1 0 0 1 1 0 1 2 0 2 0 0 0\n"):
            with self.subTest(line=line), self.assertRaises(ValueError):
                parse_command(line)

    def test_maximum_begin2_is_bounded(self):
        numeric = "18446744073709551615 4 -2147483648"
        line = ("BEGIN2 2147483647 4294967295 16 " + (numeric + " ") * 16 +
                "16 " + (numeric + " " + numeric + " ") * 16 +
                "4294967295 255 255 255\n").encode()
        self.assertLess(len(line), MAX_LINE)
        request = parse_command(line)
        self.assertEqual(len(request["query"]["filters"]), 16)
        self.assertEqual(len(request["query"]["compound_filters"]), 16)
        import json
        self.assertLess(len(json.dumps({"op": "native_search", "request": request}).encode()), MAX_LINE)


class RPCTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.instance = "a" * 32
        self.rpc = NativeSearchRPC(Path(self.folder.name) / "runtime.lua", self.instance)
        self.sockets = []

    def tearDown(self):
        for connection in self.sockets:
            connection.close()
        self.rpc.close()
        self.assertFalse(self.rpc.thread.is_alive())
        self.folder.cleanup()

    def connect(self, instance=None):
        connection = socket.create_connection(("127.0.0.1", self.rpc.port), timeout=2)
        connection.settimeout(2)
        self.sockets.append(connection)
        connection.sendall(f"HELLO {instance or self.instance}\n".encode())
        return connection

    def command(self):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            values = self.rpc.drain()
            if values:
                return values[0]
            time.sleep(0.01)
        self.fail("native IPC command missing")

    def test_endpoint_begin_pending_cancel(self):
        self.assertEqual(self.rpc.endpoint.read_text(), f"SZERO_NATIVE_ENDPOINT_V1 {self.rpc.port} {self.instance}\n")
        connection = self.connect()
        self.assertEqual(connection.recv(100), b"READY\n")
        connection.sendall(LINE)
        self.assertEqual(self.command(), parse_command(LINE))
        self.rpc.publish({"event": "native_search", "state": "pending", "id": 1})
        self.assertEqual(connection.recv(100), b"PENDING 1\n")
        connection.sendall(b"CANCEL 1\n")
        self.assertEqual(self.command(), {"op": "cancel", "id": 1})
        self.rpc.publish({"event": "native_search", "state": "cancelled", "id": 1})
        self.assertEqual(connection.recv(100), b"CANCELLED 1\n")
        connection.sendall(LINE.replace(b"BEGIN 1 ", b"BEGIN 2 "))
        self.assertEqual(self.command()["id"], 2)
        connection.close()
        self.assertEqual(self.command(), {"op": "cancel", "id": 2})

    def test_wrong_instance_and_large_frames_rejected(self):
        bad = self.connect("b" * 32)
        self.assertEqual(bad.recv(100), b"")
        good = self.connect()
        self.assertEqual(good.recv(100), b"READY\n")
        good.sendall(b"x" * (MAX_LINE + 1))
        self.assertEqual(good.recv(100), b"")
        self.assertEqual(self.rpc.drain(), [])

    def test_disconnect_pending_injects_cancel(self):
        connection = self.connect()
        self.assertEqual(connection.recv(100), b"READY\n")
        connection.sendall(LINE)
        self.assertEqual(self.command()["op"], "begin")
        connection.close()
        self.assertEqual(self.command(), {"op": "cancel", "id": 1})

    def test_reconnect_rejects_replayed_generation(self):
        connection = self.connect()
        self.assertEqual(connection.recv(100), b"READY\n")
        connection.sendall(LINE)
        self.assertEqual(self.command()["id"], 1)
        connection.close()
        self.assertEqual(self.command(), {"op": "cancel", "id": 1})
        replay = self.connect()
        self.assertEqual(replay.recv(100), b"READY\n")
        replay.sendall(LINE)
        self.assertEqual(replay.recv(100), b"")
        fresh = self.connect()
        self.assertEqual(fresh.recv(100), b"READY\n")
        fresh.sendall(LINE.replace(b"BEGIN 1 ", b"BEGIN 2 "))
        self.assertEqual(self.command()["id"], 2)

    def test_stale_server_reply_does_not_cancel_new_generation(self):
        connection = self.connect()
        self.assertEqual(connection.recv(100), b"READY\n")
        connection.sendall(LINE)
        self.assertEqual(self.command()["id"], 1)
        self.rpc.publish({"event": "native_search", "state": "cancelled", "id": 1})
        self.assertEqual(connection.recv(100), b"CANCELLED 1\n")
        connection.sendall(LINE.replace(b"BEGIN 1 ", b"BEGIN 2 "))
        self.assertEqual(self.command()["id"], 2)
        self.rpc.publish({"event": "native_search", "state": "cancelled", "id": 1})
        self.rpc.publish({"event": "native_search", "state": "pending", "id": 2})
        self.assertEqual(connection.recv(100), b"PENDING 2\n")

    def test_close_preserves_replaced_endpoint(self):
        self.rpc.endpoint.write_text("replacement\n")
        self.rpc.close()
        self.assertEqual(self.rpc.endpoint.read_text(), "replacement\n")


if __name__ == "__main__":
    unittest.main()
