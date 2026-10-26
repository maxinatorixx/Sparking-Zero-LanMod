"""Package only standalone players and the exact Docker server dependencies."""
import hashlib
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parent.parent
SERVER_FILES=("Dockerfile",".dockerignore",".env.example","compose.yaml","server.example.json",
    "szero_lan.py","native_sessions.py",
    "native_session_transactions.py","native_search.py","native_identity_diagnostics.py",
    "native_session_codec.py","lan_identity.py","installer.py","backend_services.py",
    "account_store.py","arena_web.py","arena_supervisor.py","native_rank.py","native_profile.py","elo_matchmaking.py",
    "web/index.html","web/arena.js","web/arena.css","web/avatar.svg")


def build():
    files={name:(ROOT/".build/desktop"/name).read_bytes()
           for name in ("SzeroLAN-Windows.exe","SzeroLAN-Linux")}
    files.update({"server/"+name:(ROOT/"lan"/name).read_bytes() for name in SERVER_FILES})
    files["DEPLOYMENT.md"]=(ROOT/"lan/DEPLOYMENT.md").read_bytes()
    files["MODES.md"]=(ROOT/"lan/MODES.md").read_bytes()
    files["ACCOUNTS.md"]=(ROOT/"lan/ACCOUNTS.md").read_bytes()
    files["MinHook-LICENSE.txt"]=(ROOT/"lan/vendor/MinHook-LICENSE.txt").read_bytes()
    for name in ("README.md", "docs/screenshots/launcher.png", "docs/screenshots/website.png"):
        files[name]=(ROOT/name).read_bytes()
    for name in ("README.md", "DEPLOYMENT.md", "ACCOUNTS.md", "native/README.md"):
        files["lan/"+name]=(ROOT/"lan"/name).read_bytes()
    files["START-HERE.txt"]=(
        "Windows: open SzeroLAN-Windows.exe. Linux: chmod +x SzeroLAN-Linux, then open it.\n"
        "No Python installation is needed. Linux still needs Wine for the game.\n"
        "Select the game folder, then Install Arena Mod. Launch Game saves settings before starting.\n"
        "Saved settings restore on open. Editing/closing do not save drafts; Launch verifies Login first.\n"
        "Server: copy server/.env.example to server/.env and fill in the three secrets.\n"
        "From server/ run docker compose up -d --build (or docker-compose up -d --build).\n"
        "This builds ONE container with MariaDB, website, and the game server.\n"
        "Website: http://SERVER-IP:8080 . First registration requires ARENA_ADMIN_TOKEN from server/.env.\n"
        "MariaDB: SERVER-IP:3306 database arena user arena_editor; password in server/.env.\n"
        "Clients: PLAYER > Quick play (casual only) or Login. Enter account credentials and click Login once.\n"
        "Login uses the SAME game host/port27150; no second address. A protected session remembers the login.\n"
        "Close games and reinstall our mod on BOTH clients; stale backend helpers now block launch.\n"
        "Allow TCP/UDP27150, web8080, database3306 as needed. Clients use the server PC's IP.\n"
        "Accounts/rating tables persist in the server-data volume. See ACCOUNTS.md before upgrading.\n"
        "Cards are user-confirmed working. Tournament capacity now supports up to eight participants.\n"
        "Ranked results persist; Elo matching starts at +/-100, expands every15s, unrestricted after120s.\n"
        "Rebuild the server and reinstall our mod on BOTH PCs; older servers lack these handlers.\n"
        "Typed native results now drive LAN Elo/counters after agreement; result-menu exit error remains open.\n"
        "Logging defaults OFF; ranking works without it. Edit server/server.example.json for expanding Elo ranges.\n"
        "See DEPLOYMENT.md for tested behavior and actual-game limitations.\n"
    ).encode("utf-8")
    files["SHA256SUMS.txt"]="".join(hashlib.sha256(data).hexdigest()+"  "+name+"\n"
                                    for name,data in files.items()).encode("ascii")
    target=ROOT/"dist/SzeroLAN-Arena.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,data in files.items():
            entry=zipfile.ZipInfo(name,date_time=(2026,10,24,0,0,0))
            entry.compress_type=zipfile.ZIP_DEFLATED
            entry.external_attr=(0o100755 if name.endswith(".sh") or name=="SzeroLAN-Linux" else 0o100644)<<16
            archive.writestr(entry,data)
    with zipfile.ZipFile(target) as archive:
        assert set(archive.namelist())==set(files)
        assert all(archive.read(name)==data for name,data in files.items())
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(digest+"  "+target.name+"\n",encoding="ascii")
    image=ROOT/"dist/SzeroLAN-server.tar.gz"
    if image.exists():
        image.with_suffix(".gz.sha256").write_text(hashlib.sha256(image.read_bytes()).hexdigest()+"  "+image.name+"\n",encoding="ascii")
    print(str(target)+" SHA256 "+digest)


if __name__=="__main__":
    build()
