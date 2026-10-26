"""Build-time exact frozen-resource verification; requires PyInstaller."""
from pathlib import Path
import argparse


def verify(executable):
    from PyInstaller.archive.readers import CArchiveReader
    root=Path(__file__).resolve().parent
    scripts=root/'ue4ss/SzeroLAN/scripts'
    files=[scripts/name for name in ('main.lua','native_search.lua','native_menu.lua',
        'panel.lua','audit.lua','session_trace.lua','backend_adapter.dll',
        'native_search.dll','service_trace.dll')]
    files += [root/'vendor/MinHook-LICENSE.txt',root/'vendor/UE4SS_v3.0.1.zip']
    archive=CArchiveReader(str(executable))
    names={name.replace('\\','/'):name for name in archive.toc}
    for source in files:
        relative=source.relative_to(root).as_posix()
        if relative not in names or archive.extract(names[relative])!=source.read_bytes():
            raise ValueError('Frozen resource differs from source: '+relative)
    print(str(executable)+': '+str(len(files))+' exact embedded resources verified')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable',type=Path)
    verify(parser.parse_args().executable)
