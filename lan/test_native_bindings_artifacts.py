"""Resolve real PE artifacts as data; never launch either game executable."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class NativeBindingsArtifactTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("x86_64-w64-mingw32-gcc") and shutil.which("wine")
                         and os.environ.get("SZERO_REFERENCE_EXE") and os.environ.get("SZERO_UPDATED_EXE"),
                         "requires explicit read-only reference artifacts, MinGW and disposable Wine")
    def test_reviewed_images_relocation_hooks_and_corruption(self):
        self.assertTrue(os.environ.get("WINEPREFIX", "").startswith("/tmp/szero-"))
        native = Path(__file__).resolve().parent / "native"
        with tempfile.TemporaryDirectory(prefix="szero-binding-artifacts-") as folder:
            executable = Path(folder) / "resolve.exe"
            subprocess.run(["x86_64-w64-mingw32-gcc", "-std=c11", "-O2", "-Wall", "-Wextra",
                            "-Werror", "-municode", "-static-libgcc", "-Wl,--no-insert-timestamp",
                            str(native / "test_native_bindings_image.c"), str(native / "native_bindings.c"),
                            "-o", str(executable)], check=True, capture_output=True)
            expected = (("SZERO_REFERENCE_EXE", (0x8cf84f8, 0x23d76a0, 0x7b95320)),
                        ("SZERO_UPDATED_EXE", (0x8cf9978, 0x23d8060, 0x7b96420)))
            for key, addresses in expected:
                for flags in ((), ("--shift",), ("--hooked",), ("--shift", "--hooked"), ("--corrupt",)):
                    with self.subTest(artifact=key, flags=flags):
                        path = Path(os.environ[key]).resolve()
                        self.assertTrue(path.is_file())
                        result = subprocess.run(["wine", str(executable), "Z:" + str(path).replace("/", "\\"), *flags],
                                                capture_output=True, text=True, timeout=90,
                                                env=dict(os.environ, WINEDEBUG="-all"))
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        if "--corrupt" in flags:
                            self.assertIn("resolve=0", result.stdout)
                            self.assertIn("corrupt native signature refused", result.stdout)
                            continue
                        self.assertIn("resolve=1", result.stdout)
                        shift = 0x2000 if "--shift" in flags else 0
                        self.assertIn("context=%x result=%x service=%x" % tuple(a + shift for a in addresses), result.stdout)
                        if "--hooked" in flags:
                            self.assertIn("hooked_prefixes_rejected=19", result.stdout)
                        self.assertIn("without executing game code", result.stdout)


if __name__ == "__main__":
    unittest.main()
