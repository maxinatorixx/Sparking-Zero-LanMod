"""Server response -> C construction core; synthetic native factory, no game.

ctypes bindings below are TEST-ONLY, not an installed client-side decoder.
"""
import ctypes as c
import copy
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest

from native_sessions import NativeSessionDirectory


class Text(c.Structure):
    _fields_ = [("data", c.c_void_p), ("size", c.c_size_t)]


class Member(c.Structure):
    _fields_ = [("id", Text), ("identity", Text * 2), ("address", Text),
                ("join_order", c.c_uint64), ("field_88", c.c_uint8),
                ("optional_present", c.c_uint8), ("optional_value", c.c_uint8),
                ("field_8b", c.c_uint8), ("owner", c.c_uint8)]


class Data(c.Structure):
    _fields_ = [("profile", c.c_uint32), ("id", Text), ("compatibility", c.c_uint32),
                ("numeric", c.POINTER(c.c_int32)), ("numeric_count", c.c_size_t),
                ("members", c.POINTER(Member)), ("member_count", c.c_size_t),
                ("capacity", c.c_uint8), ("field_e1", c.c_uint8),
                ("has_stream", c.c_uint8), ("has_properties", c.c_uint8)]


class Result(c.Structure):
    _fields_ = [("tag", c.c_uint32), ("padding", c.c_uint32),
                ("payload", c.c_size_t * 5)]


@unittest.skipUnless(platform.system() == "Linux" and shutil.which("gcc"),
                     "requires Linux C compiler for synthetic shared fixture")
class ServerToMaterializerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="szero-materializer-")
        cls.addClassCleanup(cls.temporary.cleanup)
        native = Path(__file__).resolve().parent / "native"
        library = Path(cls.temporary.name) / "fixture.so"
        subprocess.run(["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC",
                        str(native / "session_materializer.c"),
                        str(native / "native_session_wire.c"),
                        str(native / "test_session_materializer.c"), "-o", str(library)],
                       check=True, capture_output=True)
        cls.library = c.CDLL(str(library))
        cls.construct = cls.library.szero_fixture_materialize
        cls.construct.argtypes = [c.POINTER(Data), c.POINTER(Result)]
        cls.construct.restype = c.c_int

    def descriptor(self, joined=False):
        directory = NativeSessionDirectory()
        partition = {"build": "e54e79e756f79719f09915078a37b6e87c23d32ecaaaa2f485d1a048ba198e55",
                     "protocol": 1, "mode": 0}
        member = {"identity_hex": [b"preserved-native-identity".hex(), b"second-identity".hex()],
                  "address_hex": b"127.0.0.1:33001".hex(), "field_88": 5,
                  "optional_present": True, "optional_value": 7, "field_8b": 9}
        native = {"profile": 1, "compatibility": 1234, "numeric": [-1, 5, 42],
                  "capacity": 2, "field_e1": 11, "stream": None, "properties": [],
                  "member": member}
        response = directory.handle("a" * 32, {"version": 1, "request_id": "create-1",
                    "op": "create", "partition": partition,
                    "attributes": {"0": -1, "1": 5, "2": 42}, "native_data": native})
        if joined:
            response = directory.handle("b" * 32, {"version": 1, "request_id": "join-1",
                "op": "join", "partition": partition,
                "session_id": response["session"]["session_id"], "native_member": member})
        # Exercise the actual server JSON representation, not shared aliases.
        return json.loads(json.dumps(response))["session"]["native_descriptor"]

    def materialize(self, descriptor):
        storage = []

        def text(value):
            buffer = c.create_string_buffer(value)
            storage.append(buffer)
            return Text(c.addressof(buffer), len(value))

        data = Data()
        data.profile = descriptor["profile"]
        data.id = text(descriptor["id"].encode("ascii"))
        data.compatibility = descriptor["compatibility"]
        numbers = (c.c_int32 * len(descriptor["numeric"]))(*descriptor["numeric"])
        data.numeric, data.numeric_count = numbers, len(numbers)
        members = (Member * len(descriptor["members"]))()
        for index, item in enumerate(descriptor["members"]):
            member = members[index]
            member.id = text(item["id"].encode("ascii"))
            for which in range(2):
                member.identity[which] = text(bytes.fromhex(item["identity_hex"][which]))
            member.address = text(bytes.fromhex(item["address_hex"]))
            for key in ("join_order", "field_88", "optional_present", "optional_value", "field_8b", "owner"):
                setattr(member, key, item[key])
        data.members, data.member_count = members, len(members)
        data.capacity, data.field_e1 = descriptor["capacity"], descriptor["field_e1"]
        data.has_stream = descriptor["stream"] is not None
        data.has_properties = bool(descriptor["properties"])
        result = Result()
        code = self.construct(c.byref(data), c.byref(result))
        return code, result

    def test_created_server_descriptor_reaches_constructor(self):
        code, result = self.materialize(self.descriptor())
        self.assertEqual(code, 0)
        self.assertEqual(result.tag, 2)
        self.assertTrue(result.payload[0] and result.payload[1])

    def test_joined_server_descriptor_reaches_constructor_with_two_members(self):
        code, result = self.materialize(self.descriptor(joined=True))
        self.assertEqual(code, 0)
        self.assertEqual(result.tag, 2)

    def test_eight_member_linked_list_reaches_factory_without_truncation(self):
        descriptor = self.descriptor()
        template = descriptor["members"][0]
        descriptor["capacity"] = 8
        descriptor["members"] = []
        for index in range(8):
            row = copy.deepcopy(template)
            row.update(id=f"{index+1:032x}", join_order=index, owner=index == 0)
            descriptor["members"].append(row)
        code, result = self.materialize(descriptor)
        self.assertEqual(code, 0)
        self.assertEqual(result.tag, 2)
        descriptor["capacity"] = 7
        self.assertEqual(self.materialize(descriptor)[0], 1)

    def test_unsupported_extra_data_cannot_be_dropped_by_constructor(self):
        for field, value in (("stream", "01"), ("properties", [1]), ("profile", 0)):
            descriptor = self.descriptor()
            descriptor[field] = value
            code, result = self.materialize(descriptor)
            self.assertEqual(code, 2)
            self.assertEqual(result.tag, 0)


if __name__ == "__main__":
    unittest.main()
