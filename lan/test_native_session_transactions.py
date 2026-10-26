"""Real directory preparation/cancellation, without any native game calls."""
import copy
import unittest

from native_sessions import NativeSessionDirectory
from native_session_transactions import NativeSessionTransactions
from test_native_sessions_v2 import A, B, C, create, data, member, request, search, query


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.directory = NativeSessionDirectory()
        self.tx = NativeSessionTransactions(self.directory, lambda: self.now)

    def operation(self, owner, op, generation=1, payload=None):
        message = {"version": 1, "op": op, "transaction_id": f"rpc-{generation}"}
        if payload is not None:
            message["request"] = payload
        return self.tx.handle(owner, message)

    def prepare_create(self, owner=A, generation=1):
        native = data(owner[0])
        return self.operation(owner, "prepare", generation, request("create", native_data=native,
                              attributes={str(i): v for i, v in enumerate(native["numeric"])}))

    def test_create_invisible_until_commit_with_stable_ids(self):
        prepared = self.prepare_create()
        snapshot = copy.deepcopy(prepared)
        self.assertFalse(self.directory.has_membership(A))
        self.assertEqual(search(self.directory), [])
        committed = self.operation(A, "commit")
        self.assertEqual(committed["session"], snapshot["session"])
        self.assertEqual(search(self.directory), [committed["session"]])
        self.assertEqual(self.operation(A, "commit"), committed)
        prepared["session"]["native_descriptor"]["numeric"].clear()
        self.assertEqual(self.directory.describe_membership(A), committed["session"])

    def test_join_reserved_but_not_visible_or_routable(self):
        session = create(self.directory)
        payload = request("join", session_id=session["session_id"], native_member=member("b"))
        prepared = self.operation(B, "prepare", payload=payload)
        self.assertEqual(len(prepared["session"]["members"]), 2)
        self.assertEqual(self.directory.describe_membership(A), session)
        self.assertIsNone(self.directory.relay_peer(A, session["session_id"]))
        with self.assertRaises(ValueError):
            self.tx.guard(C, request("join", session_id=session["session_id"], native_member=member("c")))
        with self.assertRaises(ValueError):
            self.tx.guard(A, request("update", native_member=member("a")))
        self.operation(B, "commit")
        self.assertEqual(self.directory.relay_peer(A, session["session_id"]), B)

    def test_abort_prepare_and_late_prepare_or_commit_rejected(self):
        self.prepare_create()
        self.operation(A, "abort")
        self.assertEqual(self.directory.sessions, {})
        with self.assertRaises(ValueError):
            self.operation(A, "commit")
        with self.assertRaises(ValueError):
            self.prepare_create()
        self.operation(B, "abort", 5)
        with self.assertRaises(ValueError):
            self.prepare_create(B, 5)
        self.prepare_create(B, 6)

    def test_abort_committed_only_removes_exact_old_membership(self):
        old = self.prepare_create()["session"]["session_id"]
        self.operation(A, "commit")
        self.directory.disconnect(A)
        new = create(self.directory)["session_id"]
        self.assertNotEqual(old, new)
        self.operation(A, "abort")
        self.assertEqual(self.directory.memberships[A], new)

    def test_abort_committed_join_preserves_host_and_reopens_slot(self):
        session = create(self.directory)
        self.operation(B, "prepare", payload=request("join", session_id=session["session_id"], native_member=member("b")))
        self.operation(B, "commit")
        self.operation(B, "abort")
        self.operation(B, "abort")
        self.assertEqual(self.directory.describe_membership(A), session)
        self.assertFalse(self.directory.has_membership(B))

    def test_timeout_disconnect_and_creator_leave_release_reservation(self):
        session = create(self.directory)
        payload = request("join", session_id=session["session_id"], native_member=member("b"))
        self.operation(B, "prepare", payload=payload)
        self.now += 120
        with self.assertRaises(ValueError):
            self.operation(B, "commit")
        self.tx.guard(C, request("join", session_id=session["session_id"], native_member=member("c")))
        self.operation(B, "prepare", 2, payload)
        self.tx.disconnect(B)
        self.operation(C, "prepare", payload=dict(payload, native_member=member("c")))
        self.directory.disconnect(A)
        with self.assertRaises(ValueError):
            self.operation(C, "commit")
        self.assertEqual(self.directory.sessions, {})

    def test_prepare_is_idempotent_replays_and_unowned_mutations_fail(self):
        prepared = self.prepare_create()
        self.assertEqual(self.prepare_create(), prepared)
        with self.assertRaises(ValueError):
            self.prepare_create(generation=2)
        with self.assertRaises(ValueError):
            self.operation(B, "commit")
        self.operation(A, "abort")
        self.prepare_create(generation=2)
        for op in ("prepare", "commit", "abort"):
            with self.assertRaises(ValueError):
                self.operation(A, op, 1, request("create") if op == "prepare" else None)

    def test_capacity_reservations_and_direct_membership_guard(self):
        self.directory.max_sessions = 1
        self.prepare_create()
        with self.assertRaises(ValueError):
            self.prepare_create(B)
        with self.assertRaises(ValueError):
            self.tx.guard(B, request("create"))
        with self.assertRaises(ValueError):
            self.tx.guard(A, request("update", native_member=member()))
        self.tx.direct(A, request("leave"))
        self.prepare_create(B)

    def test_invalid_leave_does_not_abort_and_reserved_search_is_hidden(self):
        self.prepare_create()
        with self.assertRaises(ValueError):
            self.tx.direct(A, {"op": "leave", "version": 999})
        self.assertEqual(self.tx.records[A].state, "prepared")
        session = self.operation(A, "commit")["session"]
        self.operation(B, "prepare", payload=request("join", session_id=session["session_id"], native_member=member("b")))
        result = self.tx.direct(C, request("search", query=query(), default_normalize=False,
                                         materialization_profile=2, limit=1))
        self.assertEqual(result["sessions"], [])

    def test_strict_validation_no_mutation_on_error(self):
        for token in ("rpc-0", "rpc-01", "rpc-2147483648", "rpc-1\n", True):
            with self.subTest(token=token), self.assertRaises(ValueError):
                self.tx.handle(A, {"version": 1, "op": "abort", "transaction_id": token})
        for payload in (request("search"), dict(request("create"), version=1), None):
            with self.assertRaises(ValueError):
                self.tx.handle(A, {"version": 1, "op": "prepare", "transaction_id": "rpc-1", "request": payload})
        self.assertEqual(self.tx.records, {})
        self.assertEqual(self.directory.sessions, {})

    def test_atomic_match_joins_existing_then_creates_independent_session(self):
        def match(owner, generation=1):
            native = data(owner[0])
            return self.operation(owner, "prepare", generation, request("match", native_data=native,
                attributes={str(i): value for i, value in enumerate(native["numeric"])},
                query=query(), default_normalize=False, create_flags=0))
        first = match(A)
        self.assertEqual(first["action"], "create")
        self.operation(A, "commit")
        second = match(B)
        self.assertEqual(second["action"], "join")
        self.assertEqual(second["session"]["session_id"], first["session"]["session_id"])
        # A second prepare may not steal B's reserved guest slot.
        third = match(C)
        self.assertEqual(third["action"], "create")
        self.operation(B, "commit")
        self.operation(C, "commit")
        self.assertEqual(len(self.directory.sessions), 2)
        self.assertEqual(len(self.directory.describe_membership(A)["members"]), 2)

    def test_simultaneous_match_prepare_retries_after_host_commits(self):
        def payload(label):
            native = data(label)
            return request("match", native_data=native, attributes={"0": -5, "1": 8},
                           query=query(), default_normalize=False, create_flags=0)
        first = self.operation(A, "prepare", payload=payload("a"))
        with self.assertRaisesRegex(ValueError, "native_match_busy"):
            self.operation(B, "prepare", payload=payload("b"))
        self.assertNotIn(B, self.tx.records)
        self.operation(A, "commit")
        second = self.operation(B, "prepare", payload=payload("b"))
        self.assertEqual(second["action"], "join")
        self.assertEqual(first["session"]["session_id"], second["session"]["session_id"])
        self.operation(B, "commit")
        self.assertEqual(len(self.directory.sessions), 1)

    def test_room_flags_are_separate_owner_only_metadata(self):
        native = data()
        session = self.tx.direct(A, request("create", native_data=native,
            attributes={"0": -5, "1": 8}, create_flags=0x80)) ["session"]
        self.assertEqual(len(search(self.directory)), 1)
        self.tx.direct(A, request("set_flags", flags=1))
        self.assertEqual(search(self.directory), [])
        changed = self.directory.describe_membership(A)
        self.assertEqual(changed["create_flags"], 0x81)
        self.assertEqual(changed["native_descriptor"], session["native_descriptor"])
        self.tx.direct(A, request("set_flags", flags=2))
        self.assertEqual(len(search(self.directory)), 1)
        self.tx.direct(B, request("join", session_id=session["session_id"], native_member=member("b")))
        with self.assertRaises(ValueError):
            self.tx.direct(B, request("set_flags", flags=0))
        self.assertEqual(self.directory.describe_membership(A)["create_flags"], 0x82)

    def test_direct_match_does_not_steal_reserved_capacity(self):
        self.directory.max_sessions = 1
        self.prepare_create()
        native = data("b")
        with self.assertRaises(ValueError):
            self.tx.direct(B, request("match", native_data=native, attributes={"0": -5, "1": 8},
                           query=query(), default_normalize=False, create_flags=0))
        self.assertEqual(self.directory.sessions, {})
