"""Data-only native binding safety/relocation regressions, no game execution."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class NativeBindingTests(unittest.TestCase):
    def test_relocation_and_fail_closed_guards(self):
        compiler = shutil.which('cc') or shutil.which('gcc')
        if not compiler:
            self.skipTest('C compiler is required for portable native fixture')
        native = Path(__file__).parent/'native'
        with tempfile.TemporaryDirectory(prefix='szero-bindings-') as directory:
            exe = Path(directory)/'bindings'
            subprocess.run([compiler,'-std=c11','-O2','-Wall','-Wextra','-Werror',str(native/'test_native_bindings.c'),'-o',str(exe)],check=True,capture_output=True,text=True)
            for mode in ('original','shifted','ambiguous','changed_field','changed_branch','wrong_section',
                         'wrong_reference','invalid_pe','out_of_bounds'):
                with self.subTest(mode=mode):
                    result=subprocess.run([str(exe),mode],capture_output=True,text=True)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertEqual(result.stdout.strip(),mode)


if __name__=='__main__':unittest.main()
