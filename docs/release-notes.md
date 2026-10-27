# Arena v0.1.2 — experimental

Tested with game **v3020 and v3022**. Native helpers now resolve functions,
globals and tables from reviewed instruction/reference patterns instead of
requiring one game executable SHA or one fixed set of addresses.

Compatible future address relocations can resolve automatically. Changed or
ambiguous instructions/layouts still refuse safely; pointer, ABI, ownership,
thread and restoration checks remain. Loader/mod/save/archive checksums remain.
Mixed game-version multiplayer and arbitrary future patches are not confirmed.

Download **SzeroLAN-Arena.zip** for both standalone Windows/Linux launchers,
the single-container Docker server, documentation and screenshots. Players
need no Python installation. The source ZIP is optional for developers.

- Game-EXE SHA restrictions removed from selection, install, launch and all six
  native helpers. Existing install receipts remain compatible.
- 147 native bindings resolve through unique patterns and decoded references.
  Worker-side initialization caches addresses; game-thread callbacks do not scan.
- Hook-coexistence tests cover helpers loading after other owned hooks, while
  damaged prologues still fail their installation guards.
- No server protocol or session-partition migration from v0.1.1.
- Preserves the README edits made on GitHub before this release.

Validation: **381 Python tests passed**, six Lua mocks and four synthetic Win64
helper fixtures. Data-only tests cover both executable versions, simulated
future relocations, hook coexistence and corrupted/ambiguous binding refusal.
Both platform launchers verify all 14 embedded mod/loader resources exactly.
Source-only fixtures do not prove every actual game flow.

Close both games and reinstall **our mod on both clients** using these
launchers. No original game EXE/PAK replacement is needed. Preserve server
configuration, `.env` and database volumes when upgrading from older releases.

**Known issue remains:** leaving the Ranked result screen can cause a black
screen/network error for the remaining player. The native exit/rematch handshake
is not fixed. Complete tournament brackets and all private-slot configurations
still need broader verification. See README.md for the complete support table.

Intended for lawful LAN play, not piracy, DRM bypass or entitlement
circumvention. No original game files or platform emulators are supplied.
Third-party dependencies retain their licenses.
