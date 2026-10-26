"""Single-file launcher entry and private bridge subprocess entry."""
import json
import os
from pathlib import Path
import sys
import tempfile


def main():
    # Windowed Windows builds have no attached console. Logging still has its
    # rotating file handler, and must not try to write to a None stream.
    if sys.stdout is None:
        sys.stdout=open(os.devnull,"w")
    if sys.stderr is None:
        sys.stderr=open(os.devnull,"w")
    if sys.argv[1:2] == ["--bridge"]:
        del sys.argv[1]
        from ingame_client import main as bridge_main
        return bridge_main()
    if sys.argv[1:2] == ["--self-check"]:
        from installer import ARCHIVE_PATH, ARCHIVE_SHA256, digest
        root = Path(__file__).resolve().parent
        required = (root / "ue4ss/SzeroLAN/scripts/native_search.dll",
                    root / "ue4ss/SzeroLAN/scripts/backend_adapter.dll",
                    root / "ue4ss/SzeroLAN/scripts/main.lua", root / "client.example.json",
                    root / "assets/four-star.ico", root / "assets/four-star.png")
        if digest(ARCHIVE_PATH) != ARCHIVE_SHA256 or not all(p.is_file() for p in required):
            raise ValueError("Bundled resources failed verification")
        from ingame_client import GameBridge
        from launcher_support import bridge_command
        from savegame import decode_save, encode_save
        sample = b"Arena bundled save codec self-check" * 4
        if decode_save(encode_save(sample)) != sample:
            raise ValueError("Bundled save codec self-check failed")
        ui_checked=False
        if "--ui" in sys.argv:
            import tkinter as tk
            from setup_launcher import SetupLauncher
            with tempfile.TemporaryDirectory(prefix="szero-ui-self-check-") as temporary:
                root=tk.Tk()
                try:
                    ui=SetupLauncher(root,Path(temporary)/"launcher.json")
                    root.update()
                    assert ui.launch_button.winfo_ismapped()
                    assert ui.launch_button.winfo_rooty()+ui.launch_button.winfo_height() <= root.winfo_rooty()+root.winfo_height()
                    ui_checked=True
                finally:
                    root.destroy()
        print(json.dumps({"resources": "ok", "bridge": GameBridge.__name__,
                          "frozen": bool(getattr(sys, "frozen", False)),
                          "ui": ui_checked,
                          "save_codec": "ok",
                          "child_mode": "--bridge" in bridge_command("game", "runtime")}))
        return 0
    from setup_launcher import main as launcher_main
    launcher_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
