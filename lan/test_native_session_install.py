"""Actual v3 publication/rollback guards on owned memory, never game code."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(shutil.which("x86_64-w64-mingw32-gcc") and shutil.which("wine"),
                     "requires MinGW and Wine")
class NativeSessionInstallTests(unittest.TestCase):
    def test_all_service_slots_idle_transport_and_publication_rollback(self):
        native = Path(__file__).resolve().parent / "native"
        with tempfile.TemporaryDirectory(prefix="szero-install-guards-") as temporary:
            executable = Path(temporary) / "install.exe"
            sources = ["native_search.c", "native_session_host.c",
                       "native_session_adapter.c", "native_session_codec.c",
                       "native_session_search.c", "native_session_inspect.c", "native_lan_identity.c", "native_lan_userinfo.c", "session_materializer.c",
                       "native_session_wire.c", "native_lan_transport.c"]
            subprocess.run(["x86_64-w64-mingw32-gcc", "-std=c11", "-Wall",
                            "-Wextra", "-Werror", "-O2", "-DSZERO_SESSION_V3",
                            "-DSZERO_NATIVE_SEARCH_TEST",
                            *(str(native / source) for source in sources),
                            "-lws2_32", "-lbcrypt", "-o", str(executable)],
                           check=True, capture_output=True)
            environment = dict(os.environ, WINEDEBUG="-all")
            selected = Path(environment.get("WINEPREFIX", "/not-selected"))
            # Unit tests never use or alter the user's system Wine prefix.
            if not str(selected).startswith("/tmp/szero-"):
                selected = Path(temporary) / "wine"
            environment["WINEPREFIX"] = str(selected)
            result = subprocess.run(["wine", str(executable)], check=True,
                                    capture_output=True, text=True,
                                    env=environment, timeout=60)
            self.assertIn("native_search synthetic Win64 contracts passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
