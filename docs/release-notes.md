# Arena v0.1.1 — experimental

Packaging update: Git now pins text line endings so both platform launchers
embed byte-identical Lua resources. No game/network logic changed from v0.1.0.

Download **SzeroLAN-Arena.zip** for both standalone launchers, the Docker server,
installation documentation and screenshots. Players need no Python installation.
The experimental source ZIP is optional for developers. SHA-256 files accompany
the packages. Use matching client/server versions.

- Native casual quickmatch/lobbies and player cards are user-confirmed working.
- Ranked combat has worked in actual tests. Typed round results now drive
  persistent per-mode LAN Elo, counters and streaks after both reports agree.
- Ranked Single/DP matchmaking starts at ±100 Elo, expands every15s to±600,
  and allows any Elo after120s while retaining native battle/settings filters.
- One Docker container provides the game service, account/profile/ranking
  website and MariaDB. Launcher login uses the same game TCP port27150.
- Windows/Linux one-file launchers include the pinned UE4SS loader and our mod.
  Settings save on Launch; logging defaults off; ranked reporting remains active.

**Known failure:** the player who remains on the Ranked result screen can get a
black screen/network error after the room creator leaves. The correct native
exit/rematch handshake is not fixed. Persistent results are independent of that
later failure. Latest actual-game rating acceptance, all private-slot settings,
complete tournament brackets and unusual finish flows still need verification.
Official game rank titles/seasons are separate from LAN Elo.

Upgrade by preserving `.env`/server configuration/volumes, rebuilding the server,
and reinstalling our mod on BOTH clients with games closed. No game EXE/PAK
replacement is needed. Source-only development fixtures do not prove every
actual game flow. See README.md and the support table before hosting an event.

Intended for lawful LAN play with legitimately owned game copies, not piracy,
DRM bypass or entitlement circumvention. No game files or platform emulators
are supplied. Third-party dependencies retain their licenses.
