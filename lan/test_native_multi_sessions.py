"""Bounded eight-participant directory/transaction contracts, not game proof."""
import copy
import unittest

from lan_identity import MULTI_PROTOCOL, principal, translate_request, validate_descriptor, validate_peer_request
from native_session_codec import encode_descriptor
from native_session_transactions import NativeSessionTransactions
from native_sessions import NativeSessionDirectory
from test_native_sessions_v2 import data, member, query, request


class MultiSessionTests(unittest.TestCase):
    def command(self, owner, op, **fields):
        return translate_request(request(op, **fields), owner, protocol=MULTI_PROTOCOL)

    def create(self, directory, owner):
        native = data(owner)
        native["capacity"] = 8
        command = self.command(owner, "create", native_data=native,
                               attributes={str(i): n for i, n in enumerate(native["numeric"])})
        validate_peer_request(directory, owner, command)
        return directory.handle(owner, command)["session"]

    def test_eight_members_full_search_reopen_and_legacy_partition_refusal(self):
        directory = NativeSessionDirectory()
        owners = [f"{i+1:032x}" for i in range(9)]
        created = self.create(directory, owners[0])
        sid = created["session_id"]
        for index, owner in enumerate(owners[1:8], 1):
            found = directory.handle(owner, self.command(owner, "search", query=query(),
                default_normalize=False, materialization_profile=2, limit=1))["sessions"]
            self.assertEqual(len(found), 1)
            self.assertEqual(len(found[0]["members"]), index)
            joined = directory.handle(owner, self.command(owner, "join", session_id=sid,
                                                         native_member=member(owner)))["session"]
            self.assertEqual(joined["capacity"], 8)
            self.assertEqual(len(joined["members"]), index+1)
            validate_descriptor(joined["native_descriptor"], max_members=8)
            self.assertTrue(encode_descriptor(joined["native_descriptor"], version=4).startswith(b"SESSION4 "))
        before = copy.deepcopy(directory.sessions)
        with self.assertRaisesRegex(ValueError, "full"):
            directory.handle(owners[8], self.command(owners[8], "join", session_id=sid,
                                                    native_member=member(owners[8])))
        self.assertEqual(directory.sessions, before)
        self.assertEqual(directory.handle(owners[8], self.command(owners[8], "search", query=query(),
            default_normalize=False, materialization_profile=2, limit=1))["sessions"], [])
        directory.disconnect(owners[3])
        directory.handle(owners[8], self.command(owners[8], "join", session_id=sid,
                                               native_member=member(owners[8])))
        self.assertEqual(len(directory.member_owners(owners[0])), 8)
        native = data("old");native["capacity"] = 8
        with self.assertRaisesRegex(ValueError, "partition"):
            directory.handle("e"*32, request("create", native_data=native,
                                            attributes={str(i): n for i, n in enumerate(native["numeric"])}))

    def test_prepared_joins_commit_incrementally_and_preserve_ownership(self):
        directory = NativeSessionDirectory()
        owners = [f"{i+1:032x}" for i in range(8)]
        sid = self.create(directory, owners[0])["session_id"]
        tx = NativeSessionTransactions(directory)
        for index, owner in enumerate(owners[1:], 1):
            payload = self.command(owner, "join", session_id=sid, native_member=member(owner))
            prepared = tx.handle(owner, {"version": 1, "op": "prepare", "transaction_id": "rpc-1", "request": payload})
            self.assertEqual(len(directory.member_owners(owners[0])), index)
            self.assertEqual(len(prepared["session"]["members"]), index+1)
            tx.handle(owner, {"version": 1, "op": "commit", "transaction_id": "rpc-1"})
            self.assertEqual(len(directory.member_owners(owner)), index+1)
        for owner in owners:
            snapshot = directory.describe_membership(owner)
            self.assertEqual(sum(m["owner"] for m in snapshot["native_descriptor"]["members"]), 1)
        directory.disconnect(owners[0])
        self.assertFalse(directory.sessions)
        self.assertFalse(directory.memberships)

    def test_capacity_shrink_and_identity_spoof_are_atomic(self):
        directory = NativeSessionDirectory()
        owners = [f"{i+1:032x}" for i in range(3)]
        sid = self.create(directory, owners[0])["session_id"]
        for owner in owners[1:]:
            directory.handle(owner, self.command(owner, "join", session_id=sid, native_member=member(owner)))
        snapshot = directory.describe_membership(owners[0])
        native = data(owners[0]);native["capacity"] = 2
        command = self.command(owners[0], "update", native_data=native, native_member=member(owners[0]))
        with self.assertRaisesRegex(ValueError, "current participants"):
            directory.handle(owners[0], command)
        self.assertEqual(snapshot, directory.describe_membership(owners[0]))
        command = self.command(owners[1], "update", native_member=member(owners[1]))
        command["native_member"]["identity_hex"][0] = principal(owners[0]).hex()
        with self.assertRaisesRegex(ValueError, "this connection"):
            validate_peer_request(directory, owners[1], command)


if __name__ == "__main__":
    unittest.main()
