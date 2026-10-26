import copy
import json
import unittest

from native_sessions import NativeSessionDirectory, MAX_ATTRIBUTES, MAX_RESULTS


PARTITION = {"build": "e" * 64, "protocol": 1, "mode": 0}
A, B, C, D = (str(i) * 32 for i in range(1, 5))


def request(op, **kwargs):
    value = {"version": 1, "request_id": "native-test-1", "op": op}
    if op != "leave":
        value["partition"] = dict(PARTITION)
    value.update(kwargs)
    return value


def create(directory, owner=A, attributes=None):
    return directory.handle(owner, request("create", attributes=attributes or {}))["session"]


def search(directory, owner=B, **kwargs):
    return directory.handle(owner, request("search", filters=[], limit=MAX_RESULTS, **kwargs))["sessions"]


class DirectoryTests(unittest.TestCase):
    def test_create_search_join_preserves_opaque_numeric_attributes(self):
        directory = NativeSessionDirectory()
        attributes = {"0": -1, str(2**64 - 1): 2**31 - 1}
        session = create(directory, attributes=attributes)
        self.assertEqual(session["attributes"], attributes)
        self.assertNotEqual(session["session_id"], A)
        self.assertNotEqual(session["members"][0]["member_id"], A)
        query = request("search", filters=[{"key": "0", "comparison": "eq", "value": -1}], limit=1)
        self.assertEqual(directory.handle(B, query)["sessions"], [session])
        joined = directory.handle(B, request("join", session_id=session["session_id"]))["session"]
        self.assertEqual([m["join_order"] for m in joined["members"]], [0, 1])
        self.assertEqual(len({m["member_id"] for m in joined["members"]}), 2)
        self.assertEqual(search(directory, C), [])
        with self.assertRaisesRegex(ValueError, "full"):
            directory.handle(C, request("join", session_id=session["session_id"]))
        self.assertFalse(directory.has_membership(C))

    def test_partition_mismatch_and_missing_attribute_fail_closed(self):
        directory = NativeSessionDirectory()
        session = create(directory, attributes={"1": 4})
        for key, value in (("build", "d" * 64), ("protocol", 2), ("mode", 1)):
            partition = dict(PARTITION, **{key: value})
            self.assertEqual(search(directory, partition=partition), [])
            with self.assertRaisesRegex(ValueError, "unavailable"):
                directory.handle(B, request("join", partition=partition, session_id=session["session_id"]))
        query = request("search", filters=[{"key": "2", "comparison": "eq", "value": 0}], limit=1)
        self.assertEqual(directory.handle(B, query)["sessions"], [])

    def test_guest_departure_reopens_creator_departure_revokes(self):
        directory = NativeSessionDirectory()
        session = create(directory)
        directory.handle(B, request("join", session_id=session["session_id"]))
        self.assertEqual(set(directory.member_owners(A)), {A, B})
        self.assertEqual(directory.disconnect(B), (A,))
        self.assertEqual(search(directory, C)[0]["session_id"], session["session_id"])
        directory.handle(C, request("join", session_id=session["session_id"]))
        self.assertEqual(directory.disconnect(A), (C,))
        self.assertFalse(directory.has_membership(A))
        self.assertFalse(directory.has_membership(C))
        self.assertEqual(directory.sessions, {})
        self.assertEqual(directory.disconnect(A), ())
        self.assertEqual(directory.member_owners(A), ())
        # A revoked member is free to create a new session.
        create(directory, C)

    def test_leave_only_affects_requesting_connection(self):
        directory = NativeSessionDirectory()
        session = create(directory)
        directory.handle(B, request("join", session_id=session["session_id"]))
        response = directory.handle(C, request("leave"))
        self.assertFalse(response["left"])
        self.assertTrue(directory.has_membership(A))
        self.assertTrue(directory.has_membership(B))
        self.assertEqual(directory.handle(B, request("leave"))["left"], True)
        self.assertTrue(directory.has_membership(A))
        self.assertNotIn(A, json.dumps(response))
        self.assertNotIn("affected_owners", response)

    def test_no_double_membership_or_implicit_destructive_replacement(self):
        directory = NativeSessionDirectory()
        session = create(directory)
        other = create(directory, B)
        for operation in (request("create", attributes={}),
                          request("join", session_id=other["session_id"]),
                          request("join", session_id=session["session_id"])):
            with self.assertRaisesRegex(ValueError, "already"):
                directory.handle(A, operation)
            self.assertEqual(directory.memberships[A], session["session_id"])
        self.assertEqual(len(directory.sessions), 2)

    def test_snapshots_have_no_mutable_aliases(self):
        directory = NativeSessionDirectory()
        attributes = {"1": 42}
        message = request("create", attributes=attributes)
        created = directory.handle(A, message)["session"]
        message["partition"]["mode"] = 99
        attributes["1"] = 7
        created["attributes"]["1"] = 3
        created["members"].clear()
        snapshot = search(directory)[0]
        self.assertEqual(snapshot["attributes"], {"1": 42})
        self.assertEqual(snapshot["partition"], PARTITION)
        self.assertEqual(len(snapshot["members"]), 1)
        snapshot["attributes"]["1"] = -5
        self.assertEqual(search(directory)[0]["attributes"], {"1": 42})
        membership = directory.describe_membership(A)
        membership["members"].clear()
        self.assertEqual(len(directory.describe_membership(A)["members"]), 1)
        self.assertIsNone(directory.describe_membership(B))

    def test_capacity_and_bounded_serialized_search(self):
        directory = NativeSessionDirectory(max_sessions=4)
        attributes = {str(2**64 - 1 - i): -(2**31) for i in range(MAX_ATTRIBUTES)}
        for i in range(4):
            create(directory, f"{i + 1:032x}", attributes)
        with self.assertRaisesRegex(ValueError, "full"):
            create(directory, "f" * 32)
        response = directory.handle("e" * 32, request("search", filters=[], limit=MAX_RESULTS))
        self.assertEqual(len(response["sessions"]), MAX_RESULTS)
        self.assertLess(len(json.dumps(response).encode()), 8192)

    def test_strict_schema_spoof_and_type_rejection_without_mutation(self):
        good = request("create", attributes={"0": 0})
        bad = []
        for key, value in (("owner_id", A), ("member_id", B), ("session_id", "a" * 32),
                           ("capacity", 99), ("version", True), ("version", 2),
                           ("request_id", "x" * 65), ("request_id", "line\nbreak"),
                           ("op", []), ("op", "cancel"), ("attributes", {"00": 0}),
                           ("attributes", {str(2**64): 0}), ("attributes", {"0": True}),
                           ("attributes", {"0": 2**31}), ("attributes", {"0": -(2**31) - 1}),
                           ("attributes", {str(i): 0 for i in range(MAX_ATTRIBUTES + 1)})):
            bad.append(dict(good, **{key: value}))
        for key, value in (("build", "E" * 64), ("protocol", True), ("protocol", 0),
                           ("mode", -1), ("mode", 2**32), ("extra", 0)):
            bad.append(dict(good, partition=dict(PARTITION, **{key: value})))
        bad.extend(([], None, {"version": 1}, dict(good, partition=None)))
        for message in bad:
            directory = NativeSessionDirectory()
            with self.subTest(message=message), self.assertRaises(ValueError):
                directory.handle(A, message)
            self.assertEqual(directory.sessions, {})
            self.assertEqual(directory.memberships, {})

    def test_unsupported_or_duplicate_search_filters_and_limits(self):
        directory = NativeSessionDirectory()
        create(directory)
        base = request("search", filters=[], limit=1)
        filter_ = {"key": "1", "comparison": "eq", "value": 2}
        for value in ([dict(filter_, comparison=0)], [dict(filter_, comparison="lt")],
                      [filter_, filter_], [dict(filter_, owner_id=A)], [None],
                      [dict(filter_, value=True)], [filter_] * (MAX_ATTRIBUTES + 1), {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                directory.handle(B, dict(base, filters=value))
        for value in (0, MAX_RESULTS + 1, True, "1"):
            with self.assertRaises(ValueError):
                directory.handle(B, dict(base, limit=value))
        for owner in ("", "a" * 31, True, A.upper()):
            # Numeric A remains unchanged by upper(); use alpha to test case.
            if owner == A:
                continue
            with self.assertRaises(ValueError):
                directory.handle(owner, base)
        with self.assertRaises(ValueError):
            directory.handle("A" * 32, base)


def member(**changes):
    return dict(identity_hex=["616263", "646566"], address_hex="3132372e302e302e313a3237",
                field_88=3, optional_present=False, optional_value=5, field_8b=7, **changes)


def native_data():
    return {"profile": 1, "compatibility": 42, "numeric": [-1, 5], "capacity": 2,
            "field_e1": 9, "stream": None, "properties": [], "member": member()}


def native_create(directory, owner=A, data=None):
    data = native_data() if data is None else data
    return directory.handle(owner, request("create", native_data=data,
                            attributes={str(i): value for i, value in enumerate(data["numeric"])}))["session"]


class MaterializationProfileTests(unittest.TestCase):
    def test_server_generates_ids_ownership_and_preserves_native_values(self):
        directory = NativeSessionDirectory()
        session = native_create(directory)
        descriptor = session["native_descriptor"]
        self.assertEqual(descriptor["id"], session["session_id"])
        self.assertEqual(descriptor["numeric"], [-1, 5])
        self.assertEqual(descriptor["compatibility"], 42)
        self.assertEqual(descriptor["field_e1"], 9)
        self.assertIsNone(descriptor["stream"])
        self.assertEqual(descriptor["properties"], [])
        self.assertNotIn("member", descriptor)
        creator = descriptor["members"][0]
        self.assertEqual(creator["id"], session["members"][0]["member_id"])
        self.assertEqual(creator["join_order"], 0)
        self.assertTrue(creator["owner"])
        for key, value in member().items():
            self.assertEqual(creator[key], value)

    def test_search_profile_separates_legacy_and_materialized(self):
        directory = NativeSessionDirectory()
        native = native_create(directory)
        legacy = create(directory, C)
        self.assertEqual([s["session_id"] for s in search(directory, B)], [legacy["session_id"]])
        results = directory.handle(B, request("search", filters=[], limit=4,
                                              materialization_profile=1))["sessions"]
        self.assertEqual([s["session_id"] for s in results], [native["session_id"]])
        self.assertNotIn("native_descriptor", directory.describe_membership(C))

    def test_join_requires_native_member_and_assigns_guest_fields(self):
        directory = NativeSessionDirectory()
        session = native_create(directory)
        join = request("join", session_id=session["session_id"])
        with self.assertRaisesRegex(ValueError, "requires native_member"):
            directory.handle(B, join)
        self.assertFalse(directory.has_membership(B))
        joined = directory.handle(B, dict(join, native_member=member()))["session"]
        self.assertEqual([m["join_order"] for m in joined["native_descriptor"]["members"]], [0, 1])
        self.assertEqual([m["owner"] for m in joined["native_descriptor"]["members"]], [True, False])
        self.assertEqual(len({m["id"] for m in joined["native_descriptor"]["members"]}), 2)

    def test_legacy_join_rejects_native_member(self):
        directory = NativeSessionDirectory()
        session = create(directory)
        with self.assertRaisesRegex(ValueError, "does not accept"):
            directory.handle(B, request("join", session_id=session["session_id"], native_member=member()))
        self.assertFalse(directory.has_membership(B))

    def test_member_spoof_fields_and_invalid_bytes_rejected_atomically(self):
        bad = []
        for key, value in (("id", "a" * 32), ("owner", True), ("join_order", 0),
                           ("identity_hex", ["61"]), ("identity_hex", ["61", ""]),
                           ("identity_hex", ["AB", "61"]), ("address_hex", "a"),
                           ("address_hex", "aa" * 65), ("address_hex", ""),
                           ("address_hex", "610062"), ("address_hex", "gg"),
                           ("field_88", True), ("field_88", -1), ("field_8b", 256),
                           ("optional_present", 1), ("optional_value", 256)):
            value_ = member()
            value_[key] = value
            bad.append(value_)
        missing = member()
        del missing["optional_value"]
        bad.append(missing)
        for value in bad:
            directory = NativeSessionDirectory()
            data = native_data()
            data["member"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                native_create(directory, data=data)
            self.assertEqual(directory.sessions, {})
            self.assertEqual(directory.memberships, {})

    def test_native_data_unsupported_fields_and_bounds_fail_closed(self):
        for key, value in (("profile", True), ("profile", 2), ("capacity", True),
                           ("capacity", 1), ("compatibility", -1), ("compatibility", 2**32),
                           ("field_e1", 256), ("stream", "aa"), ("stream", {}),
                           ("properties", [{}]), ("properties", {}), ("properties", None),
                           ("numeric", [True]), ("numeric", [2**31]), ("numeric", [0] * 17),
                           ("numeric", {}), ("unknown", 1)):
            directory = NativeSessionDirectory()
            data = native_data()
            data[key] = value
            # Keep malformed numeric unchanged while supplying an unrelated
            # valid attributes object; production validation must reject it.
            message = request("create", attributes={}, native_data=data)
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                directory.handle(A, message)
            self.assertEqual(directory.sessions, {})
        for key in native_data():
            data = native_data()
            del data[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                NativeSessionDirectory().handle(A, request("create", attributes={}, native_data=data))

    def test_attributes_must_exactly_index_native_numeric(self):
        for attributes in ({}, {"0": -1}, {"0": -1, "1": 6}, {"0": -1, "1": 5, "2": 0},
                           {"1": -1, "2": 5}):
            with self.subTest(attributes=attributes), self.assertRaisesRegex(ValueError, "exactly index"):
                NativeSessionDirectory().handle(A, request("create", attributes=attributes,
                                                           native_data=native_data()))

    def test_malformed_join_does_not_mutate_existing_membership(self):
        directory = NativeSessionDirectory()
        session = native_create(directory)
        before = directory.describe_membership(A)
        spoofed = dict(member(), owner=True)
        with self.assertRaises(ValueError):
            directory.handle(B, request("join", session_id=session["session_id"], native_member=spoofed))
        self.assertEqual(directory.describe_membership(A), before)
        self.assertFalse(directory.has_membership(B))

    def test_disconnect_releases_native_metadata_and_allows_rejoin(self):
        directory = NativeSessionDirectory()
        session = native_create(directory)
        directory.handle(B, request("join", session_id=session["session_id"], native_member=member()))
        old_id = directory.describe_membership(B)["native_descriptor"]["members"][1]["id"]
        directory.disconnect(B)
        self.assertNotIn(B, directory.sessions[session["session_id"]].native_members)
        joined = directory.handle(C, request("join", session_id=session["session_id"],
                                            native_member=member()))["session"]
        self.assertNotEqual(joined["native_descriptor"]["members"][1]["id"], old_id)
        self.assertEqual(directory.disconnect(A), (C,))
        self.assertEqual(directory.sessions, {})

    def test_input_and_output_native_snapshots_are_independent(self):
        directory = NativeSessionDirectory()
        data = native_data()
        expected = copy.deepcopy(data)
        session = native_create(directory, data=data)
        data["numeric"].clear()
        data["member"]["identity_hex"][0] = "ff"
        session["native_descriptor"]["members"][0]["identity_hex"].clear()
        session["native_descriptor"]["numeric"][0] = 100
        snapshot = directory.describe_membership(A)["native_descriptor"]
        self.assertEqual(snapshot["numeric"], expected["numeric"])
        self.assertEqual(snapshot["members"][0]["identity_hex"], expected["member"]["identity_hex"])
        incoming = member()
        directory.handle(B, request("join", session_id=session["session_id"], native_member=incoming))
        incoming["identity_hex"].clear()
        self.assertEqual(len(directory.describe_membership(A)["native_descriptor"]["members"][1]["identity_hex"]), 2)

    def test_materialization_profile_search_validation(self):
        directory = NativeSessionDirectory()
        for value in (None, True, 0, 2, "1", {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                directory.handle(A, request("search", filters=[], limit=1, materialization_profile=value))

    def test_maximum_native_search_response_is_bounded(self):
        directory = NativeSessionDirectory()
        data = native_data()
        data["numeric"] = [-(2**31)] * MAX_ATTRIBUTES
        data["compatibility"] = 2**32 - 1
        data["field_e1"] = 255
        data["member"] = {"identity_hex": ["ff" * 64] * 2, "address_hex": "ff" * 64,
                          "field_88": 255, "optional_present": False,
                          "optional_value": 255, "field_8b": 255}
        for i in range(MAX_RESULTS):
            native_create(directory, f"{i + 1:032x}", data)
        response = directory.handle("f" * 32, request("search", filters=[], limit=MAX_RESULTS,
                                                     materialization_profile=1,
                                                     request_id="x" * 64))
        self.assertEqual(len(response["sessions"]), MAX_RESULTS)
        self.assertLess(len(json.dumps(response).encode()), 8192)


if __name__ == "__main__":
    unittest.main()
