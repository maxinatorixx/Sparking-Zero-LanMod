"""Pure launcher settings/argv helpers. Never change native multiplayer state."""
import ctypes
import json
import os
from pathlib import Path
import sys

RESOURCE_ROOT = Path(__file__).resolve().parent
DEFAULT_OPTIONS = {"display": "Game default", "resolution": "Game default",
                   "wine_binary": "wine", "wine_prefix": "", "service_trace": False,
                   "mod_logging": False}
DISPLAYS = ("Game default", "Fullscreen", "Windowed", "Borderless")
RESOLUTIONS = ("Game default", "1280x720", "1600x900", "1920x1080", "2560x1440", "3840x2160")


def preferences_path():
    # Never write into a one-file executable's temporary extraction directory.
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "SzeroLAN" / "launcher.json"


def read_preferences(path):
    path = Path(path)
    value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if type(value) is not dict:
        raise ValueError("Launcher settings must be a JSON object; file left unchanged")
    for key in ("game_directory", "adapter_runtime"):
        if key in value:
            if type(value[key]) is not str or "\0" in value[key]:
                raise ValueError("Invalid saved " + key)
            # Migrate the old Windows-under-Wine launcher's Z: paths when the
            # new native Linux launcher reads the same setup.json.
            if os.name != "nt" and value[key][:3].lower() in ("z:\\", "z:/"):
                value[key]="/"+value[key][3:].replace("\\","/")
    return value


def launch_options(value=None):
    if value is None:
        value = {}
    if type(value) is not dict:
        raise ValueError("launch_options must be an object")
    result = dict(value)  # Preserve unknown options for future versions.
    # Retired controls must not silently keep affecting launches from old files.
    result.pop("dx11", None)
    result.pop("skip_splash", None)
    for key, default in DEFAULT_OPTIONS.items():
        result.setdefault(key, default)
    if type(result["service_trace"]) is not bool:
        raise ValueError("Online diagnostics must be true or false")
    if type(result["mod_logging"]) is not bool:
        raise ValueError("Mod logging must be true or false")
    # One explicit opt-in controls all mod diagnostics. Legacy trace settings
    # alone must not silently enable logging in the renamed control.
    result["service_trace"] = result["mod_logging"]
    if result["display"] not in DISPLAYS or result["resolution"] not in RESOLUTIONS:
        raise ValueError("Choose a listed display mode and resolution")
    for key in ("wine_binary", "wine_prefix"):
        if type(result[key]) is not str or len(result[key]) > 4096 or any(c in result[key] for c in "\0\r\n"):
            raise ValueError("Invalid Wine setting")
    if not result["wine_binary"].strip():
        raise ValueError("Enter a Wine executable (normally wine)")
    return result


def game_arguments(options):
    options = launch_options(options)
    args = {"Game default": [], "Fullscreen": ["-fullscreen"],
             "Windowed": ["-windowed"], "Borderless": ["-windowed", "-noborder"]}[options["display"]]
    if options["resolution"] != "Game default":
        width, height = options["resolution"].split("x")
        args += ["-ResX=" + width, "-ResY=" + height]
    return args


def game_command(executable, options, platform=None):
    options = launch_options(options)
    platform = platform or sys.platform
    args = [str(Path(executable).resolve()), *game_arguments(options)]
    return args if platform == "win32" else [options["wine_binary"].strip(), *args]


def game_environment(environment, options, platform=None):
    """Sanitize frozen runtime search paths for external Wine/game processes."""
    env = dict(environment)
    platform = platform or sys.platform
    if platform != "win32":
        if getattr(sys, "frozen", False) or "LD_LIBRARY_PATH_ORIG" in env:
            if "LD_LIBRARY_PATH_ORIG" in env:
                env["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH_ORIG"]
            else:
                env.pop("LD_LIBRARY_PATH", None)
        prefix = launch_options(options)["wine_prefix"].strip()
        if prefix:
            env["WINEPREFIX"] = str(Path(prefix).expanduser().resolve())
        overrides = []
        native_names = {"dwmapi"}
        for override in env.get("WINEDLLOVERRIDES", "").split(";"):
            names, separator, value = override.partition("=")
            names = ",".join(name for name in names.split(",") if name.strip().lower() not in native_names)
            if names.strip() and separator:
                overrides.append(names + "=" + value)
        # Preserve unrelated overrides; our bundled native proxy must win.
        env["WINEDLLOVERRIDES"] = ";".join([*overrides, *[name + "=n,b" for name in sorted(native_names)]])
    return env


def spawn_game(popen, command, **kwargs):
    # PyInstaller changes the Windows DLL search path for its own Tk/Python.
    # Only the external game launch must use the normal system search path.
    frozen_windows = os.name == "nt" and getattr(sys, "frozen", False)
    if frozen_windows:
        ctypes.windll.kernel32.SetDllDirectoryW(None)
    try:
        return popen(command, **kwargs)
    finally:
        if frozen_windows:
            ctypes.windll.kernel32.SetDllDirectoryW(str(RESOURCE_ROOT))


def bridge_command(game_root, runtime, watch_parent=False):
    args = ["--game-root", str(game_root), "--runtime", str(runtime)]
    if watch_parent:
        args.append("--watch-parent-stdin")
    if getattr(sys, "frozen", False):
        return [sys.executable, "--bridge", *args]
    return [sys.executable, str(RESOURCE_ROOT / "ingame_client.py"), *args]


def find_game_folder():
    origin = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else RESOURCE_ROOT
    for folder in (origin, origin.parent, origin / "DRAGON BALL - Sparking! ZERO",
                   origin.parent / "DRAGON BALL - Sparking! ZERO"):
        if (folder / "SparkingZERO.exe").is_file():
            return folder.resolve()
    return None
