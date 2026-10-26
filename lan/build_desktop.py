"""Build a self-contained launcher on the target OS (no cross-compilation)."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def build(output):
    if sys.platform not in ("win32", "linux"):
        raise ValueError("Build on Windows or Linux for that same platform")
    if sys.platform == "win32" and sys.version_info >= (3,14):
        raise ValueError("Use Python 3.13 or 3.12 for Windows builds; the pinned packager does not collect Tk 9 zipfs data")
    output = Path(output).resolve()
    from build_icon import build_icon
    icons = build_icon(output / "build/icons")
    name = "SzeroLAN-Windows" if sys.platform == "win32" else "SzeroLAN-Linux"
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
            "--name", name, "--distpath", str(output), "--workpath", str(output / "build"),
            "--specpath", str(output / "build"), "--paths", str(ROOT),
            "--icon", str(icons / "four-star.ico")]
    if sys.platform == "win32":
        args.append("--windowed")
    for source, destination in (("ue4ss", "ue4ss"),
                                ("vendor/UE4SS_v3.0.1.zip", "vendor"),
                                ("vendor/UE4SS-LICENSE.txt", "vendor"),
                                ("vendor/UE4SS.json", "vendor"),
                                ("vendor/MinHook-LICENSE.txt", "vendor"),
                                ("client.example.json", ".")):
        args += ["--add-data", str(ROOT / source) + ":" + destination]
    args += ["--add-data", str(icons) + ":assets"]
    args.append(str(ROOT / "desktop.py"))
    environment=dict(os.environ, PYINSTALLER_CONFIG_DIR=str(output / "build/cache"))
    subprocess.run(args, check=True, env=environment)
    artifact = output / (name + (".exe" if sys.platform == "win32" else ""))
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (output / (artifact.name + ".sha256")).write_text(digest + "  " + artifact.name + "\n", encoding="ascii")
    print(artifact)
    return artifact


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT.parent / ".build/desktop"))
    build(parser.parse_args().output)
