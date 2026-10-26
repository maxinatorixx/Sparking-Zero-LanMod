"""Portable DTO-only LAN identity projection; no platform/native calls."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(shutil.which("cc"), "requires C compiler")
class NativeLanIdentityTests(unittest.TestCase):
    def test_owned_projection_and_failure_atomicity(self):
        native = Path(__file__).resolve().parent / "native"
        with tempfile.TemporaryDirectory(prefix="szero-lan-identity-") as temporary:
            output = Path(temporary)
            subprocess.run(["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                "-Wframe-larger-than=512", "-c", str(native / "native_lan_identity.c"),
                "-o", str(output / "identity.o")], check=True, capture_output=True)
            executable = output / "identity-test"
            subprocess.run(["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                str(native / "native_lan_identity.c"), str(native / "test_native_lan_identity.c"),
                "-o", str(executable)], check=True, capture_output=True)
            result = subprocess.run([str(executable)], check=True, capture_output=True, text=True)
            self.assertIn("LAN identity projection contracts passed", result.stdout)
