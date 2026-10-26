"""Existing profile2 room policy, not proof of native lobby UI support.

The native flags are deliberately unnamed: bits selected by mask5 suppress
discovery, while a known session ID can still be joined. Numeric slot/value
examples remain opaque and are NOT recovered ranked/casual game enums.
"""
import copy
import unittest

from native_sessions import NativeSessionDirectory
from native_session_transactions import NativeSessionTransactions
from test_native_sessions_v2 import A, B, C, data, member, predicate, query, request


def room_request(label="a", flags=0, value=17):
    native = data(label)
    native["numeric"] = [value, -9]
    return request("create", native_data=native, create_flags=flags,
                   attributes={"0": value, "1": -9})


def discovery(value=None):
    filters = [] if value is None else [predicate(0, 0, value)]
    return request("search", query=query(filters=filters),
                   default_normalize=False, materialization_profile=2, limit=1)


def matching(label="b", value=17):
    result = room_request(label, value=value)
    result.update(op="match", query=query(filters=[predicate(0, 0, value)]),
                  default_normalize=False)
    return result


class NativeRoomModeTests(unittest.TestCase):
    def test_discovery_uses_exact_flags_mask_not_blanket_nonzero_check(self):
        for flags in (*range(16), 0x28, 0x80, 0x100, 0x8000, 0xffff):
            with self.subTest(flags=flags):
                directory = NativeSessionDirectory()
                created = directory.handle(A, room_request(flags=flags))["session"]
                expected = [] if flags & 5 else [created]
                self.assertEqual(directory.handle(B, discovery())["sessions"], expected)

    def test_hidden_room_known_id_join_preserves_transaction_visibility(self):
        for flags in (1, 4, 5, 0x85):
            with self.subTest(flags=flags):
                directory = NativeSessionDirectory()
                transaction = NativeSessionTransactions(directory)
                original = transaction.direct(A, room_request(flags=flags))["session"]
                sid = original["session_id"]
                self.assertEqual(transaction.direct(B, discovery())["sessions"], [])
                join = request("join", session_id=sid, native_member=member("b"))
                prepared = transaction.handle(B, {"version": 1, "op": "prepare",
                    "transaction_id": "rpc-1", "request": join})
                self.assertEqual(prepared["action"], "join")
                self.assertEqual(len(prepared["session"]["members"]), 2)
                self.assertEqual(directory.describe_membership(A), original)
                self.assertFalse(directory.has_membership(B))
                self.assertIsNone(directory.relay_peer(A, sid))
                committed = transaction.handle(B, {"version": 1, "op": "commit",
                                                   "transaction_id": "rpc-1"})["session"]
                self.assertEqual(committed["session_id"], sid)
                self.assertEqual(committed["create_flags"], flags)
                self.assertEqual(committed["native_descriptor"]["stream"],
                                 original["native_descriptor"]["stream"])
                self.assertEqual(directory.relay_peer(A, sid), B)
                self.assertEqual(directory.relay_peer(B, sid), A)

    def test_owner_only_flags_toggle_visibility_without_descriptor_edits(self):
        directory = NativeSessionDirectory()
        original = directory.handle(A, room_request(flags=0x80))["session"]
        changed = directory.handle(A, request("set_flags", flags=1))["session"]
        self.assertEqual(changed["create_flags"], 0x81)
        self.assertEqual(changed["native_descriptor"], original["native_descriptor"])
        self.assertEqual(directory.handle(B, discovery())["sessions"], [])
        changed = directory.handle(A, request("set_flags", flags=2))["session"]
        self.assertEqual(changed["create_flags"], 0x82)
        self.assertEqual(directory.handle(B, discovery())["sessions"], [changed])
        directory.handle(B, request("join", session_id=original["session_id"],
                                    native_member=member("b")))
        before = copy.deepcopy(directory.describe_membership(A))
        for owner in (B, C):
            with self.subTest(owner=owner), self.assertRaises(ValueError):
                directory.handle(owner, request("set_flags", flags=0))
            self.assertEqual(directory.describe_membership(A), before)

    def test_join_or_create_respects_same_visibility_policy_as_discovery(self):
        for flags in (0, 1, 2, 4, 5, 0x28, 0x80):
            with self.subTest(flags=flags):
                directory = NativeSessionDirectory()
                host = directory.handle(A, room_request(flags=flags))["session"]
                found = directory.handle(B, matching())
                if flags & 5:
                    self.assertEqual(found["action"], "create")
                    self.assertNotEqual(found["session"]["session_id"], host["session_id"])
                    self.assertEqual(len(directory.describe_membership(A)["members"]), 1)
                else:
                    self.assertEqual(found["action"], "join")
                    self.assertEqual(found["session"]["session_id"], host["session_id"])
                    self.assertEqual(len(found["session"]["members"]), 2)

    def test_explicit_opaque_numeric_slot_segregates_search_and_matching(self):
        directory = NativeSessionDirectory()
        first = directory.handle(A, room_request(value=17))["session"]
        second = directory.handle(B, room_request("b", value=29))["session"]
        for value, expected in ((17, first), (29, second), (31, None)):
            with self.subTest(value=value):
                sessions = directory.handle(C, discovery(value))["sessions"]
                self.assertEqual(sessions, [] if expected is None else [expected])
        joined = directory.handle(C, matching("c", value=29))
        self.assertEqual(joined["action"], "join")
        self.assertEqual(joined["session"]["session_id"], second["session_id"])
        self.assertEqual(len(directory.describe_membership(A)["members"]), 1)
        self.assertEqual(joined["session"]["native_descriptor"]["numeric"], [29, -9])

    def test_known_id_does_not_override_build_protocol_or_partition(self):
        directory = NativeSessionDirectory()
        host = directory.handle(A, room_request(flags=1))["session"]
        for key, value in (("build", "f" * 64), ("protocol", 2), ("mode", 1)):
            join = request("join", session_id=host["session_id"], native_member=member("b"))
            join["partition"][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "unavailable"):
                directory.handle(B, join)
            self.assertFalse(directory.has_membership(B))
            self.assertEqual(directory.describe_membership(A), host)

    def test_hidden_room_join_does_not_bypass_capacity_or_host_departure(self):
        directory = NativeSessionDirectory()
        host = directory.handle(A, room_request(flags=5))["session"]
        sid = host["session_id"]
        directory.handle(B, request("join", session_id=sid, native_member=member("b")))
        with self.assertRaisesRegex(ValueError, "full"):
            directory.handle(C, request("join", session_id=sid, native_member=member("c")))
        self.assertFalse(directory.has_membership(C))
        self.assertEqual(directory.handle(C, discovery())["sessions"], [])
        directory.handle(A, request("leave"))
        self.assertFalse(directory.has_membership(B))
        self.assertIsNone(directory.relay_peer(B, sid))
        with self.assertRaisesRegex(ValueError, "unavailable"):
            directory.handle(C, request("join", session_id=sid, native_member=member("c")))


if __name__ == "__main__":
    unittest.main()
