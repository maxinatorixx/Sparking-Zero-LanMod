from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest

from native_search import NativeSearchRPC, parse_session_command
from native_sessions import NativeSessionDirectory

CREATE = b"CREATE3 1 42 2 -1 7 2 0 1 3 0 3 616263 61 62 3132372e302e302e313a34303030 0 0 0 0\n"
MATCH = CREATE.replace(b"CREATE3", b"MATCH3").rstrip(b"\n") + b" 0 42 0 0 0 0 0 255\n"


class SessionCommandTests(unittest.TestCase):
    def test_settings_member_stream_and_search_preserved(self):
        command = parse_session_command(CREATE)
        data = command["request"]["native_data"]
        self.assertEqual(data["numeric"], [-1, 7])
        self.assertEqual(data["stream"]["data_base64"], "YWJj")
        self.assertEqual(data["stream"]["write_cursor"], 3)
        self.assertEqual(data["member"]["identity_hex"], ["61", "62"])
        search = parse_session_command(b"SEARCH3 2 0 42 1 0 4 -1 1 1 0 2 2 3 -3 0 0 0 255\n")
        self.assertEqual(search["request"]["query"]["compound_count"], 1)
        self.assertFalse(search["request"]["default_normalize"])
        match = parse_session_command(CREATE.replace(b"CREATE3", b"MATCH3").rstrip(b"\n") +
                                      b" 0 42 0 0 0 0 0 255\n")
        self.assertEqual(match["request"]["op"], "match")
        self.assertEqual(match["request"]["native_data"], data)
        self.assertEqual(match["request"]["query"]["compatibility"], 42)
        self.assertEqual(parse_session_command(b"FLAGS3 3 65535\n")["request"]["flags"], 65535)
        self.assertEqual(parse_session_command(b"POLL3 4\n")["op"], "poll")

    def test_strict_bounds_and_unrecognized_fields(self):
        for line in (CREATE.replace(b"616263", b"61626"), CREATE.replace(b" 3 0 3 ", b" 3 0 4 "),
                     CREATE.replace(b"CREATE3 1", b"CREATE3 01"), CREATE[:-1], CREATE[:-1] + b" extra\n",
                     b"ACK3 0\n", b"LEAVE3 1 \n", b"JOIN3 1 nope 61 62 63 0 0 0\n"):
            with self.subTest(line=line), self.assertRaises(ValueError):
                parse_session_command(line)
        self.assertEqual(parse_session_command(b"ACK3 1\n")["op"], "commit")

    def test_settings_update_preserves_raw_settings_and_member_flags(self):
        line = b"UPDATESETTINGS3 7 4294967295 2 -2147483648 2147483647 2 255 1 3 1 3 01ff7f 6162 6364 6566 255 1 249\n"
        request = parse_session_command(line)["request"]
        self.assertEqual(set(request), {"version", "request_id", "op", "native_member", "native_data"})
        self.assertEqual(request["op"], "update")
        self.assertEqual(request["native_data"]["compatibility"], 2**32-1)
        self.assertEqual(request["native_data"]["numeric"], [-(2**31), 2**31-1])
        self.assertEqual(request["native_data"]["stream"], {"kind": "spnet-memory-v1", "data_base64": "Af9/",
                                                               "read_cursor": 1, "write_cursor": 3})
        member = request["native_member"]
        self.assertEqual(member, request["native_data"]["member"])
        self.assertEqual((member["field_88"], member["optional_present"], member["optional_value"]), (255, True, 249))
        request["native_member"]["optional_value"] = 0
        self.assertEqual(request["native_data"]["member"]["optional_value"], 249)
        with self.assertRaises(ValueError):
            parse_session_command(line[:-1] + b" 0\n")


class SessionRPCTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.rpc = NativeSearchRPC(Path(self.folder.name) / "runtime.lua", "a" * 32)
        self.sock = socket.create_connection(("127.0.0.1", self.rpc.port), timeout=2)
        self.sock.settimeout(2)
        self.reader = self.sock.makefile("rb")
        self.sock.sendall(b"HELLO " + b"a" * 32 + b"\n")
        self.assertEqual(self.reader.readline(), b"READY\n")

    def tearDown(self):
        self.reader.close()
        self.sock.close()
        self.rpc.close()
        self.folder.cleanup()

    def command(self):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            commands = self.rpc.drain()
            if commands:
                return commands[0]
            time.sleep(.01)
        self.fail("missing command")

    def prepared(self):
        self.sock.sendall(CREATE)
        command = self.command()
        self.assertEqual(command["channel"], "native_session_transaction")
        self.assertEqual(command["request"]["op"], "prepare")
        directory = NativeSessionDirectory()
        result = directory.handle("b" * 32, command["request"]["request"])
        self.rpc.publish({"event": "native_session_transaction", "transaction_id": "rpc-1",
                          "op": "prepare", "state": "prepared", "session": result["session"]})
        self.assertEqual(self.reader.readline(), b"RESULT3 1 PREPARED\n")
        self.assertTrue(self.reader.readline().startswith(b"SESSION3 "))

    def test_prepare_ack_commit_and_stale_result_isolation(self):
        self.prepared()
        self.sock.sendall(b"ACK3 1\n")
        command = self.command()
        self.assertEqual(command["request"], {"version": 1, "op": "commit", "transaction_id": "rpc-1"})
        self.rpc.publish({"event": "native_session_transaction", "transaction_id": "rpc-1",
                          "state": "committed", "op": "commit"})
        self.assertEqual(self.reader.readline(), b"RESULT3 1 COMMITTED\n")
        self.sock.sendall(b"LEAVE3 2\n")
        command = self.command()
        self.assertEqual(command["request"]["op"], "leave")
        self.rpc.publish({"event": "native_session_result", "request_id": "rpc-1", "left": True})
        self.rpc.publish({"event": "native_session_result", "request_id": "rpc-2", "left": True})
        self.assertEqual(self.reader.readline(), b"RESULT3 2 OK\n")

    def test_disconnect_before_prepare_reply_aborts(self):
        self.sock.sendall(CREATE)
        self.assertEqual(self.command()["request"]["op"], "prepare")
        self.sock.shutdown(socket.SHUT_RDWR)
        command = self.command()
        self.assertEqual(command["request"], {"version": 1, "op": "abort", "transaction_id": "rpc-1"})

    def test_cancel_before_prepare_reply_cannot_publish_late_descriptor(self):
        self.sock.sendall(CREATE)
        self.command()
        self.sock.sendall(b"CANCEL3 1\n")
        self.assertEqual(self.command()["request"]["op"], "abort")
        self.rpc.publish({"event": "native_session_transaction", "transaction_id": "rpc-1",
                          "state": "prepared", "session": {}})
        self.rpc.publish({"event": "native_session_transaction", "transaction_id": "rpc-1", "state": "aborted"})
        self.assertEqual(self.reader.readline(), b"RESULT3 1 CANCELLED\n")

    def test_poll_only_reports_verified_server_snapshot_and_revocation(self):
        request = parse_session_command(CREATE)["request"]
        result = NativeSessionDirectory().handle("b" * 32, request)
        self.rpc.publish({"event": "native_session_state", "session": result["session"]})
        self.sock.sendall(b"POLL3 1\n")
        self.assertEqual(self.reader.readline(), b"RESULT3 1 OK\n")
        self.assertTrue(self.reader.readline().startswith(b"SESSION3 "))
        self.assertEqual(self.rpc.drain(), [])
        self.rpc.publish({"event": "native_session_state", "session": None})
        self.sock.sendall(b"POLL3 2\n")
        self.assertEqual(self.reader.readline(), b"RESULT3 2 EMPTY\n")

    def test_late_native_cancel_after_committed_reply_revokes_exact_generation(self):
        self.prepared()
        self.sock.sendall(b"ACK3 1\n")
        self.assertEqual(self.command()["request"]["op"], "commit")
        self.rpc.publish({"event": "native_session_transaction", "transaction_id": "rpc-1", "state": "committed"})
        self.assertEqual(self.reader.readline(), b"RESULT3 1 COMMITTED\n")
        self.sock.sendall(b"CANCEL3 1\n")
        self.assertEqual(self.command()["request"], {"version": 1, "op": "abort", "transaction_id": "rpc-1"})
        self.rpc.publish({"event": "native_session_transaction", "transaction_id": "rpc-1", "state": "aborted"})
        self.assertEqual(self.reader.readline(), b"RESULT3 1 CANCELLED\n")

    def test_committed_normal_close_does_not_leave_and_reconnect_can_cancel(self):
        self.prepared()
        self.sock.sendall(b"ACK3 1\n")
        self.command()
        self.rpc.publish({"event": "native_session_transaction", "transaction_id": "rpc-1", "state": "committed"})
        self.assertEqual(self.reader.readline(), b"RESULT3 1 COMMITTED\n")
        self.reader.close()
        self.sock.close()
        time.sleep(.1)
        self.assertEqual(self.rpc.drain(), [])
        self.rpc.transport_ports = (27151, 27152)
        self.sock = socket.create_connection(("127.0.0.1", self.rpc.port), timeout=2)
        self.sock.settimeout(2)
        self.reader = self.sock.makefile("rb")
        self.sock.sendall(b"HELLO3 " + b"a" * 32 + b"\n")
        self.assertEqual(self.reader.readline(), b"READY3 27151 27152\n")
        self.sock.sendall(b"CANCEL3 1\n")
        self.assertEqual(self.command()["request"]["op"], "abort")
        self.rpc.publish({"event": "native_session_transaction", "transaction_id": "rpc-1", "state": "aborted"})
        self.assertEqual(self.reader.readline(), b"RESULT3 1 CANCELLED\n")

    def test_addresses_are_process_local_copies_identity_is_preserved(self):
        directory = NativeSessionDirectory()
        created = directory.handle("b" * 32, parse_session_command(CREATE)["request"])
        request = parse_session_command(("JOIN3 2 " + created["session"]["session_id"] + " 63 64 65 0 0 0\n").encode())["request"]
        joined = directory.handle("c" * 32, request)
        original = joined["session"]["native_descriptor"]
        self.rpc.transport_ports = (27151, 27152)
        self.rpc.session_identity = ["61", "62"]
        frame = self.rpc._encode_local_descriptor(original)
        self.assertIn(b"127.0.0.1:27151".hex().encode(), frame)
        self.assertIn(b"127.0.0.1:27152".hex().encode(), frame)
        self.assertEqual(original["members"][0]["identity_hex"], ["61", "62"])
        self.assertEqual(original["members"][0]["address_hex"], "3132372e302e302e313a34303030")
        self.assertEqual(original["members"][1]["address_hex"], "65")

    def test_stale_cancel_after_next_generation_does_not_revoke(self):
        self.prepared()
        self.sock.sendall(b"ACK3 1\n")
        self.command()
        self.rpc.publish({"event": "native_session_transaction", "transaction_id": "rpc-1", "state": "committed"})
        self.assertEqual(self.reader.readline(), b"RESULT3 1 COMMITTED\n")
        self.sock.sendall(b"POLL3 2\n")
        self.assertEqual(self.reader.readline(), b"RESULT3 2 EMPTY\n")
        self.sock.sendall(b"CANCEL3 1\n")
        self.assertEqual(self.reader.readline(), b"RESULT3 1 ERROR\n")
        self.assertEqual(self.rpc.drain(), [])

    def test_match_busy_retries_identical_generation_until_prepared(self):
        self.sock.sendall(MATCH)
        original = self.command()
        for _ in range(2):
            self.rpc.publish({"event": "native_session_transaction", "transaction_id": "rpc-1", "op": "prepare",
                              "state": "error", "message": "native_match_busy"})
            self.assertEqual(self.command(), original)
        result = NativeSessionDirectory().handle("b" * 32, parse_session_command(CREATE)["request"])
        self.rpc.publish({"event": "native_session_transaction", "transaction_id": "rpc-1", "op": "prepare",
                          "state": "prepared", "session": result["session"]})
        self.assertEqual(self.reader.readline(), b"RESULT3 1 PREPARED\n")
        self.assertTrue(self.reader.readline().startswith(b"SESSION3 "))

    def test_cancel_while_match_busy_stops_retry_and_ignores_late_busy(self):
        self.sock.sendall(MATCH)
        self.command()
        busy = {"event": "native_session_transaction", "transaction_id": "rpc-1", "op": "prepare",
                "state": "error", "message": "native_match_busy"}
        self.rpc.publish(busy)
        self.sock.sendall(b"CANCEL3 1\n")
        self.assertEqual(self.command()["request"]["op"], "abort")
        self.rpc.publish(busy)
        self.rpc.publish({"event": "native_session_transaction", "transaction_id": "rpc-1", "op": "abort", "state": "aborted"})
        self.assertEqual(self.reader.readline(), b"RESULT3 1 CANCELLED\n")
        time.sleep(.2)
        self.assertEqual(self.rpc.drain(), [])

    def test_delayed_commit_reply_cannot_rewind_newer_member_snapshot(self):
        self.prepared()
        self.sock.sendall(b"ACK3 1\n")
        self.command()
        directory = NativeSessionDirectory()
        created = directory.handle("b" * 32, parse_session_command(CREATE)["request"])
        join = parse_session_command(("JOIN3 2 " + created["session"]["session_id"] + " 63 64 65 0 0 0\n").encode())["request"]
        joined = directory.handle("c" * 32, join)
        fetched, release = threading.Event(), threading.Event()
        original_get = self.rpc.session_outbound.get_nowait

        def delayed_get():
            event = original_get()
            if event.get("state") == "committed":
                fetched.set()
                release.wait(2)
            return event

        self.rpc.session_outbound.get_nowait = delayed_get
        try:
            self.rpc.publish({"event": "native_session_transaction", "transaction_id": "rpc-1", "op": "commit",
                              "state": "committed", "session": created["session"]})
            self.assertTrue(fetched.wait(2))
            self.rpc.publish({"event": "native_session_state", "session": joined["session"]})
        finally:
            release.set()
        self.assertEqual(self.reader.readline(), b"RESULT3 1 COMMITTED\n")
        self.sock.sendall(b"POLL3 2\n")
        self.assertEqual(self.reader.readline(), b"RESULT3 2 OK\n")
        frame = self.reader.readline()
        self.assertIn(joined["session"]["native_descriptor"]["members"][1]["id"].encode(), frame)
        # A delayed abort from the older transaction cannot clear the mailbox
        # after the helper has advanced to a new generation either.
        self.rpc.publish({"event": "native_session_transaction", "transaction_id": "rpc-1", "op": "abort", "state": "aborted"})
        self.sock.sendall(b"POLL3 3\n")
        self.assertEqual(self.reader.readline(), b"RESULT3 3 OK\n")
        self.assertEqual(self.reader.readline(), frame)


if __name__ == "__main__":
    unittest.main()
