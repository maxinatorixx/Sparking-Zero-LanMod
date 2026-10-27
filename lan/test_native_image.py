"""Loaded-image guards accept unrelated file digests, not incompatible layouts."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class NativeImageTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('x86_64-w64-mingw32-gcc') and shutil.which('wine'),
                         'requires MinGW and disposable Wine')
    def test_pe64_prefix_bounds_and_different_file_hashes(self):
        self.assertTrue(os.environ.get('WINEPREFIX','').startswith('/tmp/szero-'))
        native=Path(__file__).resolve().parent/'native'
        with tempfile.TemporaryDirectory(prefix='szero-native-image-') as folder:
            original=Path(folder)/'original.exe';modified=Path(folder)/'different.exe'
            subprocess.run(['x86_64-w64-mingw32-gcc','-std=c11','-O2','-Wall','-Wextra',
                '-Werror',str(native/'test_native_image.c'),'-o',str(original)],
                check=True,capture_output=True)
            modified.write_bytes(original.read_bytes()+b'Unrelated on-disk overlay; native layout unchanged')
            self.assertNotEqual(hashlib.sha256(original.read_bytes()).digest(),
                                hashlib.sha256(modified.read_bytes()).digest())
            for executable in (original,modified):
                result=subprocess.run(['wine',str(executable)],capture_output=True,text=True,
                    timeout=25,env=dict(os.environ,WINEDEBUG='-all'))
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn('changed-instruction refusal passed',result.stdout)
