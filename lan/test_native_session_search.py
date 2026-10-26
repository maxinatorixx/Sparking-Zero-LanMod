"""Production search result construction with a synthetic allocator only."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(shutil.which("cc"), "requires a C compiler")
class NativeSessionSearchTests(unittest.TestCase):
    def test_owned_vector_result_and_failure_ownership(self):
        native = Path(__file__).resolve().parent / "native"
        with tempfile.TemporaryDirectory(prefix="szero-search-vector-") as temporary:
            executable = Path(temporary) / "search-test"
            subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                *(str(native / file) for file in ["native_session_search.c",
                    "session_materializer.c", "native_session_wire.c",
                    "test_native_session_search.c"]),
                "-o", str(executable)], check=True, capture_output=True)
            result = subprocess.run([str(executable)], check=True,
                                    capture_output=True, text=True)
            self.assertIn("owned search vector contracts passed", result.stdout)
