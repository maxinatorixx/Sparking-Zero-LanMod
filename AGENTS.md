# Sparking ZERO Arena — maintainer handoff

## Objective and current status

Provide a configurable LAN server and standalone launcher while retaining the
native Battle → Online menus and game battle logic. No hosts-file edits.
The public user guide is README.md; lan/README.md maps code responsibilities.

As of 2026-10-26, casual quickmatch/battles, ordinary lobbies and cards are
user-confirmed working. Ranked combat has worked. Private-slot settings and full
tournament brackets still need fresh actual-game verification. Eight-member
transport/56 directed UDP paths are tested, not proof of a complete tournament.

The result-menu exit remains UNFIXED: creator leave deletes the native room;
the remaining bridge reports POLL3EMPTY, native cache removal uses the actual
SessionLeft reason 57C3A7BB, and the other player may black-screen/error. Keeping
an ownerless or ghost-host descriptor is not a verified rematch/exit handshake.
Do not force success codes/controller states or claim this issue is resolved.

## Ranked result contract

- Operational backend revision ranked-result1 owns the exact-build
  SetBattleResult hook, including when mod logging is OFF.
- Original reflected FKoratBattleResult.BattleWinLose is byte+0; native setter
  1423d76a0 (exec141f32200) copies0x230 to SSGameInstance+11c8. Original142216650
  verifies Win1/Lose2 strings. Enum: None0,Win1,Lose2,Draw3,Timeup4,RingOut5,
  Win1P6,Win2P7. Only own1/2/3 are reportable; otherwise0/unavailable.
- Capture is bound to a successful server-issued32hex round code. A new code
  resets; duplicate start keeps capture; a valid end seals it for retries.
- SERVICE5 carries instance,path,match_code,completion_outcome,raw_category,
  native_result,rank_snapshot_hex. Completion outcome1/2 is NOT winner identity.
- Supplied actual a9b6 capture recorded own Lose2 at19:28:26.134UTC before its
  endP2 response26.837, agreeing with the user's known result. The new reporting
  path still needs actual-game end-to-end rating acceptance.
- Server supplies accounts/roles from authenticated connection/room state.
  Persist each own report before ACK; NEVER wait for both before P1 ACK.
  Complementary Win/Lose or Draw/Draw in the same category commits once through
  ranked_reports/rank_events. Unknown/conflicting/self-play reports are unrated.
  Receipts survive first leave600s; retry must not award twice.
- LAN Elo1000/K32 is separate per Single/DP/Team. Native official titles/point
  thresholds remain separate; do not replace them with web Elo.
- Raw category1=Single,2=DP,3=TeamUnlimited. Cached native rank folds2/3, so it is
  not mode authority. Native1459ea4a0 maps raw1->sessionkind2,2->3,3->0.
- Native145923850 encodes namespace*1000+positive session kind;1459eac70 proves
  kinds2/3 are RankMatch. Elo policy applies only to proven Single/DP AFTER native
  eligibility BEFORE limit. Never guess an opaque numeric filter slot as Elo.
- Defaults±100,+100 every15s,cap±600,any Elo after120s; longer wait then smaller
  difference. Preserve queue age on retries, cancel on abort/mode/leave/disconnect.
  Rating cache5s, invalidated on finish. Config: server.example.json.
- Native stat lookup145c61350 compares type+3a/sessionkind+34/extra+39;145c617b0
  sums match/win for RankMatch kinds2/3. Both period1/2 views intentionally show
  LAN lifetime counts (no seasons). Do not project Team into kind0 or fabricate
  most-used fighter/title progression. First finisher may see old totals while
  peer report pending; fresh card/login reads committed state.

## Hook and transport invariants

Exact original Shipping SHA256:
e54e79e756f79719f09915078a37b6e87c23d32ecaaaa2f485d1a048ba198e55

Keep build/prefix/thread/argument/RAX/LastError/borrowed-memory and native-owned
response/lifetime guards. Don't globally reanalyze the game or remove guards to
support another build. Impact/clash GetWinner/IsWinner are not match winners.
Context17fa was not proven own-win authority. No guessed result or identity writes.

Optional postresult2 observer skips only its result setter when operational
backend owns it, retaining17 other hooks. Standalone observer has18. Pinned
trampolines/owned restoration and bounded recording remain required.

Current HELLO5/READY5/SESSION4 partition5 transport supports eight members and
stable per-remote loopback proxies, never reused after departure in process life.
Targeted kind4 UDP validates registered source/current destination membership.
Keep compatible legacy partitions and transactional prepare/ACK/rollback intact.

Current DLL SHA256:
- backend_adapter.dll:54e3cdf1ddcda715a8585a34e5e184557ea8ddd466033dd4d8ea445f5e5c53c6
- service_trace.dll:d9173fa5ddb621230c4d55ccf9ded671804f05856966828b93f14cf03e9689c5
- native_search.dll:6f716041541e004b2b48a224e961f75c48d4c47660de82ad9efae54b17ba4ef3

## Launcher/account/installation behavior to preserve

Logging defaults OFF and does not disable networking/ranked capture. Enable all
our logging only through the explicit mod flag; UE4SS core logging is separate.
Control/lifetime endpoint/policy files remain needed in quiet mode. Never log
credentials, raw platform auth envelopes or private-key material.

Launch performs login FIRST, before preferences/config/INI/preflight/processes.
Current password authenticates; blank uses a scoped remembered token. Failure
stops launch. Other drafts save only on Launch; explicit Login remembers token.
No new plaintext password persistence. Login uses game host/port27150 only.
Quick play stays unauthenticated and cannot play Ranked. Keep equal-sized tabs,
removed display controls and removed stutter integration.

Game must be closed for install/uninstall/save edits. Uninstall removes our
payloads/receipt directly, without new uninstall backups. Preserve original
shared-loader backups, unrelated mods and user saves. Save unlocks require
confirmation/backup and only change recognized gameplay fields, not entitlements.
Installed location: Win64/Mods/SzeroLAN or detected Win64/ue4ss/Mods/SzeroLAN.
This ranked revision changes ONLY scripts/backend_adapter.dll/service_trace.dll
versus the preceding logging release. Close/reinstall OUR mod on BOTH clients
and rebuild server for its handlers/migrations. Original EXE/PAKs unchanged.

One Compose container contains MariaDB, web and game worker. User creates .env
from .env.example; no generated secrets/start scripts. Existing secret policy
requires length>=2 only. Preserve data volumes on upgrades. DB arena_editor is
external schema editor; app user arena is separate. Auth is plain game TCP, so
use trusted LAN/VPN; web HTTPS doesn't encrypt that port. Don't mutate live user
containers, game installations, DB or Wine prefix for tests.

## Builds, tests and publication

Stage onefiles ONLY in .build/desktop. Preserve existing standalone binaries in
both dist/ and dist/desktop. Distribute complete ZIPs/checksums, not loose EXEs.
Build source Windows with Python3.13/PyInstaller6.16; Linux uses Ubuntu22.04
Docker baseline. Native strict compiler commands: lan/native/README.md.
Verify frozen Lua/DLL/license identities and full manifests, not just file names.

Last full local validation:375Python checks PASS/no skips321.867s, all6Lua mocks
PASS, including compiled quiet reporting->real bridge/TCP/SQLite, MariaDB
consensus/restarts, original ownership/ABI guards,8-peer/UDP and frozen GUIs.
This includes retired local stutter checks excluded from public Git, and is NOT
actual-game/native-Windows game acceptance. Disposable fixtures/prefix:
/tmp/szero-ranked1-build/. Log:/tmp/szero-ranked-final-full-clean.log.
Two initial test-only failures were corrected: search diagnostics now count all
native-eligible candidates before final limit; authenticated native fixture now
waits until worker observes its endpoint before simulating removal. Production
DLL was rebuilt with the same image base and verified byte-identical afterward.

User authorized public Git/release publication on2026-10-26. Remote:
https://github.com/maxinatorixx/Sparking-Zero-LanMod . Preserve initial remote
commit6f51e228e34402198e90fbaa79d521cc2e68426e; don't force-push history.
Project commit3b725fcb19a5b5e1006db50d829e36f3bf373c31 is taggedv0.1.0.
GitHub Actions run40399079913 succeeded on native Windows/Linux builds and UI/
resource checks; published experimental full-ZIP release. Downloaded manifests
and native DLLs verified. Windows checkout converted Lua to CRLF in v0.1.0;
.gitattributes now pins LF and v0.1.1 rebuilds byte-identical mod resources.
No network/game logic changed. This is not game proof.
Final published v0.1.1 run40400024277 succeeded on both native platform builds,
exact11-resource checks and UI checks, then release publication. Downloaded all
assets and verified GitHub digests, all39Arena/all204source manifest entries,
exact user screenshots/docs, and independently read back both onefiles'6Lua,
3nativeDLL, MinHooklicense and pinnedUE4SSarchive bytes against current source.
ArenaZIP:d0754e03b46a79698770926779cff445b300fb75117fdcc7992abc8e2ce3cf27
SourceZIP:d123dac5c40c3d771767d89ac9c99e57137c71c1d97ff2cff97f16c639f493c0
Local dist fullZIPs/checksums synchronized to published assets; all4 existing
dist root/desktop standalone binaries remain unchanged. Release URL:
https://github.com/maxinatorixx/Sparking-Zero-LanMod/releases/tag/v0.1.1
Future v* tags build/publish through scoped job GITHUB_TOKEN; no personal token
or SSH private key belongs in source. Private deploy key remains outside Git.
Only source/docs/our payloads/licensed UE4SS are tracked. Exclude original game,
raw local decompilation, runtime logs/saves/secrets and generated dist. User's
screenshots live in docs/screenshots; code map in lan/README.md. Full historical
notes are preserved locally in ignored analysis/ and may not exist on a clone.
