"""Server-side native numeric/session profile2; no installed provider claims."""
import base64
import copy
import json
import unittest

from native_sessions import NativeSessionDirectory, native_numeric_matches

A, B, C = (letter * 32 for letter in "abc")
PARTITION = {"build": "e" * 64, "protocol": 1, "mode": 0}


def member(label="a"):
    return {"identity_hex": [label.encode().hex(), (label + "-native").encode().hex()],
            "address_hex": b"127.0.0.1:30001".hex(), "field_88": 0,
            "optional_present": False, "optional_value": 0, "field_8b": 1}


def data(label="a", payload=b"\x00\xff\x01\x00"):
    return {"profile": 2, "compatibility": 1234, "numeric": [-5, 8], "capacity": 2,
            "field_e1": 0, "properties": [], "member": member(label),
            "stream": {"kind": "spnet-memory-v1", "data_base64": base64.b64encode(payload).decode(),
                       "read_cursor": 1, "write_cursor": len(payload)}}


def request(op, **fields):
    result = {"version": 2, "request_id": "v2-" + op, "op": op}
    if op not in ("update", "leave", "set_flags"):
        result["partition"] = dict(PARTITION)
    return dict(result, **fields)


def query(**fields):
    return dict({"compatibility": 1234, "filters": [], "compound_count": 0,
                 "compound_filters": [], "distance": 0, "field_4c": 0, "field_4d": 0,
                 "field_4e": 255}, **fields)


def predicate(key=0, comparison=0, value=-5):
    return {"key": str(key), "comparison": comparison, "value": value}


def create(directory, owner=A, label="a", native=None):
    native = data(label) if native is None else native
    return directory.handle(owner, request("create", native_data=native,
        attributes={str(i): v for i, v in enumerate(native["numeric"])}))["session"]


def search(directory, owner=B, **fields):
    return directory.handle(owner, request("search", query=query(**fields),
        default_normalize=False, materialization_profile=2, limit=1))["sessions"]


class NativeV2Tests(unittest.TestCase):
    def test_create_query_join_update_and_leave_keep_complete_payload(self):
        directory = NativeSessionDirectory()
        session = create(directory)
        descriptor = session["native_descriptor"]
        self.assertEqual(base64.b64decode(descriptor["stream"]["data_base64"]), b"\0\xff\1\0")
        self.assertEqual(descriptor["members"][0]["field_8b"], 0)
        self.assertEqual(search(directory), [session])
        joined = directory.handle(B, request("join", session_id=session["session_id"],
                                            native_member=member("b")))["session"]
        self.assertEqual([m["owner"] for m in joined["native_descriptor"]["members"]], [True, False])
        self.assertEqual([m["field_8b"] for m in joined["native_descriptor"]["members"]], [0, 0])
        self.assertEqual(search(directory, C), [])
        changed = dict(member("b"), optional_present=True, optional_value=7)
        updated = directory.handle(B, request("update", native_member=changed))["session"]
        self.assertEqual(updated["native_descriptor"]["members"][1]["optional_value"], 7)
        directory.handle(B, request("leave"))
        self.assertEqual(len(search(directory, C)), 1)
        directory.handle(A, request("leave"))
        self.assertEqual(search(directory, C), [])

    def test_signed_comparisons_all_five_and_or_pairs(self):
        candidate = data()
        for op, value, expected in ((0, -5, True), (0, 5, False), (1, -4, True),
                (1, -6, False), (2, -5, True), (3, -6, True), (3, -4, False),
                (4, -5, True), (4, -4, False)):
            with self.subTest(op=op, value=value):
                self.assertEqual(native_numeric_matches(query(filters=[predicate(0, op, value)]),
                                                       candidate, False), expected)
        pair = {"first": predicate(0, 0, 99), "second": predicate(1, 0, 8)}
        q = query(compound_count=1, compound_filters=[pair])
        self.assertTrue(native_numeric_matches(q, candidate, False))
        pair["second"]["value"] = 9
        self.assertFalse(native_numeric_matches(q, candidate, False))

    def test_missing_keys_follow_recovered_native_semantics(self):
        candidate = data()
        self.assertTrue(native_numeric_matches(query(filters=[predicate(2**64 - 1)]), candidate, False))
        for pair in ({"first": predicate(99), "second": predicate(0, 0, 99)},
                     {"first": predicate(0, 0, 99), "second": predicate(99)}):
            self.assertTrue(native_numeric_matches(query(compound_count=1, compound_filters=[pair]),
                                                   candidate, False))

    def test_compatibility_normalization_is_explicit_and_zero_bypasses(self):
        candidate = data()
        self.assertFalse(native_numeric_matches(query(compatibility=2234), candidate, False))
        self.assertTrue(native_numeric_matches(query(compatibility=2234), candidate, True))
        self.assertFalse(native_numeric_matches(query(compatibility=2234, field_4e=0), candidate, True))
        self.assertTrue(native_numeric_matches(query(compatibility=2234, field_4e=1), candidate, False))
        self.assertTrue(native_numeric_matches(query(compatibility=0), candidate, False))
        with self.assertRaises(ValueError):
            native_numeric_matches(query(), candidate, 1)

    def test_snapshot_applies_filters_not_just_pending_pairing(self):
        directory = NativeSessionDirectory()
        create(directory)
        self.assertEqual(search(directory, filters=[predicate(0, 0, 42)]), [])
        self.assertEqual(len(search(directory, filters=[predicate(0, 2, -5)])), 1)
        pair = {"first": predicate(0, 0, 99), "second": predicate(1, 0, 8)}
        self.assertEqual(len(search(directory, compound_count=1, compound_filters=[pair])), 1)

    def test_profile_isolation_duplicate_identity_and_no_mutation_on_failure(self):
        directory = NativeSessionDirectory()
        session = create(directory)
        for message in (request("join", native_member=member(), session_id=session["session_id"]),
                        dict(request("join", native_member=member("b"), session_id=session["session_id"]), version=1)):
            with self.assertRaises(ValueError):
                directory.handle(B, message)
            self.assertFalse(directory.has_membership(B))
        legacy = {"version": 1, "request_id": "v1", "op": "search", "partition": PARTITION,
                  "filters": [], "limit": 4, "materialization_profile": 1}
        self.assertEqual(directory.handle(B, legacy)["sessions"], [])

    def test_update_settings_authority_and_deep_snapshot(self):
        directory = NativeSessionDirectory()
        session = create(directory)
        directory.handle(B, request("join", native_member=member("b"), session_id=session["session_id"]))
        before = directory.describe_membership(A)
        with self.assertRaises(ValueError):
            directory.handle(B, request("update", native_member=member("b"), native_data=data("b")))
        with self.assertRaises(ValueError):
            directory.handle(B, request("update", native_member=member("other")))
        self.assertEqual(directory.describe_membership(A), before)
        updated = data(payload=b"123456")
        updated["numeric"] = [1, 2, 3]
        response = directory.handle(A, request("update", native_member=member(), native_data=updated))
        updated["numeric"].clear()
        response["session"]["native_descriptor"]["numeric"].clear()
        self.assertEqual(directory.describe_membership(A)["native_descriptor"]["numeric"], [1, 2, 3])

    def test_malformed_stream_properties_and_cursors_fail_closed(self):
        for change in ({"data_base64": "A==="}, {"data_base64": "YQ==\n"},
                       {"kind": "unknown"}, {"read_cursor": 99}, {"write_cursor": 99},
                       {"read_cursor": True}, {"data_base64": "AA==" * 2000}):
            native = data()
            native["stream"].update(change)
            directory = NativeSessionDirectory()
            with self.subTest(change=change), self.assertRaises(ValueError):
                create(directory, native=native)
            self.assertEqual(directory.sessions, {})
        native = data()
        native["properties"] = ["unknown-type"]
        with self.assertRaises(ValueError):
            create(NativeSessionDirectory(), native=native)

    def test_maximum_stream_single_result_fits_control_frame(self):
        directory = NativeSessionDirectory()
        native = data(payload=bytes(range(256)) * 16)
        native["numeric"] = [-(2**31)] * 16
        native["member"] = {**member(), "identity_hex": ["61" * 64, "62" * 64],
                            "address_hex": "63" * 64}
        create(directory, native=native)
        response = directory.handle(B, request("search", query=query(), default_normalize=False,
                                    materialization_profile=2, limit=1))
        self.assertLess(len(json.dumps(response).encode()), 8192)


if __name__ == "__main__":
    unittest.main()
