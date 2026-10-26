"""Portable injected native-ABI fixture, never invokes game callbacks."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(shutil.which("cc"), "requires a C compiler")
class NativeSessionAdapterTests(unittest.TestCase):
    def test_owned_id_join_plain_error_and_consumed_refresh(self):
        native = Path(__file__).resolve().parent / "native"
        with tempfile.TemporaryDirectory(prefix="szero-adapter-") as temporary:
            executable = Path(temporary) / "adapter-test"
            subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                str(native / "native_session_adapter.c"),
                str(native / "session_materializer.c"),
                str(native / "native_session_wire.c"),
                str(native / "test_native_session_adapter.c"),
                "-o", str(executable)], check=True, capture_output=True)
            result = subprocess.run([str(executable)], check=True,
                                    capture_output=True, text=True)
            self.assertIn("injected-ABI contracts passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
