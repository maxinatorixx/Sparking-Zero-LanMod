"""Read-only native candidate diagnostics with bounded synthetic memory."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(shutil.which("cc"), "requires C compiler")
class NativeSessionInspectTests(unittest.TestCase):
    def test_bounded_actual_descriptor_inspection(self):
        native = Path(__file__).resolve().parent / "native"
        with tempfile.TemporaryDirectory(prefix="szero-session-inspect-") as temporary:
            executable = Path(temporary) / "inspect-test"
            subprocess.run(["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                "-Wframe-larger-than=512", "-c", str(native / "native_session_inspect.c"),
                "-o", str(Path(temporary) / "inspect.o")], check=True, capture_output=True)
            subprocess.run(["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                str(native / "native_session_inspect.c"),
                str(native / "test_native_session_inspect.c"), "-o", str(executable)],
                check=True, capture_output=True)
            result = subprocess.run([str(executable)], check=True, capture_output=True, text=True)
            self.assertIn("native descriptor inspection contracts passed", result.stdout)
