"""Actual lifecycle include with synthetic native callbacks in disposable Wine."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(shutil.which("x86_64-w64-mingw32-gcc") and shutil.which("wine"),
                     "requires MinGW and Wine")
class NativeLifecycleTests(unittest.TestCase):
    def test_owned_settings_member_diff_and_background_mailbox(self):
        native = Path(__file__).resolve().parent / "native"
        with tempfile.TemporaryDirectory(prefix="szero-lifecycle-") as temporary:
            executable = Path(temporary) / "lifecycle.exe"
            subprocess.run(["x86_64-w64-mingw32-gcc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                "-DSZERO_BINDINGS_TEST_IDENTITY",
                *(str(native / file) for file in ["test_native_session_lifecycle.c",
                    "session_materializer.c", "native_session_wire.c",
                    "native_session_adapter.c", "native_session_codec.c"]),
                "-o", str(executable)], check=True, capture_output=True)
            environment = dict(os.environ, WINEDEBUG="-all")
            # Reuse only explicitly selected disposable task prefixes; never
            # let a unit test default to the user's system ~/.wine installation.
            selected = Path(environment.get("WINEPREFIX", "/not-selected"))
            if not str(selected).startswith("/tmp/szero-"):
                selected = Path(temporary) / "wine"
            environment["WINEPREFIX"] = str(selected)
            result = subprocess.run(["wine", str(executable)], check=True,
                capture_output=True, text=True, env=environment, timeout=60)
            self.assertIn("native lifecycle actual include contracts passed", result.stdout)
