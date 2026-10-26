"""Compiled owned-memory settings/stream contracts, not a game test."""
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(platform.machine().lower() in ("x86_64", "amd64") and shutil.which("gcc"),
                     "requires an x64 C compiler for exact native layout fixture")
class NativeSessionSettingsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("x86_64-w64-mingw32-gcc"), "requires MinGW stack-usage output")
    def test_capture_does_not_reserve_payloads_on_native_fiber_stack(self):
        native = Path(__file__).resolve().parent / "native"
        with tempfile.TemporaryDirectory(prefix="szero-settings-stack-") as temporary:
            destination = Path(temporary) / "wire.o"
            subprocess.run(["x86_64-w64-mingw32-gcc", "-std=c11", "-O2",
                "-fstack-usage", "-c", str(native / "native_session_wire.c"),
                "-o", str(destination)], check=True, capture_output=True, timeout=30)
            rows = destination.with_suffix(".su").read_text().splitlines()
            captures = {row.split("\t")[0].rsplit(":", 1)[-1]: int(row.split("\t")[1])
                        for row in rows if row.split("\t")[0].rsplit(":", 1)[-1]
                        in ("capture_settings", "szero_capture_settings", "szero_capture_settings_info")}
            self.assertIn("szero_capture_settings", captures)
            for function, size in captures.items():
                self.assertLessEqual(size, 512, function + " must not stack-allocate stream payloads")

    def test_compiled_capture_and_profile2_materializer_contracts(self):
        native = Path(__file__).resolve().parent / "native"
        with tempfile.TemporaryDirectory(prefix="szero-settings-contract-") as temporary:
            executable = Path(temporary) / "settings-contract"
            built = subprocess.run([
                "gcc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                str(native / "native_session_wire.c"),
                str(native / "session_materializer.c"),
                str(native / "test_native_session_wire.c"),
                "-o", str(executable)], capture_output=True, text=True, timeout=30)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("owned synthetic memory only", result.stdout)


if __name__ == "__main__":
    unittest.main()
