"""Compiled scoped LAN user+98 contracts; no native game execution."""
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(platform.machine().lower() in ("x86_64", "amd64") and shutil.which("gcc"),
                     "requires x64 C compiler")
class NativeLanUserInfoTests(unittest.TestCase):
    def test_namespace_split_and_native_owned_vector_transfer(self):
        native = Path(__file__).resolve().parent / "native"
        with tempfile.TemporaryDirectory(prefix="szero-userinfo-") as temporary:
            exe = Path(temporary) / "userinfo"
            subprocess.run(["gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                str(native / "native_lan_userinfo.c"), str(native / "native_lan_identity.c"),
                str(native / "test_native_lan_userinfo.c"), "-o", str(exe)],
                check=True, capture_output=True, timeout=30)
            run = subprocess.run([str(exe)], check=True, capture_output=True, text=True, timeout=10)
            self.assertIn("synthetic memory only", run.stdout)

    @unittest.skipUnless(shutil.which("x86_64-w64-mingw32-gcc"), "requires MinGW")
    def test_native_fiber_frames_remain_bounded(self):
        native = Path(__file__).resolve().parent / "native"
        with tempfile.TemporaryDirectory(prefix="szero-userinfo-stack-") as temporary:
            subprocess.run(["x86_64-w64-mingw32-gcc", "-std=c11", "-O2", "-Wall",
                "-Wextra", "-Werror", "-Wframe-larger-than=512", "-c",
                str(native / "native_lan_userinfo.c"), "-o", str(Path(temporary) / "userinfo.o")],
                check=True, capture_output=True, timeout=30)
