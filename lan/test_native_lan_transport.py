"""Compile/run the source-only idle-channel contract; never loads the game."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class NativeLanTransportTests(unittest.TestCase):
    def test_native_transport_memory_contract(self):
        compiler = shutil.which("cc") or shutil.which("gcc")
        self.assertIsNotNone(compiler, "C compiler required for native contract")
        native = Path(__file__).resolve().parent / "native"
        with tempfile.TemporaryDirectory(prefix="szero-lan-transport-") as temporary:
            fixture = Path(temporary) / "fixture"
            subprocess.run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                            str(native / "native_lan_transport.c"),
                            str(native / "test_native_lan_transport.c"),
                            "-o", str(fixture)], check=True, capture_output=True)
            result = subprocess.run([str(fixture)], check=True, capture_output=True, text=True)
            self.assertIn("synthetic memory only", result.stdout)


if __name__ == "__main__":
    unittest.main()
