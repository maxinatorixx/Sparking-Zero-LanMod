# Sparking ZERO Arena — maintainer handoff

## Publication authorization — v0.1.2 (2026-10-27)

User explicitly authorized GitHub push AND release, superseding all older
LOCAL-ONLY/no-publication restrictions below. Preserve upstream README commit
13901b8: user removed the fixed-EXE SHA block and game-ownership Requirements
bullet. Both edits are retained; Legal disclaimer remains. User explicitly
confirmed testing on game v3020 and v3022; document those versions as tested.
Mixed-version multiplayer remains unverified. Publish full ZIP assets only via
the existing scoped GitHub Actions release workflow; no loose dist launchers.
Temporary stash kept safely while resolving upstream README overlap; all
compatibility code/resources restored on top of13901b8 without history rewrite.

Publication COMPLETE: compatibility commit78180267b406d62f9707fefecd4987bf51c8b5f8,
annotated tagv0.1.2; upstream README13901b8 remains an ancestor, no force-push.
GitHub Actions40546720996 PASSED both native Windows/Linux builds, UI/resource
checks and scoped release job. Release:
https://github.com/maxinatorixx/Sparking-Zero-LanMod/releases/tag/v0.1.2
All4assets independently downloaded and verified against GitHub SHA256digests;
all39Arena/all218source manifest entries and source/docs/screenshots verified.
Published README retains both upstream removals and lists v3020/v3022 as tested.
Independently read back both published onefiles: all14DLL/Lua/loader/license
resources match tested source byte-for-byte. No game files, Update, analysis,
logs/saves/secrets or generated standalone EXEs were added to Git.
PublishedArenaZIP:c6d643c39331a271f7d3820c55f2a4236eff476b3a9eb74d4c1613bf990bcdce
PublishedsourceZIP:afa2efd03b55b65a112403795ebcf07930fefcc6578be8179006c0692be65ffa
Localdist completeZIPs/checksums synchronized to published assets. Publication
operations did not write any loose root/desktop standalones. Current root
standalones match the preceding local build (Linuxf383dc48...,Windows19ad6594...),
while desktop files retain7a81918b.../66e9b3ec.... The older previous-turn
/tmp/szero-multiversion-dist-before.sha256 no longer matches root files; do not
restore that historical baseline over current files. Earlier local-only ZIP hashes below are
historical and differ from native CI-built release archives. Local source
manifest remains byte-identical to the published sourceZIP. No runtime code
changed after381test validation; subsequent changes are publication docs only.

## Adaptive native bindings — local update (2026-10-27)

User supplied a newer installation under ignored `/Update/` and requested both
versions plus similar future relocations. All work remains LOCAL ONLY: no
commit/push/tag/release, no installed-game/PAK/save/prefix/live-container writes.
Original and Update Shipping executables were inspected READ ONLY; data-only PE
fixtures never execute their code. `/Update/` is now ignored in its entirety.

Shared `native_bindings.c/.h` resolves147real image bindings (148inventory
operands included one obsolete image-minimum extent). Catalog165unique recipes,
22body reference constraints and95prefix reference/section constraints. No EXE
hash, timestamp or global relocation delta selects a layout. Two independently
decoded data references/class-name constraint used where needed; field offsets,
local branch distances and non-relative instruction bytes remain constrained.
All original thread/ABI/pointer/native-owned memory/restoration guards remain.
Known reference addresses are developer metadata, not runtime allowlists.

All6helpers and shared session/stream/transport/provider code use canonical-RVA
resolution. Initialization/scanning occurs on worker threads before callbacks;
all game-thread lookups are cached binary searches. Small hook targets also use
interior anchors: an initial fault-injection run caught83byte58f19f0 anchored at
its prologue; corrected and rerun successfully. Do not reintroduce this race.
Owning-helper prefix checks additionally validate masked reference targets.
Backend revision ranked-bindings1; optional tracer schema6/bindings1. Diagnostics
include `binding_error` for missing/ambiguous/conflicting addresses.

Generator `lan/generate_native_bindings.py` uses tracked
`native/native_bindings_recipes.json` plus explicitly supplied original/new PE
paths; requires pefile+GNUobjdump only for regeneration. Ordinary builds use
checked-in catalog and need no game files. `lan/build_native.py` stages all six
DLLs with shared resolver. Fixtures use explicit identity mode only where they
supply synthetic callback addresses; production never falls back to identity.

Read-only comparison mapped all operands;122/124 bounded code comparisons
normalize identically; remaining two contain embedded switch-table RVAs/data.
Verified84session-provider,12transport,20userinfo and2pair vtable slots in order.
All124normalized16byte prefixes pass against BOTH supplied PE artifacts.
Data-only matrix passed original/new, each with simulated+0x2000section relocation,
19damaged hooked prologues, combined shift/hooks and corrupted-anchor refusal.
Separate9synthetic cases cover ambiguity, altered field/branch, wrong referenced
callee/data section and invalidPE/bounds. Resolver scan measured~3.85sperimage
once off-thread; no game-thread scans. FINAL381Python tests PASS/no skips394.516s, including both data-only artifacts
and all shift/hook/corruption cases with all124prefixguards; sixLua mocks PASS
and four manual legacy/session-host Win64 fixtures PASS. Full clean log:
/tmp/szero-multiversion-build/full-tests-final.log. Focused6native checks
also PASS66.900s. First full attempt was interrupted after a mistyped disposable
Docker image tag caused2test errors; final uses imageIDff7e388f5a9e. Legacy menu
fixture initially used a wrapping canonical base from Wine low stack: its
TEST-ONLY code buffer is now static; identity-prefix fixtures use bounded RPM
while production retains actual resolved PE/prefix guards. No production failure
was suppressed. The initial hook-coexistence failure was a realresolverissue,
fixed in the interior-anchor policy and covered by final regression.

All6DLLs rebuilt strictly, then reproduced byte-for-byte in a separate staging
directory. `build_native.py` pins preferred image bases because MinGW otherwise
hashes output paths into base addresses; ASLR/relocations remain enabled.
Both onefiles rebuilt from full source into .build/desktop only; each14embedded
DLL/Lua/loader/license resources verified exact.
Linux:f383dc481ccff65940ac5f66b46918a81ccf0aa3a930033d4ac82dc5f3734881
Windows:19ad6594212821c21588e94e42f63aebe13fc47616442fff73fba62a0e2de7bd
Final39entryArenaZIP:c2109f8fdea2491e33918341a9975438faab346004feeec2902200c61a092cf8
Final218entrysourceZIP:3c15a115058ad9295ba57bb2d1474cf21d9d34dc182a64542df3943e448c3fe3
All4diststandalones remain unchanged against
/tmp/szero-multiversion-dist-before.sha256. GitHEAD remains6d925a3; no
commits/push/tags/releases, installed-game/userprefix/liveDB mutations.

This is static compatibility evidence, not actual updated-game acceptance.
Future relocations work only while required patterns/references/layout agree;
changes fail closed. Mixed original/updated multiplayer protocol compatibility
is UNVERIFIED. Result-menu exit bug remains UNFIXED and unrelated.

## Objective and current status

LOCAL-ONLY UPDATE (2026-10-26): user explicitly requested removing ALL game-EXE
SHA gates and creating a local fullZIP before any publication. Do NOT commit,
push, tag or publish these changes. This overrides prior publication permission.
Selection/install/launch now require file presence, not EXE digest. Installer
API is install(game_root); old receipts work and drop game_exe_sha256 on update.
All6 native helpers use shared native_image.h for loaded PE64/AMD64/bounds,
retaining original prefix/pointer/ABI/ownership/thread checks. Backend hashes
only its OWN DLL for optional diagnostic identity; loader/mod/save/ZIP integrity
checks remain. Static native session partition is unchanged as historical
layout/protocol ID, not an observed EXE SHA. No server migration needed fromv0.1.1.
Backend revision ranked-layout1; tracer schema6/layout1 removes EXE digest field;
console/session metadata uses validation:native_layout, audit.lua no hash gate.
All6 helperDLLs+audit.lua installed delta; no original EXE/PAK/save/other-mod edits.
Reinstall OUR mod with new LOCAL launchers on both closed games. Native layout
compatibility remains required; removing SHA does not support every game patch.
Builds staged ONLY.build/desktop; preserve all dist root/desktop standalones.
Exact frozen payload verifier now checks14resources (all6DLLs,6Lua,loader/license).
Focused39 UI/installer/account checks PASS1.321s; native4checks PASS76.468s;
3legacy probe fixtures PASS;6Lua mocks PASS. Includes different-digest EXE
selection/install/launch, missing file refusal, legacy receipt update/uninstall,
corrupt loader refusal, PE64/bounds and changed-prefix refusal. FINAL379Python tests PASS/no skips333.248s plus6Lua mocks and3legacy native
probe fixtures. Initial full run had7errors solely from one old test fixture
passing the deleted install argument; fixed test_install_controls helper,8focused
ownership checks passed, final clean379 passed. No production failure hidden.
Fresh compiled IPC fixtures:/tmp/szero-noexesha-native; full log:/tmp/szero-noexesha-full-clean.log.
Bothonefiles rebuilt FULLSOURCE and
14embeddedresources verified exact, including all6DLLs and6Lua+loader/license.
Linux:db59ac58c279ef1adcc85035260ef86f4431a2544f3d3f7ca9065be0a7a5602c
Windows:fe40a842053c377956925eee4292d2e587841abe6954b122a995ce233a87612d
Isolatedtestserver:ff7e388f5a9e0ece7a2ae1b7d6215fe1d1ea1f331b15c0a9d71847a44e850f09.
No actual game execution or claims of arbitrary-version native compatibility.
Final39entryArenaZIP:6c54d2b168e6258b61d1866ef3a2398ead2ed5fd341b850a10e9b01d54fd0607
Final207entrysourceZIP:af229427959c26857871b9e20476abe6330a7a9e62cbfd95268c323fe9cb649e
All manifest entries/exact staged onefiles and local-only docs verified.
GitHEAD remains6d925a3; no commits/
pushes/tags/releases performed. All4diststandalones unchanged against
/tmp/szero-noexesha-dist-before.sha256. No installed-game/userprefix/liveDB writes.

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

Analyzed reference Shipping SHA256 (NOT an executable allowlist):
e54e79e756f79719f09915078a37b6e87c23d32ecaaaa2f485d1a048ba198e55

Keep layout/prefix/thread/argument/RAX/LastError/borrowed-memory and native-owned
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
- backend_adapter.dll:1ef5348df4ad88d84ed89ef086e52bd093194bc3a70ffb4e3fb538de18ff3fd1
- service_trace.dll:58376673e2bcfa2a6872cb11fde7b930a9bc029db4ca3168a25afb79a36de40a
- native_search.dll:6519320f25246a16178dffbb2be8e072c12d51369f79654cb010399318515b16
- console_probe.dll:e5b2ebbd7ff30a1b7895e49054cb3e4b9beadc04997ea3dc67057df5bbc2e3c1
- menu_bridge.dll:aa09d8938061fd842ff960c5c6bf55c2943e621172a5812755f7132233921d83
- session_probe.dll:6697d19bdde2db3e8ca4a6b12479186775cff764a58799f0c8d54c2450c08526

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
