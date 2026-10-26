"""Build/check the explicit LAN allowlist; never scan original game files."""
from pathlib import Path
import argparse
import hashlib
import os
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
FILES = (
    "README.md",
    "docs/screenshots/launcher.png",
    "docs/screenshots/website.png",
    "lan/README.md",
    "lan/DEPLOYMENT.md",
    "lan/MODES.md",
    "lan/ACCOUNTS.md",
    "lan/account_client.py",
    "lan/account_store.py",
    "lan/arena_web.py",
    "lan/arena_supervisor.py",
    "lan/.env.example",
    "lan/web/index.html",
    "lan/web/arena.js",
    "lan/web/arena.css",
    "lan/web/avatar.svg",
    "lan/test_account_client.py",
    "lan/test_account_store.py",
    "lan/test_arena_web.py",
    "lan/test_account_connection.py",
    "lan/test_battle_start.py",
    "lan/test_battle_start_bridge.py",
    "lan/test_battle_end.py",
    "lan/test_native_rank.py",
    "lan/native_rank.py",
    "lan/native_profile.py",
    "lan/test_native_account_state.py",
    "lan/test_native_profile.py",
    "lan/test_ranked_reports.py",
    "lan/elo_matchmaking.py",
    "lan/test_elo_matchmaking.py",
    "lan/Dockerfile",
    "lan/Dockerfile.launcher",
    "lan/Dockerfile.launcher.dockerignore",
    "lan/.dockerignore",
    "lan/compose.yaml",
    "lan/desktop.py",
    "lan/build_desktop.py",
    "lan/build_icon.py",
    "lan/assets/four-star.png",
    "lan/assets/four-star.ico",
    "lan/build_release.py",
    "lan/build-requirements.txt",
    "lan/Build-Launcher.cmd",
    "lan/build-launcher.sh",
    "lan/Start-Client.sh",
    "lan/Start-Client.cmd",
    "lan/Start-Native-Trace.cmd",
    "lan/build_bundle.py",
    "lan/client.example.json",
    "lan/ingame_client.py",
    "lan/backend_rpc.py",
    "lan/backend_services.py",
    "lan/installer.py",
    "lan/launcher.py",
    "lan/launcher_support.py",
    "lan/launcher_theme.py",
    "lan/lifecycle.py",
    "lan/game_process.py",
    "lan/savegame.py",
    "lan/save_catalog.py",
    "lan/lan_identity.py",
    "lan/native/README.md",
    "lan/native/service_trace.c",
    "lan/native/backend_adapter.c",
    "lan/native/backend_response.c",
    "lan/native/backend_response.h",
    "lan/native/test_backend_adapter.c",
    "lan/native/test_backend_response.c",
    "lan/native/test_service_trace.c",
    "lan/native/vendor/minhook/UPSTREAM.md",
    "lan/native/vendor/minhook/LICENSE.txt",
    "lan/native/vendor/minhook/include/MinHook.h",
    "lan/native/vendor/minhook/src/buffer.c",
    "lan/native/vendor/minhook/src/buffer.h",
    "lan/native/vendor/minhook/src/hook.c",
    "lan/native/vendor/minhook/src/trampoline.c",
    "lan/native/vendor/minhook/src/trampoline.h",
    "lan/native/vendor/minhook/src/hde/hde64.c",
    "lan/native/vendor/minhook/src/hde/hde64.h",
    "lan/native/vendor/minhook/src/hde/pstdint.h",
    "lan/native/vendor/minhook/src/hde/table64.h",
    "lan/native/console_probe.c",
    "lan/native/menu_bridge.c",
    "lan/native/native_lan_transport.c",
    "lan/native/native_lan_transport.h",
    "lan/native/native_lan_identity.c",
    "lan/native/native_lan_identity.h",
    "lan/native/native_lan_userinfo.c",
    "lan/native/native_lan_userinfo.h",
    "lan/native/native_lan_userinfo_provider.inc",
    "lan/native/test_native_lan_userinfo.c",
    "lan/native/native_search.c",
    "lan/native/native_session_adapter.c",
    "lan/native/native_session_adapter.h",
    "lan/native/native_session_codec.c",
    "lan/native/native_session_codec.h",
    "lan/native/native_session_frames.inc",
    "lan/native/native_session_host.c",
    "lan/native/native_session_host.h",
    "lan/native/native_session_inspect.c",
    "lan/native/native_session_inspect.h",
    "lan/native/native_session_lifecycle.inc",
    "lan/native/native_session_provider.inc",
    "lan/native/native_session_search.c",
    "lan/native/native_session_search.h",
    "lan/native/native_session_transport.inc",
    "lan/native/native_session_wire.c",
    "lan/native/native_session_wire.h",
    "lan/native/session_materializer.c",
    "lan/native/session_materializer.h",
    "lan/native/session_probe.c",
    "lan/native/test_native_lan_transport.c",
    "lan/native/test_native_lan_identity.c",
    "lan/native/test_native_search_ipc.c",
    "lan/native/test_native_session_adapter.c",
    "lan/native/test_native_session_codec.c",
    "lan/native/test_native_session_host.c",
    "lan/native/test_native_session_inspect.c",
    "lan/native/test_native_session_ipc.c",
    "lan/native/test_native_session_lifecycle.c",
    "lan/native/test_native_session_search.c",
    "lan/native/test_native_session_wire.c",
    "lan/native/test_session_materializer.c",
    "lan/native_search.py",
    "lan/native_identity_diagnostics.py",
    "lan/native_session_codec.py",
    "lan/native_session_transactions.py",
    "lan/native_sessions.py",
    "lan/server.example.json",
    "lan/setup_launcher.py",
    "lan/szero_lan.py",
    "lan/test_adapter.lua",
    "lan/test_audit.lua",
    "lan/test_ingame_client.py",
    "lan/test_launcher.py",
    "lan/test_launcher_support.py",
    "lan/test_service_trace.py",
    "lan/test_backend_adapter.py",
    "lan/test_backend_bridge.py",
    "lan/test_backend_rpc.py",
    "lan/test_backend_services.py",
    "lan/test_lifecycle.py",
    "lan/test_savegame.py",
    "lan/test_install_controls.py",
    "lan/test_native_lan_userinfo.py",
    "lan/test_container.py",
    "lan/test_desktop_packaging.py",
    "lan/test_windows_desktop.py",
    "lan/test_lan_identity.py",
    "lan/test_native_lan_identity.py",
    "lan/test_native_lan_transport.py",
    "lan/test_native_menu.lua",
    "lan/test_native_search.lua",
    "lan/test_native_search.py",
    "lan/test_native_identity_diagnostics.py",
    "lan/test_native_udp_diagnostics.py",
    "lan/test_native_search_compiled.py",
    "lan/test_native_search_wire.py",
    "lan/test_native_server_ports.py",
    "lan/test_native_session_adapter.py",
    "lan/test_native_session_bridge.py",
    "lan/test_native_room_modes.py",
    "lan/test_native_session_install.py",
    "lan/test_native_session_inspect.py",
    "lan/test_native_session_codec.py",
    "lan/test_native_session_diagnostics.py",
    "lan/test_native_session_lifecycle.py",
    "lan/test_native_session_rpc.py",
    "lan/test_native_session_search.py",
    "lan/test_native_session_settings.py",
    "lan/test_native_session_transactions.py",
    "lan/test_native_session_transactions_wire.py",
    "lan/test_native_session_transport.py",
    "lan/test_native_multi_sessions.py",
    "lan/test_native_multi_bridge.py",
    "lan/test_multi_transport.py",
    "lan/test_native_session_wire.py",
    "lan/test_native_sessions.py",
    "lan/test_native_sessions_v2.py",
    "lan/test_panel.lua",
    "lan/test_session_materializer.py",
    "lan/test_session_trace.lua",
    "lan/test_setup_launcher.py",
    "lan/test_szero_lan.py",
    "lan/ue4ss/SzeroLAN/enabled.txt",
    "lan/ue4ss/SzeroLAN/scripts/audit.lua",
    "lan/ue4ss/SzeroLAN/scripts/console_probe.dll",
    "lan/ue4ss/SzeroLAN/scripts/main.lua",
    "lan/ue4ss/SzeroLAN/scripts/menu_bridge.dll",
    "lan/ue4ss/SzeroLAN/scripts/native_menu.lua",
    "lan/ue4ss/SzeroLAN/scripts/native_search.dll",
    "lan/ue4ss/SzeroLAN/scripts/service_trace.dll",
    "lan/ue4ss/SzeroLAN/scripts/backend_adapter.dll",
    "lan/ue4ss/SzeroLAN/scripts/native_search.lua",
    "lan/ue4ss/SzeroLAN/scripts/panel.lua",
    "lan/ue4ss/SzeroLAN/scripts/session_probe.dll",
    "lan/ue4ss/SzeroLAN/scripts/session_trace.lua",
    "lan/vendor/UE4SS-LICENSE.txt",
    "lan/vendor/MinHook-LICENSE.txt",
    "lan/vendor/UE4SS.json",
    "lan/vendor/UE4SS_v3.0.1.zip",
)
MANIFEST = "lan/SHA256SUMS.txt"
ARCHIVE = "dist/SzeroLAN-experimental.zip"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def payload():
    result = {}
    for relative in FILES:
        path = ROOT / relative
        public_docs={"README.md", "docs/screenshots/launcher.png", "docs/screenshots/website.png"}
        if (not (relative.startswith("lan/") or relative in public_docs)
                or ".." in Path(relative).parts or path.is_symlink()):
            raise ValueError("invalid bundle allowlist entry")
        result[relative] = path.read_bytes()
    result[MANIFEST] = "".join(f"{digest(data)}  {name}\n" for name, data in result.items()).encode("ascii")
    return result


def build():
    contents = payload()
    (ROOT / "dist").mkdir(exist_ok=True)
    target = ROOT / ARCHIVE
    descriptor, temporary = tempfile.mkstemp(prefix="szero-bundle-", suffix=".zip", dir=target.parent)
    os.close(descriptor)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name, data in contents.items():
                entry = zipfile.ZipInfo(name, date_time=(2026, 10, 22, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, data)
        os.replace(temporary, target)
        (ROOT / MANIFEST).write_bytes(contents[MANIFEST])
        (ROOT / "dist/SHA256SUMS.txt").write_text(f"{digest(target.read_bytes())}  {ARCHIVE}\n", encoding="ascii")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    check()


def check():
    contents = payload()
    if (ROOT / MANIFEST).read_bytes() != contents[MANIFEST]:
        raise ValueError("source checksum manifest differs")
    with zipfile.ZipFile(ROOT / ARCHIVE) as archive:
        if len(archive.namelist()) != len(contents) or set(archive.namelist()) != set(contents):
            raise ValueError("archive is not the explicit allowlist")
        for name, data in contents.items():
            if archive.read(name) != data:
                raise ValueError("archive payload differs: " + name)
    archive_hash = digest((ROOT / ARCHIVE).read_bytes())
    if (ROOT / "dist/SHA256SUMS.txt").read_text(encoding="ascii") != f"{archive_hash}  {ARCHIVE}\n":
        raise ValueError("archive checksum differs")
    print(f"{len(contents)} allowlisted entries; archive SHA-256 {archive_hash}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify only; no writes")
    args = parser.parse_args()
    check() if args.check else build()
