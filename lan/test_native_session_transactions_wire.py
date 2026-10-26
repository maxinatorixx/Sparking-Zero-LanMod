"""Actual TCP transaction lifecycle and UDP isolation; never game callbacks."""
import socket
import time
import unittest

import test_native_session_transport as transport
from test_native_sessions_v2 import data, member, query, request


class NativeTransactionWireTests(unittest.TestCase):
    # Reuse only connection/socket fixture helpers, not its test methods.
    setUp = transport.NativeSessionTransportTests.setUp
    tearDown = transport.NativeSessionTransportTests.tearDown
    connect = transport.NativeSessionTransportTests.connect
    operation = transport.NativeSessionTransportTests.operation
    create = transport.NativeSessionTransportTests.create

    def transaction(self, client, op, generation=1, payload=None, state=None):
        message = {"version": 1, "op": op, "transaction_id": f"rpc-{generation}"}
        if payload is not None:
            message["request"] = payload
        client.send("native_session_transaction", request=message)
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            event = client.events.get(timeout=4)
            if event.get("event") == "native_session_transaction":
                self.assertEqual(event["transaction_id"], message["transaction_id"])
                self.assertEqual(event["op"], op)
                if state is not None:
                    self.assertEqual(event["state"], state, event)
                return event
        self.fail("missing native transaction response")

    def create_payload(self, label, op="create"):
        native = data(label)
        payload = request(op, native_data=native,
            attributes={str(i): value for i, value in enumerate(native["numeric"])})
        if op == "match":
            payload.update(query=query(), default_normalize=False, create_flags=0)
        return payload

    def test_prepare_is_invisible_commit_ids_stable_and_duplicate_commit(self):
        (host, _), (observer, _) = self.connect("host"), self.connect("observer")
        prepared = self.transaction(host, "prepare", payload=self.create_payload("host"), state="prepared")
        self.assertEqual(self.server.native_sessions.sessions, {})
        self.assertIsNone(host.assignment)
        found = self.operation(observer, "search", query=query(), default_normalize=False,
                                materialization_profile=2, limit=1)
        self.assertEqual(found["sessions"], [])
        replay = self.transaction(host, "prepare", payload=self.create_payload("host"), state="prepared")
        self.assertEqual(replay["session"], prepared["session"])
        committed = self.transaction(host, "commit", state="committed")
        self.assertEqual(committed["session"], prepared["session"])
        duplicate = self.transaction(host, "commit", state="committed")
        self.assertEqual(duplicate["session"], committed["session"])
        found = self.operation(observer, "search", query=query(), default_normalize=False,
                                materialization_profile=2, limit=1)
        self.assertEqual(found["sessions"], [committed["session"]])

    def test_disconnect_releases_uncommitted_join_and_no_route_exists(self):
        (host, _), (guest, _), (next_guest, _) = [self.connect(name) for name in ("h", "g", "n")]
        session = self.create(host, "host")
        joined = request("join", session_id=session["session_id"], native_member=member("guest"))
        self.transaction(guest, "prepare", payload=joined, state="prepared")
        self.assertEqual(len(self.server.native_sessions.describe_membership(host.client_id.hex())["members"]), 1)
        self.assertIsNone(self.server.native_sessions.relay_peer(host.client_id.hex(), session["session_id"]))
        self.assertIsNone(guest.assignment)
        denied = self.transaction(next_guest, "prepare",
            payload=dict(joined, native_member=member("next")), state="error")
        self.assertIn("reserved", denied["message"])
        guest.close()
        self.assertTrue(transport.until(lambda: guest.client_id.hex() not in self.server.native_transactions.records))
        staged = self.transaction(next_guest, "prepare", generation=2,
            payload=dict(joined, native_member=member("next")), state="prepared")
        self.assertEqual(staged["session"]["session_id"], session["session_id"])
        self.transaction(next_guest, "commit", generation=2, state="committed")
        self.assertTrue(transport.until(lambda: host.assignment and next_guest.assignment))

    def test_late_abort_cannot_remove_new_generation_membership(self):
        host, _ = self.connect("host")
        first = self.transaction(host, "prepare", payload=self.create_payload("first"), state="prepared")
        self.transaction(host, "commit", state="committed")
        self.operation(host, "leave")
        second = self.transaction(host, "prepare", 2, self.create_payload("second"), state="prepared")
        self.transaction(host, "commit", 2, state="committed")
        self.assertNotEqual(first["session"]["session_id"], second["session"]["session_id"])
        self.transaction(host, "abort", 1, state="error")
        self.assertEqual(self.server.native_sessions.memberships[host.client_id.hex()], second["session"]["session_id"])
        self.transaction(host, "abort", 2, state="aborted")
        self.assertFalse(self.server.native_sessions.has_membership(host.client_id.hex()))
        self.transaction(host, "abort", 3, state="aborted")
        self.transaction(host, "prepare", 3, self.create_payload("late"), state="error")
        self.assertEqual(self.server.native_sessions.sessions, {})

    def test_two_committed_transaction_sessions_route_independently(self):
        pairs = [self.connect(str(i)) for i in range(5)]
        a, b, c, d, observer = [pair[0] for pair in pairs]
        first = self.transaction(a, "prepare", payload=self.create_payload("a", "match"), state="prepared")
        self.transaction(a, "commit", state="committed")
        second = self.transaction(b, "prepare", payload=self.create_payload("b", "match"), state="prepared")
        self.assertEqual(second["action"], "join")
        self.assertEqual(first["session"]["session_id"], second["session"]["session_id"])
        third = self.transaction(c, "prepare", payload=self.create_payload("c", "match"), state="prepared")
        self.assertEqual(third["action"], "create")
        self.transaction(c, "commit", state="committed")
        self.transaction(b, "commit", state="committed")
        fourth = self.transaction(d, "prepare", payload=self.create_payload("d", "match"), state="prepared")
        self.assertEqual(fourth["action"], "join")
        self.assertEqual(third["session"]["session_id"], fourth["session"]["session_id"])
        self.transaction(d, "commit", state="committed")
        self.assertTrue(transport.until(lambda: all(client.assignment for client in (a, b, c, d))))
        self.assertIsNone(observer.assignment)
        for sender, receiver in ((0, 1), (1, 0), (2, 3), (3, 2)):
            payload = f"native-transaction-{sender}".encode()
            pairs[sender][1].sendto(payload, ("127.0.0.1", pairs[sender][0].proxy_port))
            received, address = pairs[receiver][1].recvfrom(100)
            self.assertEqual(received, payload)
            self.assertEqual(address[1], pairs[receiver][0].proxy_port)
        self.transaction(b, "abort", state="aborted")
        self.assertTrue(transport.until(lambda: b.assignment is None))
        self.assertIsNone(self.server.native_sessions.relay_peer(a.client_id.hex(), first["session"]["session_id"]))
        self.assertTrue(c.assignment and d.assignment)
        pairs[0][1].sendto(b"revoked", ("127.0.0.1", a.proxy_port))
        for _, game in pairs:
            with self.assertRaises(socket.timeout):
                game.recvfrom(100)
        self.assertEqual(self.server.matches, {})
        self.assertEqual(self.server.waiting, [])

    def test_late_abort_cannot_remove_new_member_in_same_session(self):
        (host, _), (guest, _) = self.connect("host"), self.connect("guest")
        session = self.create(host, "host")
        payload = request("join", session_id=session["session_id"], native_member=member("guest"))
        prepared = self.transaction(guest, "prepare", payload=payload, state="prepared")
        self.transaction(guest, "commit", state="committed")
        self.operation(guest, "leave")
        new = self.operation(guest, "join", session_id=session["session_id"], native_member=member("guest"))
        self.assertNotEqual(prepared["session"]["members"][1]["member_id"],
                            new["session"]["members"][1]["member_id"])
        self.transaction(guest, "abort", state="aborted")
        self.assertEqual(self.server.native_sessions.describe_membership(guest.client_id.hex()), new["session"])
        self.assertEqual(self.server.native_sessions.relay_peer(host.client_id.hex(), session["session_id"]),
                         guest.client_id.hex())


if __name__ == "__main__":
    unittest.main()
