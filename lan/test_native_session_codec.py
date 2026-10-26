"""Compiled SESSION3 contracts. No native game callbacks are executed."""
from pathlib import Path
import copy
import base64
import json
import platform
import shutil
import subprocess
import tempfile
import unittest

from native_session_codec import encode_descriptor
from native_sessions import NativeSessionDirectory
from test_native_sessions_v2 import B, create, data, member, request


@unittest.skipUnless(platform.machine().lower() in ("x86_64", "amd64") and shutil.which("gcc"),
                     "requires x64 C compiler for native descriptor layout")
class NativeSessionCodecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="szero-session-codec-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.executable = Path(cls.temporary.name) / "codec-contract"
        native = Path(__file__).resolve().parent / "native"
        result = subprocess.run([
            "gcc", "-std=c11", "-Wall", "-Wextra", "-Werror",
            str(native / "native_session_codec.c"),
            str(native / "test_native_session_codec.c"), "-o", str(cls.executable)],
            capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)

    def decode(self, frame):
        return subprocess.run([str(self.executable), "--decode"], input=frame,
                              capture_output=True, timeout=10)

    def test_compiled_parser_contracts(self):
        result = subprocess.run([str(self.executable)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("owned data only", result.stdout)

    def test_stdin_path_uses_same_bounded_parser(self):
        frame = ("SESSION3 " + "a" * 32 + " 12 0 2 0 0 0 0 0 - 1 " +
                 "b" * 32 + " 0 78 79 7a 0 0 0 0 1\n").encode("ascii")
        result = self.decode(frame)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b"12 0 1 0 0 0 0\n\n")
        for malformed in (frame + b"\n", frame[:-1], frame.replace(b" 12 ", b" 012 "),
                          b"x" * 16385):
            self.assertEqual(self.decode(malformed).returncode, 2)

    def descriptor(self, payload=b"\x00\xff\x01\x00", joined=True):
        directory = NativeSessionDirectory()
        session = create(directory, native=data(payload=payload))
        if joined:
            session = directory.handle(B, request("join", session_id=session["session_id"],
                                                 native_member=member("b")))["session"]
        return json.loads(json.dumps(session))["native_descriptor"]

    def test_server_json_encoder_reaches_actual_c_parser_without_payload_loss(self):
        for payload, joined in ((b"\0\xff\1\0", True), (bytes(range(256)) * 16, False)):
            with self.subTest(size=len(payload), joined=joined):
                descriptor = self.descriptor(payload, joined)
                unchanged = copy.deepcopy(descriptor)
                frame = encode_descriptor(descriptor)
                self.assertEqual(descriptor, unchanged)
                self.assertLessEqual(len(frame), 16384)
                result = self.decode(frame)
                self.assertEqual(result.returncode, 0, result.stderr)
                expected = f"1234 2 {2 if joined else 1} 1 {len(payload)} 1 {len(payload)}\n"
                self.assertEqual(result.stdout, expected.encode("ascii") + payload.hex().encode("ascii") + b"\n")
                self.assertTrue(all(item["field_8b"] == 0 for item in descriptor["members"]))

    def test_encoder_rejects_malformed_or_ambiguous_server_data(self):
        original = self.descriptor()
        changes = [
            lambda d: d.update(id="A" * 32),
            lambda d: d.update(profile=1),
            lambda d: d.update(properties=["unknown-type"]),
            lambda d: d.update(numeric=[0] * 17),
            lambda d: d["members"][1].update(id=d["members"][0]["id"]),
            lambda d: d["members"][1].update(join_order=0),
            lambda d: d["members"][1].update(owner=True),
            lambda d: d["members"][0].update(owner=False),
            lambda d: d["members"][0].update(field_8b=1),
            lambda d: d["members"][0].update(identity_hex=["00", "61"]),
            lambda d: d["stream"].update(data_base64="AA==\n"),
        ]
        for change in changes:
            descriptor = copy.deepcopy(original)
            change(descriptor)
            with self.subTest(change=change), self.assertRaises(ValueError):
                encode_descriptor(descriptor)

    def test_session4_eight_members_and_legacy_isolation(self):
        descriptor = self.descriptor(joined=False)
        source = descriptor["members"][0]
        descriptor["capacity"] = 8
        descriptor["members"] = []
        for index in range(8):
            row = copy.deepcopy(source)
            row.update(id=f"{index+1:032x}", join_order=index, owner=index == 0,
                       identity_hex=[f"szlan:{index+1:032x}".encode().hex(), f"player{index}".encode().hex()],
                       address_hex=f"127.0.0.1:{30000+index}".encode().hex())
            descriptor["members"].append(row)
        frame = encode_descriptor(descriptor, version=4)
        result = self.decode(frame)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"1234 2 8 1 4 1 4", result.stdout)
        self.assertEqual(self.decode(frame.replace(b"SESSION4", b"SESSION3", 1)).returncode, 2)
        with self.assertRaises(ValueError):
            encode_descriptor(descriptor)
        descriptor["members"][7]["id"] = descriptor["members"][0]["id"]
        with self.assertRaises(ValueError):
            encode_descriptor(descriptor, version=4)
        # Nonadjacent duplicate IDs must also be refused by the C decoder.
        altered = frame.replace(b"00000000000000000000000000000008 7", b"00000000000000000000000000000001 7")
        self.assertEqual(self.decode(altered).returncode, 2)
        descriptor["members"][7]["id"] = "00000000000000000000000000000008"
        for index, row in enumerate(descriptor["members"]):
            row["identity_hex"] = [(bytes([65+index])*64).hex(), (b"n"*64).hex()]
            row["address_hex"] = (b"a"*64).hex()
        descriptor["stream"].update(data_base64=base64.b64encode(b"\xff"*4096).decode(),
                                      read_cursor=0, write_cursor=4096)
        maximum = encode_descriptor(descriptor, version=4)
        self.assertLessEqual(len(maximum), 16384)
        self.assertEqual(self.decode(maximum).returncode, 0)


if __name__ == "__main__":
    unittest.main()
