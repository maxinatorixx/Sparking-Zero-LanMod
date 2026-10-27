"""Offline loader and LAN adapter installation with backups and a file receipt."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent
LOADER_VERSION = "3.0.1"
ARCHIVE_SHA256 = "4b47d4bceddd2f561a4e395bfa00924ccfc945af576a2d0c613e6537846c57ec"
ARCHIVE_PATH = ROOT / "vendor/UE4SS_v3.0.1.zip"
SHARED_HELPER = "Mods/shared/UEHelpers/UEHelpers.lua"
LOADER_FILES = ("dwmapi.dll", "UE4SS.dll", "UE4SS-settings.ini", SHARED_HELPER)
MOD_FILES = ("scripts/main.lua", "scripts/panel.lua", "scripts/audit.lua",
             "scripts/console_probe.dll", "scripts/native_menu.lua", "scripts/menu_bridge.dll",
             "scripts/session_trace.lua", "scripts/session_probe.dll", "scripts/native_search.lua",
             "scripts/native_search.dll", "scripts/service_trace.dll", "scripts/backend_adapter.dll", "enabled.txt")


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as output:
            output.write(content)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def enabled_mods(content):
    """Preserve other mods and the input file's BOM/line-ending convention."""
    bom = content.startswith(b"\xef\xbb\xbf")
    text = content.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    pattern = r"(?m)^[ \t]*SzeroLAN[ \t]*:[ \t]*[01][ \t]*(?=\r?$)"
    if re.search(pattern, text):
        text = re.sub(pattern, "SzeroLAN : 1", text)
    else:
        text = "SzeroLAN : 1" + newline + text
    return (b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8")


def installed_runtime(game_root):
    """Detect our enabled mod only; do not treat an unrelated UE4SS as ours."""
    win64 = Path(game_root) / "SparkingZERO/Binaries/Win64"
    for loader in (win64 / "ue4ss", win64):
        scripts = loader / "Mods/SzeroLAN/scripts"
        mods = loader / "Mods/mods.txt"
        checked = (loader, loader / "Mods", loader / "Mods/SzeroLAN", scripts,
                   mods, loader / "Mods/SzeroLAN/enabled.txt",
                   scripts / "main.lua", scripts / "native_search.dll")
        if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in checked):
            continue
        enabled = (loader / "Mods/SzeroLAN/enabled.txt").is_file()
        if mods.is_file():
            text = mods.read_text(encoding="utf-8-sig")
            match = re.search(r"(?m)^\s*SzeroLAN\s*:\s*([01])\s*$", text)
            if match:
                enabled = match[1] == "1"
        if enabled and all((scripts / name).is_file() for name in ("main.lua", "native_search.dll")):
            return str(scripts / "lan_runtime.lua")
    return None


def uninstall(game_root):
    """Disable/remove receipt-owned mod files, retaining shared loaders/settings.

    Other mods may now use the shared loader, so uninstalling SzeroLAN never
    removes UE4SS/dwmapi or rewinds the whole mods.txt/configuration file.
    A modified own-mod file refuses the entire operation before any changes.
    Removed payloads are not copied into persistent uninstall backups. Existing
    install-time backups stay untouched; rollback data lives only in memory.
    """
    root = Path(game_root).resolve()
    def safe_target(path):
        if not path.resolve().is_relative_to(root):
            raise ValueError("An uninstall path escapes the selected game folder")
        current = path
        while current != root:
            if current.is_symlink() or getattr(current, "is_junction", lambda: False)():
                raise ValueError("Symlink in uninstall path")
            current = current.parent
    receipt_path = root / "SparkingZERO/Binaries/Win64/SzeroLAN-install.json"
    safe_target(receipt_path)
    if receipt_path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("Install receipt is too large")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("format") != 1 or not isinstance(receipt.get("transactions"), list):
        raise ValueError("Invalid install receipt; nothing was removed")
    known = {}
    allowed = {prefix + relative for prefix in ("SparkingZERO/Binaries/Win64/Mods/SzeroLAN/",
                "SparkingZERO/Binaries/Win64/ue4ss/Mods/SzeroLAN/") for relative in MOD_FILES}
    for transaction in receipt["transactions"]:
        if not isinstance(transaction, dict) or not isinstance(transaction.get("files", []), list):
            raise ValueError("Invalid install transaction")
        for item in transaction.get("files", []):
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                raise ValueError("Invalid install inventory entry")
            name = item["path"]
            if "/Mods/SzeroLAN/" in "/" + name:
                if name not in allowed or not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", ""))):
                    raise ValueError("Install receipt contains an unowned mod path")
                known[name] = item["sha256"]
    if not known:
        raise ValueError("No owned mod files in install receipt; nothing was removed")
    removals = {}
    for name, expected in known.items():
        path = root / name
        safe_target(path)
        if path.exists():
            if not path.is_file() or digest(path) != expected:
                raise ValueError("An installed mod file was modified; nothing removed: " + name)
            removals[path] = path.read_bytes()
    changes = {}
    for loader in (root / "SparkingZERO/Binaries/Win64/ue4ss", root / "SparkingZERO/Binaries/Win64"):
        path = loader / "Mods/mods.txt"
        safe_target(path)
        if path.is_file():
            original = path.read_bytes()
            text = original.decode("utf-8-sig")
            text = re.sub(r"(?m)^([ \t]*SzeroLAN[ \t]*:[ \t]*)1([ \t]*)(?=\r?$)", r"\g<1>0\2", text)
            updated = (b"\xef\xbb\xbf" if original.startswith(b"\xef\xbb\xbf") else b"") + text.encode("utf-8")
            if original != updated:
                changes[path] = (original, updated)
    try:
        for path, (_, data) in changes.items():
            atomic_write(path, data)
        for path in removals:
            path.unlink()
        receipt["uninstalled"] = True
        atomic_write(receipt_path, (json.dumps(receipt, indent=2) + "\n").encode())
    except BaseException:
        for path, data in removals.items():
            atomic_write(path, data)
        for path, (original, _) in changes.items():
            atomic_write(path, original)
        raise
    return None


def install(game_root):
    root = Path(game_root).resolve()
    win64 = root / "SparkingZERO/Binaries/Win64"
    executable = win64 / "SparkingZERO-Win64-Shipping.exe"
    if not executable.is_file():
        raise ValueError("Game executable is missing: " + str(executable))

    # Check the pinned archive before making any changes, even when reusing a loader.
    if digest(ARCHIVE_PATH) != ARCHIVE_SHA256:
        raise ValueError("Bundled UE4SS archive checksum mismatch; extract the package again.")
    with zipfile.ZipFile(ARCHIVE_PATH) as archive:
        bundled = {name: archive.read(name) for name in LOADER_FILES}
    license_bytes = (ROOT / "vendor/UE4SS-LICENSE.txt").read_bytes()

    loader = next((p for p in (win64 / "ue4ss", win64)
                   if (p / "UE4SS.dll").is_file()), None)
    fresh = loader is None
    plan = {}
    if fresh:
        loader = win64
        proxy = win64 / "dwmapi.dll"
        if proxy.exists() and digest(proxy) != hashlib.sha256(bundled["dwmapi.dll"]).hexdigest():
            raise ValueError("An unrelated dwmapi.dll already exists. It was left unchanged; "
                             "resolve that proxy-loader conflict before setup.")
        for relative, data in bundled.items():
            target = loader / relative
            # Keep an existing user settings/helper file, including partial installs.
            if relative not in ("dwmapi.dll", "UE4SS.dll") and target.exists():
                continue
            plan[target] = data
        plan[loader / "UE4SS-LICENSE.txt"] = license_bytes
    elif not (loader / SHARED_HELPER).exists():
        plan[loader / SHARED_HELPER] = bundled[SHARED_HELPER]
        plan[loader / "UE4SS-LICENSE.txt"] = license_bytes

    destination = loader / "Mods/SzeroLAN"
    for relative in MOD_FILES:
        plan[destination / relative] = (ROOT / "ue4ss/SzeroLAN" / relative).read_bytes()
    config = root / "SzeroLAN.json"
    if not config.exists():
        plan[config] = (ROOT / "client.example.json").read_bytes()
    mods_txt = loader / "Mods/mods.txt"
    plan[mods_txt] = enabled_mods(mods_txt.read_bytes() if mods_txt.exists() else b"")

    receipt = win64 / "SzeroLAN-install.json"
    previous = json.loads(receipt.read_text(encoding="utf-8")) if receipt.exists() else {
        "format": 1, "transactions": []}
    if (not isinstance(previous, dict) or previous.get("format") != 1
            or not isinstance(previous.get("transactions"), list)):
        raise ValueError("Existing setup receipt is invalid; nothing was installed.")
    previous.pop("uninstalled", None)
    previous.pop("game_exe_sha256", None)  # Legacy receipts remain uninstallable.

    # Preflight every target so directory conflicts cannot cause a partial install.
    for target in [*plan, receipt]:
        if not target.resolve().is_relative_to(root):
            raise ValueError("An installation path points outside the selected game folder.")
        if target.exists() and not target.is_file():
            raise ValueError(f"A directory conflicts with an installation file: {target}")
        current = target
        while current != root:
            if current.is_symlink():
                raise ValueError(f"A symlink conflicts with an installation path: {current}")
            if current != target and current.exists() and not current.is_dir():
                raise ValueError(f"A file conflicts with an installation folder: {current}")
            current = current.parent

    changes, written = [], []
    transaction = str(time.time_ns())
    try:
        for target, data in plan.items():
            original = target.read_bytes() if target.exists() else None
            if original == data:
                continue
            backup = None
            if original is not None:
                backup = target.with_name(target.name + f".{transaction}.bak")
                atomic_write(backup, original)
            written.append((target, original))
            atomic_write(target, data)
            changes.append({
                "path": target.relative_to(root).as_posix(),
                "before_sha256": hashlib.sha256(original).hexdigest() if original is not None else None,
                "after_sha256": hashlib.sha256(data).hexdigest(),
                "backup": backup.relative_to(root).as_posix() if backup else None,
            })
        inventory = [{"path": target.relative_to(root).as_posix(), "sha256": digest(target)}
                     for target in plan]
        previous["transactions"].append({
            "id": transaction, "loader": "bundled " + LOADER_VERSION if fresh else "existing, preserved",
            "archive_sha256": ARCHIVE_SHA256, "changes": changes, "files": inventory,
        })
        atomic_write(receipt, (json.dumps(previous, indent=2) + "\n").encode())
    except BaseException:
        for target, original in reversed(written):
            if original is None:
                target.unlink(missing_ok=True)
            else:
                atomic_write(target, original)
        raise
    return str(destination / "scripts/lan_runtime.lua")
