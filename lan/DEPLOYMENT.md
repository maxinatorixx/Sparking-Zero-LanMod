# Arena — Docker server and standalone launcher

## Latest: persistent Ranked results and expanding Elo matchmaking

New matched clients capture the game's typed own result operationally, even
with mod logging OFF. Both participants' issued-code reports must agree as
Win/Lose, Lose/Win or Draw/Draw in the same raw battle category. Each own finish
ACK remains immediate; the server never waits for both before replying. The
second valid report commits Elo, wins/losses/draws/games and streak counters
once, transactionally. Reports and events persist in MariaDB; retries cannot
award twice. Missing/unknown/conflicting results and self-play do not award
points. Existing normal-end outcome1/2 is NOT interpreted as a score.

LAN Elo starts1000 withK32 and separate Single/DP/Team records. Website rankings
and account profiles read the current values. These are LAN ratings, separate
from official native rank titles/thresholds, which remain preserved. Native
Single/DP win-rate rows now use confirmed LAN lifetime counts. The game reads
native period IDs1/2 separately; this server has no seasonal reset, so both views
show the same lifetime counts. TeamUnlimited is not projected into a fake native
Ranked session_kind0. Most-used fighter data and official native max-rank/title
progression are not fabricated. The first finish response can show previous
counters while the peer report is pending; a fresh login/card request loads the
confirmed counts for the next Ranked attempt.

Ranked matchmaking applies Elo AFTER the original native eligibility/settings
predicate and BEFORE the one-result limit. Verified compatibility session kinds
2/3 identify Ranked Single/DP across native namespaces; casual Quickmatch, public/
private lobbies and tournaments retain their original ordering/filtering.
Both sides must have authenticated account ratings. Priority is the pair with
the longest-waiting participant, then the smaller Elo difference, with stable
server owner-ID tie-breaking. The longer wait controls the allowed difference.
Retries/advertisements preserve queue age; cancellation, mode change, leave and
disconnect clear it. Fresh rating reads have a5second cache, invalidated on
result submission. Original native room/filter/settings restrictions still apply.

Edit the mounted `server.example.json` section `elo_matchmaking`:

```json
"elo_matchmaking": {
  "enabled": true,
  "initial_range": 100,
  "range_step": 100,
  "expand_interval_seconds": 15,
  "maximum_range": 600,
  "any_rating_after_seconds": 120,
  "queue_ttl_seconds": 600
}
```

This permits±100initially,±200at15seconds,±600at75seconds, and any Elo after
120seconds. It never permits an otherwise incompatible native match. Restart
Compose after configuration edits. Old configuration files without the section
use these defaults.

The supplied a9b6 capture records actual native `Lose` before maxinator's P2
finish, matching the user's report that matsi won. The new backend owns the
verified result-setter hook; optional postresult2 tracing skips that same setter
and keeps its other17hooks, avoiding duplicate hooks. No logging is required for
ranking. Actual updated-game result/rating acceptance still needs a test.

**Remaining issue:** the non-menu player's result-screen exit can still show a
black screen/network error when the host leaves. Read-only analysis confirms
host departure revokes the session and our native cache removal reports the
original `SessionLeft` reason57C3A7BB. The correct graceful result-menu handshake
has not been recovered; no guessed success code or forced controller state is
applied. A correctly committed result remains recorded despite this later exit.

Upgrade: use the NEW full ZIP, merge server files while keeping `.env` and data,
then `docker compose up -d --build`. Close both games and uninstall/reinstall OUR
mod on BOTH PCs using the new launchers. Installed-game deltas from the previous
logging/postresult1 package are ONLY `backend_adapter.dll` and
`service_trace.dll` in `SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/` (or
installer-detected `Win64/ue4ss/Mods/SzeroLAN/scripts/`). Original EXE/PAK/loaders,
other mods and saves are unchanged. Existing accounts/rankings remain; new
report table and streak columns migrate automatically. No old test match is
silently backfilled from a user name or incomplete historic capture.

Earlier sections below are historical where they conflict with this update.


## Latest launcher logging/login and result-capture update

**Enable mod logging** replaces Record online checks and defaults OFF, including
first launch and legacy trace-only preferences. It controls our bridge log,
native session/backend reports, Lua messages and optional online/result observer.
Runtime/endpoint/control files remain required for communication. UE4SS itself
may still create its own engine log; our Lua messages are suppressed. Existing
log files are not deleted. Enabling logging does not enable automatic ratings.

When Login is selected, Launch verifies the current supplied password first;
if blank, it validates the remembered server/user-scoped session. Authentication
failure reports an error and stops before settings/config/INI writes, patch
preflight or any bridge/game process. Successful Launch then saves all settings
and optional UserName INI before starting. Explicit Login still works.
Uninstall directly deletes our validated payload files and receipt, without
creating a new uninstall-backup directory. Existing install-time backups of
original configuration/shared files remain available; other mods are preserved.

The previous winner/loser labels (maxinator/matsi, winner using GokuSSJ4) suffice
to label that recorded match. The old capture lacks the native typed result.
A new optional `postresult1` observer records exact
`SSGameInstance::SetBattleResult` / `FKoratBattleResult.BattleWinLose` using the
verified native setter and enum. Schema5 event `native_battle_result` includes
readability/validity, enum and label: None0, Win1, Lose2, Draw3, Timeup4, RingOut5,
Win1P6, Win2P7. Original code also ties1/2 directly to WIN/LOSE strings. No state,
borrowed data, result or rating is modified. The existing bounded512event/time/
thread/cleanup safeguards remain. Actual Ranked result timing/value still needs
a fresh game capture; the old outcome1 on both clients is not enough.

For that capture: close/update both clients, tick **Enable mod logging** on BOTH,
Launch (which saves the checkbox), play one short Ranked match, then press Next.
Keep both `native_service_trace_<id>.jsonl` and
`native_backend_adapter_<id>.jsonl`, plus client logs and server logs if an error
persists. Note winner/loser names. No further character/account details or old
identical captures are needed. Turn logging off again for normal play if desired.

Upgrade from battle-end2/profile-sync1: rebuild server from the complete ZIP and
close games/uninstall/reinstall OUR mod on both PCs. Changed installed payloads
are `backend_adapter.dll`, `native_search.dll`, `service_trace.dll`, plus
`main.lua`, `native_search.lua`, `native_menu.lua`, `panel.lua`, `audit.lua`,
`session_trace.lua`, under `SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/`
(or detected `Win64/ue4ss/Mods/SzeroLAN/scripts/`). Session DLL change only gates
its diagnostic report; no transport/session protocol logic changed. Original
EXE/PAK/loaders/other mods/saves remain unchanged by development.


## Latest paired finish update: profile-sync1

Both supplied winner/loser captures use the correct battle-end2 helper. Both
normal finish requests reach the server successfully; both game screens show the
correct Victory/Defeat. Afterward the winner's adapter refuses
`/user/update_proficiency_rank.php`, and the loser's adapter refuses
`/user/update_player_rank.php`. These are recovered profile synchronization
operations, separate from match-score submission. The exact UI error attribution
still needs an actual updated-game test.

Revision `profile-sync1` implements both requests with their exact typed fields:
`player_rank` signed int8, or `character_id` string plus
`character_proficiency_rank` signed int8. The native adapter strips the common
authentication envelope and sends only approved fields. Each valid update is
acknowledged only after saving its own account state. Account state persists in
MariaDB table `native_profile_state`; guests retain it only for their connection.
Fresh login and own/opponent room cards load the saved state. Independent
accounts remain isolated; no body-selected account ID is accepted.

The selected card badge and character proficiency are not Elo. The existing
server LAN Elo policy is1000initial/K32, separate for Single/DP/Team, but automatic
result ingestion remains DISABLED. Both captured finish requests contain
`outcome:1`; this is not a caller-relative win flag. Original-code recovery now
proves raw native categories1Single/2DP/3TeamUnlimited, while cached rank lookup
mergesDP/Team. Winner mapping remains insufficiently proven. This update does
not award rank points or repair match win-rate counters, and does not reinterpret
a selected card badge as a competitive rating. No official ranking formula is
claimed.

The launcher removes display/resolution controls. Launch saves game defaults for
those retired overrides before starting processes. Quick play and Login tabs
now have equal dimensions and consistent padding in both selection states.
Other save-on-Launch/login behavior is preserved.

Update the server files and run `docker compose up -d --build`. Close both games,
then uninstall/reinstall OUR mod using the new full ZIP launchers on BOTH PCs.
Installed-game delta: ONLY
`SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/backend_adapter.dll`
(or detected `Win64/ue4ss/Mods/SzeroLAN/scripts/backend_adapter.dll`).
Session transport, card identity mapping, Lua, tracer, originalEXE/PAK/loaders,
other mods and saves are unchanged by this update. Existing account/ranking
tables are retained; the new native-state table is created automatically.

Earlier sections below are historical where they conflict with this update.


## Latest 295f update: normal Ranked match completion

The user confirms Ranked combat now runs successfully. In the supplied run,
both start handlers succeeded and the server relayed4673/4701 gameplay packets.
At20:44:12.765UTC the previous adapter refused an unsupported request immediately
before both native leaves; TCP connections stayed open. This is consistent with
the missing end operation, rather than a TCP server crash. The old refusal did
not record its exact route. The user reports maxinator won.

Revision `battle-end2` implements the recovered normal
`/pvp/end_battle_player1.php` and `/pvp/end_battle_player2.php` contracts. Each
caller must own the issued match code and role, authenticate, and have completed
both start operations. The native adapter extracts only the code, numeric outcome
and the caller's current native rank snapshot. Tickets and arbitrary request
bodies are never forwarded. Peer2 start now also validates the native-issued
code, preventing a stale retry from joining a new round.

The server acknowledges each valid report immediately: original P1 reports
BEFORE its final peer connection, whereas P2 reports AFTER it. Waiting for both
reports before acknowledging P1 can deadlock. Duplicate reports are idempotent,
conflicting outcomes are refused, and the first accepted snapshot remains fixed.
Bounded600second receipts allow the remaining player to finish after the first
leaves. A new round receives a new code; late reports cannot change that round.

The response echoes each player's own verified native rank record so the game's
original result consumer does not zero existing rank values. A missing record
uses the exact recovered native fresh-entry constructor. No account Elo, wins,
rank points or penalties are awarded. Force-end and additional outcome types
remain unsupported. Actual game acceptance of this completion update and rematch
still need validation; passing synthetic native tests is not game proof.

Rebuild the server using `docker compose up -d --build`. Close both games and
use the new full ZIP launchers to uninstall/reinstall OUR mod on BOTH PCs.
The installed-game delta is ONLY
`SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/backend_adapter.dll`
(or installer-detected `Win64/ue4ss/Mods/SzeroLAN/scripts/backend_adapter.dll`).
Session helper, postpair3 tracer, Lua, cards, original EXE/PAK/loaders, other mods
and save files are unchanged by the development update. Backend log header is
schema3/revision `battle-end2`; end exchanges record raw outcome and whether a
fresh-entry snapshot was needed, without logging rank values or credentials.

Earlier sections below are historical where they conflict with this update.

## Latest 985e/812b update: LAN battle-start handshake

Both supplied postpair3 captures now reach native preparation, future result,
peer startup and connection success. They are separate attempts, not both ends
of one session. The earlier connection boundary is no longer the unknown. A
later original Steam HTTP failure is present, but its exact parent is not
identified by the supplied trace.

Selected original-code recovery establishes a separate required ranked battle
start: `145a81010` calls `/pvp/start_battle_player1.php` for the local first member.
Original parser `145a27f90` consumes root `match_code` (string) and `match_phase`
(integer). `145a833d0` stores the code and broadcasts it using native command21.
The other player waits through `145a733d0`/context+14b8 for that code, then calls
`/pvp/start_battle_player2.php`. Our earlier adapter/server supported neither
route. This is a concrete missing backend contract consistent with the later
failure; the existing trace alone does not prove its exact runtime call site.

The new `battle-start1` backend supports those TWO exact routes. First caller
must be the actual first member of a committed, current two-participant native
LAN room; the second caller must be its second member. Both must authenticate
and complete LAN login. The server creates one opaque `match_code` for that
room/ordered membership. Retries return the same code; the second route requires
the first record. Leaves/rejoins, roster changes and disconnects invalidate it.
Native membership IDs fence a stale record even if a notification was missed.
Bodies, requested account IDs/roles/codes, outsiders, guests and other room sizes
are refused. Native request bodies, platform tickets and fighter/stage selections
are not forwarded; the server derives ownership from its live TCP peers.

Replies pass through the game's original HTTP/JSON projection and validation.
The root envelope is `res:0`; the shared code is nonempty32hex and `match_phase:0`
is the parser's initial phase (this consumer does not use it to force gameplay).
No native success flag, filter, identity or timeout is overwritten. Existing
channel transport sends the code to the opponent. Battle records are ephemeral
per room, not completed results. Ranked battle completion, rematch lifecycle,
end-battle reporting and automatic Elo/result ingestion remain unverified or
unsupported; no full Ranked gameplay claim is made before an actual game test.

Use the NEW full ZIP, rebuild/recreate the server with
`docker compose up -d --build`, close all games and reinstall OUR mod using its
launchers on both PCs. The installed-game change from postpair3 is ONLY
`SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/backend_adapter.dll` (or detected
`Win64/ue4ss/Mods/SzeroLAN/scripts/`). Native session DLL, postpair3 tracer, Lua,
original EXE/PAK/loaders, other mods and saves are unchanged. Updated launchers
include the two additional route-only IPC operations. Old server images lack
these handlers and must be rebuilt.

Backend log header is schema3/revision `battle-start1`. Exchange and refusal
records now include UTC worker timestamps; refusal timestamps are batch-flush
times. The server logs each exact start route with state=ok/refused. A bounded
`battle_start_foreign_or_unbound_service` diagnostic preserves existing service
ownership/delegation rather than silently binding an unrelated service. Keep
online checks enabled for the next Ranked attempt; if it still fails, the new
backend log and postpair3 trace identify whether this handshake was reached.

Earlier sections below are historical where they conflict with this update.

## Latest ef680 Ranked capture: postpair3 recorder

The supplied postpair2 recorder stopped before the first search, which began
about six minutes after launch. The server still paired both peers and relayed
1039/1032 packets before native leave. No post-pair native return was captured,
so this run cannot identify the remaining connection failure.

The updated observer records initial menu/service checks for five minutes,
then waits quietly for preparation/connection until thirty minutes from startup.
The first selected post-pair entry starts one five-minute connection window;
maximum lifetime is thirty-five minutes, still512events and no repeated renewal.
Unrelated calls during quiet waiting are forwarded without consuming events.
The ring and pending return tokens are preserved. Bridge close, event cap and
log errors still stop and restore owned hooks. Header revision is `postpair3`;
`waiting_for_pair` and `pair_capture_started` explain recorder state. Footer now
distinguishes `pair_wait_timeout` and `capture_timeout`.

Close games and reinstall OUR mod using the new ZIP launchers on both PCs.
The installed-game change from modes4 is ONLY
`SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/service_trace.dll` (or detected
`Win64/ue4ss/Mods/SzeroLAN/scripts/`). The native session DLL, card backend and
Lua are unchanged. The launcher also restores a missing first-received UDP log
for targeted packets; delivery behavior is unchanged. No server rebuild or
protocol change is required when upgrading from modes4.

Enable **Record online checks**, launch fresh games and reproduce one Ranked
failure. The recorder now accommodates time spent in menus. Send each client's
`native_service_trace_<launch-id>.jsonl` and client log. This is a diagnostic
coverage fix; Ranked combat is still unresolved. The server evidence does not
justify forcing native success or altering its filters/identities.

Earlier timing limits below are historical; this section takes precedence.

## Current update: tournament capacity and Ranked connection tracing

Cards are now confirmed working by the user. Their adapter and server response
contract are preserved in this revision.

The latest tournament capture refused `member_capacity=8` before any server
create request. The former two-member adapter has been extended to a bounded
**eight-member** session path (`modes4`, HELLO5/SESSION4, LAN partition5). Capacity,
member snapshots, native owned copies, user-info lookup and UDP routing now share
that bound. Every remote participant has a distinct, stable local UDP endpoint;
the server relays only to the specified current room member. Old two-member
protocols remain isolated and compatible. Opaque game settings and matchmaking
filters remain unchanged. Larger capacities and multi-result browsing remain
unsupported. This removes the captured capacity refusal; actual tournament
creation, bracket progression and fighting still require game validation.

The relay keeps at most64 remote endpoint identities for one game process and
never gives a departed identity's port to someone else. Restart the game after
exhausting that lifetime bound. No additional public server ports are required:
the existing TCP/UDP27150 connection carries targeted routing. All participants
must use the updated launcher/mod/server for the new partition.

Ranked remains unresolved. The latest matched attempt completed native
preparation and forwarded923/946 game datagrams, including packets larger than
keepalives. The previous diagnostic expired six seconds into native connection;
its unfinished call is not proof of a crash. The new `postpair2` observer records
peer resolution, native future completion, commit and peer startup. Its initial
five-minute window extends once when preparation/connection begins, bounded at
ten minutes total and512events. It changes no native result or game timeout.

Close games, rebuild the server with `docker compose up -d --build`, then use
the launchers inside the new full ZIP and uninstall/reinstall OUR mod on every
PC. Installed deltas from the preceding package are ONLY
`SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/native_search.dll` and
`scripts/service_trace.dll` (or installer-detected `Win64/ue4ss/Mods/SzeroLAN/`).
The backend/card DLL and Lua are unchanged; original EXE/PAK/loaders, other mods
and savegames are unchanged.

For one new Ranked attempt, enable **Record online checks (extends after
pairing)** on both clients, launch fresh games and begin searching within five
minutes. Keep the games running through the connection failure. The useful files
are each client's `native_service_trace_<launch-id>.jsonl`,
`lan_runtime_<launch-id>.client.log`, `native_search_<launch-id>.json`,
`UE4SS.log`, and the matching server log. This capture can distinguish the
unobserved inner connection branches; it is not a claimed Ranked gameplay fix.

The sections below describe historical revisions; this section takes precedence.

## Accounts and native cards — current update (2026-10-25)

Use the complete ZIP. Copy `server/.env.example` to `server/.env` and fill in
the three secrets, then run `docker compose up -d --build` from `server/`.
Compose builds and starts ONE container containing the
game server, website on8080 and MariaDB on3306. Existing game27150 TCP/UDP stays
available. Accounts/profile/ranking tables persist in the new `server-data`
volume; logs remain in `server-logs`. Read [ACCOUNTS.md](ACCOUNTS.md) for the first
admin token, database editor credentials, reverse proxy configuration and backup
details. No live server is replaced by development or test commands.

The PLAYER area offers Quick play and Login tabs. Quick play preserves casual
play. Clicking Login verifies the account through the SAME game host/port27150;
there is no separate website address or web-management button. The server
supplies the profile display name. Passwords are never saved. The
remembered token stays in protected launcher preferences, outside the game
configuration; explicit Login saves this session immediately. Other settings
and the optional existing INI name are saved BEFORE
preflight, bridge creation and game launch, as before.

The new helper gates native Ranked entry for Quick play. An instance policy
file is enabled only by a server-authenticated welcome. Logged-in startup
preserves the native entry and optional diagnostic tracer. Quick-play diagnostics
are disabled because their hook overlaps the guest Ranked gate. Game restart is
required to change account ownership. This is LAN account access, independent
of Steam ownership or official online progression.

Cards now have a bounded target-only IPC request: exact local identity becomes
`self`, and remote targets must use a live `szlan:` principal in the caller's
current session. Official platform IDs and native request credentials never
leave the process. The response includes the verified scalar `player_rank`
presence that the original card validator requires, with explicit default
fields and booleans. Native card rendering is now user-confirmed working.
Website artwork IDs are not passed as invented native asset IDs.

Both clients must uninstall/reinstall OUR mod with the updated ZIP launcher.
The installed delta from backend3 is ONLY
`SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/backend_adapter.dll`
(or detected `Win64/ue4ss/Mods/SzeroLAN/scripts/`). Original EXE/PAK, loader,
other mods and savegames are unchanged. The server context must be rebuilt.
Use the new standalone launchers INSIDE the ZIP; existing standalone `dist`
files are deliberately preserved.

LAN Elo storage/result transactions exist, but automatic native battle-result
ingestion remains unsupported; the rankings page states this. Ranked menu entry
is not proof of a completed ranked match or persisted progression. The latest
two-client report identifies a completion-rate search/room mismatch (key7,
query0, candidate80). Original145a5d990 proves this is the requested minimum
completion threshold, not rank. Our login advertised0% for every new player;
fresh LAN profiles now use clean100%, preserving the original comparison.
This fixes the source datum behind the captured rejection. It is not yet proof
of completed two-player Ranked gameplay.

## Latest supplied matched-ranked runs:36e2/fcd97

The completion correction now admits both peers to the same session. Actual
Docker logs show create/join committed, bidirectional UDP forwarding, then host
flags40→43, followed by native leave after the loading delay. First-packet logs
are not a full packet trace; their2-byte sizes do not prove no larger packets
followed. The server now records bounded aggregate forwarded counts/byte totals
and min/max size when a native session ends, without payloads.

Original14599c540 waits for two members and native readiness before that flag
transition, then continues through peer preparation1459bd290 and connection
1459aecb0. The optional online-check tracer now also observes those two exact
boundaries (`post_pair_prepare`, `post_pair_connect`) with unchanged original
arguments/results, to locate the later failure. This is targeted evidence for
the still-unresolved loading failure, not a forced-success transport patch.

The external installed backend DLL was backend3 (`6e0bdc...`), without card
support, while the previous ZIP already carried the card-capable42c687... helper.
The launcher now checks backend_adapter.dll and native_search.lua unconditionally,
so mixed versions cannot launch. The new helper logs schema2 revision
`accounts-card2` and its exact SHA plus bounded refusal enums. Do not treat the
old schema1 logs as proof that the new card path failed.

Close both games, use the updated ZIP launcher, uninstall/reinstall OUR mod on
both PCs, rebuild the server, and start fresh game processes. Changed installed
payloads from the preceding accounts package: ONLY
`scripts/backend_adapter.dll` and `scripts/service_trace.dll`, under
`SparkingZERO/Binaries/Win64/Mods/SzeroLAN/` or the detected `Win64/ue4ss/Mods/`
variant. SessionDLL, Lua, original EXE/PAK, other mods and saves are unchanged.
Actual card rendering and Ranked battle completion remain unverified.

Earlier sections below document previous revisions and are historical.

## Backend completion handoff — backend3 (2026-10-25)

The f207 report proves the backend2 response correction passed real native login
once (login response/backend/service all code0), including transaction checking.
Later handlers return57C80000 without corresponding follow-up IPC requests.
Source review and a deterministic compiled regression found our completed job
remained busy until the worker's next poll. Native continuations can immediately
issue another request during that gap. The helper now releases a completed job
before returning, after projection and cleanup finish. Worker cleanup uses CAS
so it cannot overwrite the next job. Cancelled/in-flight buffers remain owned
until the worker acknowledges completion; genuine concurrent calls still refuse.
This is a reproduced adapter bug consistent with the supplied failures, not a
runtime breakpoint proving every57C80000 in that run had this cause.

Close games, use the launcher from the **new complete ZIP**, then uninstall and
reinstall **our Arena mod** on each client. The only installed-game delta from
backend2 is `SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/backend_adapter.dll`
(or the detected `Win64/ue4ss/Mods/SzeroLAN/scripts/` variant). The server is
unchanged; keep the backend2 server with its `res:0` correction. No server rebuild
is needed if that version is already deployed. Existing original game files,
other mods, settings and saves are untouched by development work.

Actual in-game acceptance after this handoff fix remains unverified. Player-card
target mapping and ranked results/progression remain unsupported. Source tests
now explicitly pause the worker after DONE and require immediate reuse, and the
real bridge fixture exercises all five routes without waiting between calls.

Linux launcher was rebuilt normally. The earlier disposable Windows build runtime
had been cleared, so its existing launcher was refreshed with the pinned
PyInstaller6.16 archive API: only the bundled backend DLL changes; all other
payloads/Python bytecode/runtime/bootloader bytes are verified identical, with
the PE checksum updated and original archive Python version preserved. Actual
Windows onefile GUI/bridge tests under disposable Wine pass. Standard full builds
via Build-Launcher.cmd/build_desktop.py remain supported. No standalone executables
in dist were overwritten; delivery remains ZIP-only.

## Backend response correction — backend2 (2026-10-25)

The1080 test confirmed eight login responses arrived (653 bytes each), but the
common native backend wrapper rejected them before the login-response handler:
our successful responses omitted the required top-level integer `res: 0`.
Original145ad0500 explicitly maps missing `res` on an HTTP2xx result to55E5E2BF.
This correction adds that field to successful known LAN operations only;
unsupported routes and invalid requests still refuse. Route-specific fields
remain at the root; no `data` wrapper or native success override is introduced.

**Server-only deployment:** extract the complete updated ZIP, then run
`docker compose up -d --build` from its `server/` folder. Restart the game after
the server is recreated. Existing backend1 clients/DLLs are compatible and need
**no repatching**. Both client executables in this ZIP are intentionally unchanged.
The live server was not redeployed automatically. Older offline server images
do not contain this correction.

This fixes the identified response omission, not a claim of verified in-game
Ranked operation. Player-card target mapping and ranked result/progression
handling remain unsupported. Both reported UI failures stopped at login before
reaching their later feature-specific operations.

## LAN backend transport update (2026-10-25)

This is an operational LAN service adapter, not another diagnostic-only update.
The supplied466 trace proves all ten captured HTTP attempts failed when Steam
returned a zero request handle, before sending. Service readiness had passed.
The new separate helper replaces the exact title backend exchange for five
verified routes: login, transaction check, notices, report counts and shop banners.
Responses come from the configured LAN server, then go through the original
native JSON parser and login/maintenance continuations. No Steam tickets, native
request bodies, account IDs or official URLs cross the new IPC/network path.
No account authentication or readiness result is forced successful.

Close games. Extract the **complete new ZIP**. In its `server/` folder run
`docker compose up -d --build` to rebuild/recreate the server. Older offline
server images do not contain these handlers. On BOTH clients use the new
launcher to uninstall/reinstall **our Arena mod**, then launch normally. No new
checkbox, host-file change or additional address is required; existing saved
server/player settings remain the source of configuration. This workspace's
live server and external game installations were not updated automatically.

Installed-game changes relative to the last diagnostic package:

- NEW `SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/backend_adapter.dll`
- UPDATED `SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/native_search.lua`

For nested UE4SS use `Win64/ue4ss/Mods/SzeroLAN/scripts/` instead. The working
`native_search.dll` remains byte-identical (`10af5494...df1d3f`). Original EXE,
PAKs, saves, loaders and other mods are not changed. Existing installer backups
and receipts apply. Staged standalone binaries stay outside `dist`; only complete
ZIP packages are published there.

The adapter is exact-build guarded, yields cooperatively on the known game
thread, and does network I/O on a worker with bounded waits. It accepts only
responses for its launch instance and live TCP peer; disconnect invalidates
cached ownership until game restart. Unknown routes fail rather than returning
generic success. Header maps and streams use original native allocation/cleanup.
Reports are `native_backend_adapter_<launch-id>.jsonl` beside the mod scripts;
`response_received` means response bytes arrived, **not** successful game parsing.

Verification covers compiled synthetic Win64 hooks, the real bridge/server,
ownership/cancellation/restoration and both frozen launcher runtimes. Actual
Ranked entry/gameplay acceptance still requires an in-game check. This server
starts a fresh LAN profile with no official ranks; it does not submit official
ratings/results or persist LAN rating progression. **Player-card target mapping
is not implemented**, so own/opponent card requests still refuse. Do not treat
this transport fix as completion of all ranked/card/Shop features.

The sections below retain earlier release history; older statements about this
specific HTTP boundary being unidentified are superseded by this update.

## Modes3 helper update (2026-10-25)

The latest Linux report records create refusal at00:20:18 Berlin time for the
exact40-byte borrowed-view settings stream146d36f80. Modes3 adds bounded capture
of that original type (including empty buffers) without changing wire protocol,
filters, capacity, identity or the working lobby/Quickmatch paths. This addresses
that specific pre-server refusal, consistent with the reported private-slot
creation error00000413; actual private-slot creation/join validation is pending.
The supplied Windows report confirms the same create refusal at00:25:33 Berlin
time, with no native searches recorded. Ranked error57C80000 is not uniquely
attributable from these logs and remains unresolved. No ranked fix is claimed.

With games closed, uninstall/reinstall OUR Arena mod using the updated launcher
on each client. Installed-game delta from rooms2: only
`SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/native_search.dll`
(or the same path under detected Win64/ue4ss/Mods). OriginalEXE/PAKs/saves and
other mods are untouched. Server update/restart is not required.

## Arena2.1 update (2026-10-25)

The user confirms rooms work and Linux edited saves load successfully.
Multiplayer/helper/server behavior is unchanged in this launcher-only update.
Windows save checks now handle pathname/descriptor ctime differences correctly;
file identity, size, mtime, per-API stability, content rechecks and backups remain.
Disposable Windows-runtime copies pass confirmed character and earned-content
unlock/write tests. Native Windows game acceptance remains a separate test.

Stutter Free is removed from the UI, launch integration and both executable
payloads. Already-installed rendering files are NOT silently deleted. If you
enabled it previously, close the game and untick it in the OLD launcher before
replacing that launcher; this restores its verified managed backups. Do not
blindly delete rendering DLLs belonging to another mod. The old receipt and
backups remain at Win64/SzeroStutter-install.json and SzeroStutter-backups/.

## Arena2 controls

### Optional online-service diagnostics (Ranked / player cards / Shop & Customize)

These errors are not fixed by this diagnostic build. To capture the missing
client-side boundary, close the game, replace the launcher, then uninstall and
reinstall **our Arena mod** with it. No server restart/update is required.
The only installed-mod changes are:

- `SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/native_search.lua`
- NEW `SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/service_trace.dll`

For a nested UE4SS installation use `Win64/ue4ss/Mods/SzeroLAN/scripts/` instead.
Normal installer receipts/backups remain in effect. Original EXE/PAKs/loaders,
other mods, saves and the existing multiplayer `native_search.dll` are unchanged.

Enable **Record online checks (extends after pairing)**, then click Launch Game.
The checkbox, like all settings and the optional INI username update, saves
before the game starts; editing alone does not save it. With the flag off the
probe DLL is not loaded and no diagnostic hooks run.
Within five minutes try Ranked, your own player card, the opponent player card,
and Shop & Customize, noting the order/times. Send the new
`native_service_trace_<launch-id>.jsonl` beside the mod scripts. `UE4SS.log`
prints its exact path; send that too if the trace is absent or lacks `ready`.
The existing server log cannot expose these unrecorded native client returns.
Uncheck the option on the next normal launch.

The probe verifies the exact original executable SHA and ten16-byte in-memory
entry prefixes before applying temporary **in-memory** function detours. It
does not patch the EXE on disk. It records actual input masks/category and
plain40/tagged48 result codes without changing arguments, results, identity,
ownership, readiness, authentication or maintenance settings. No tickets,
identity strings, packet bodies or raw pointer addresses are logged.
Schema3 additionally traces the platform login-provider result, backend login
operation, and login-response handler. A provider-success payload is never
read/logged; `code_valid=false` means its zero code is a placeholder, NOT a
successful result. The original a696 capture isolated outer login failure but
did not distinguish these inner boundaries. This update changes only the
optional `service_trace.dll` compared with that diagnostic build; the existing
Lua adapter and working multiplayer DLL remain byte-identical.
Schema4 additionally records the Steam HTTP exchange and exact native failure
branch (`failure_origin`), plus the cached backend status with a validity flag.
All11 helper call sites are checked as original instructions before installation.
Shared helpers record ONLY those HTTP callers; other callers pass through.
Markers do not contain output status (`code_valid=false` is intentional).
This distinguishes request creation/setup failure from cached backend refusal
and later async failure. It is NOT a replacement backend or a Ranked fix.
For this increment, one fresh Ranked-entry attempt with diagnostics enabled is
enough; repeating every card/Shop action or changing accounts is unnecessary.
Capture is limited to512 events and five minutes on the known game thread,
not all game threads or every service API. It also stops when the bridge's
instance endpoint disappears (normal close/disconnect and launcher pipe EOF).
Hooks normally restore original instructions on stop; `stopped.restored` reports
the actual outcome. Pending native fibers keep valid process-pinned trampolines;
returns after capture shutdown are intentionally not recorded. A nonzero
`inflight`, unreadable result or missing return is incomplete evidence, not a
game rejection. `candidate_parent` is inferred same-thread correlation and
does not prove fiber ownership. No automatic equation between cooked menu enum
values and native check masks is made.

MinHook v1.3.4 is statically bundled in this optional DLL, with its BSD license
in the distribution and launcher resources. No additional installation is
needed. Do not combine this diagnostic with other native instrumentation of
these functions. If hook installation/restoration fails, the log reports it;
retained wrappers forward the originals without further recording rather than
leaving exception traps or freeing live trampoline code.

Select Game Folder only selects the installation. Install/Uninstall Arena Mod
is a separate button; other controls are disabled until a valid folder is selected.
Settings restore from the previous run; edits save only on Launch Game. DX11 and skip
splash controls/arguments have been removed, including migration of old settings.
The window and Windows executable use an original four-star orb icon.

Unlock Characters and Unlock Earned Content require a selected
`MainGameSaveData` (DataVersion12), all games closed, preview and confirmation.
The broader action currently covers verified base-game characters, character
items and music only, not stages, cosmetics, titles, story completion or DLC.
It preserves other fields, creates a verified sibling `.SzeroLAN-backup-*.bak`,
rechecks the source and atomically replaces only the selected save. Keep that
backup: Linux game acceptance is user-confirmed, Windows game loading still
needs confirmation. Restore
the backup as `MainGameSaveData` with the game closed if needed. The supplied
workspace originals were never edited or distributed.

Rooms2 adds an exact-build scoped LAN user-info adapter for the observed
room-join flag0x200; Quickmatch0/0x28 paths and all server admission filters
remain unchanged. Real IDs retain the original Steam path; known LAN IDs never
go to Steam's numeric-ID parser. The user confirms lobby mode now works.
Only `Mods/SzeroLAN/scripts/native_search.dll` changes in our native runtime
from rooms1. With games closed, uninstall/reinstall our mod using the new launcher
on each client. Shared UE4SS loaders, other mods, JSON settings and saves remain.

Closing the launcher stops its bridge. Killing it closes the private parent
pipe, causing the embedded bridge to close TCP/native connections. This uses
the server's existing disconnect cleanup, not a fabricated wire message.
Power loss/network loss cannot send a final packet; heartbeat timeout remains
the fallback. Closing/disconnecting does not terminate the game itself.

`SzeroLAN-Arena.zip` is the player/server distribution: two executables plus
the minimal `server/` Docker context. `SzeroLAN-experimental.zip` retains the
full tools/source/build scripts. Source build instructions below apply to that
full tools folder or the repository, not just the minimal server context.

Delivered launchers were built on Ubuntu22.04 (Linux x86-64/glibc2.35) and with
WindowsPython3.13.17 under disposable Wine. Both actual one-file GUI/resources
and embedded bridges were smoke-tested; native Windows PC/game launch validation
is still separate. The earlier desktop regression suite passed190tests without skips,
including real Docker TCP/UDP relay, plus all6Lua checks. The game was not
launched by these packaging tests.

The user reports that fix8 Quickmatch worked. The rooms1 helper retains that
path and adds capture for the exact allocator-less64-byte native stream
`146d15df0`. This removes one known refusal, not all lobby/ranked limitations.
See [mode support](MODES.md). No original game files or supplied saves are patched.
With games closed, run normal setup/update on each client before launching.
Only our installed `Mods/SzeroLAN/scripts/native_search.dll` changes from fix8
(under the detected `Win64` or `Win64/ue4ss` mod root). Server protocol unchanged.

## Server: Docker Compose

On a machine with Docker Engine/Desktop and Compose installed, extract the
tools folder, open a terminal in `lan`, then:

```sh
docker compose up --build -d
docker compose logs -f
```

First copy `.env.example` to `.env` and set its three secrets. The standalone
`docker-compose` command can be used in place of `docker compose`.
The server binds0.0.0.0 inside the container. Both **TCP and UDP27150** are
published; clients enter the server machine's actual LAN IP, never0.0.0.0.
The image runs as UID/GID10001, with a read-only root filesystem, no added Linux
capabilities, and a named volume for rotating logs. Sessions are in memory;
restarting the server disconnects games. Close/relaunch games after a restart.

No account/password is added. Restrict the published ports to your trusted LAN
using the host firewall. To bind only a particular host interface or change the
published port (Linux shell example):

```sh
SZERO_BIND_IP=192.168.1.20 SZERO_PORT=27200 docker compose up -d
```

On Windows, put those variables in a `.env` file beside compose.yaml. The
container's internal server.example.json port remains27150; host mapping and
the launcher must use the chosen published port. Default config is mounted
read-only; no game/PAK/DLL/loader files are copied into the image. First build
downloads the pinned official Python base image; no host Python is needed.

Stop with `docker compose down` (logs volume retained). Do not add`-v` unless
you explicitly want to delete that volume. Offline transfer after an initial
build is supported with Docker's own image export/import:

```sh
docker image save -o SzeroLAN-server.tar szero-lan-server:local
docker image load -i SzeroLAN-server.tar
docker compose up -d --no-build
```

## Players: one executable per operating system

Distribute **SzeroLAN-Windows.exe** to Windows PCs and **SzeroLAN-Linux** to
Linux PCs. Each executable embeds Python, Tk, the bridge, mod helpers and loader
archive. End users do not install Python, pip or launcher packages. The game
itself is not included. Linux still needs Wine and its normal game dependencies;
the Linux executable targets x86-64, glibc2.35+ desktop systems (Ubuntu22.04+),
not musl/Alpine, macOS or ARM. A graphical desktop/XWayland is required.

Put it anywhere writable, mark the Linux file executable if needed
(`chmod +x SzeroLAN-Linux`), then open it:

1. Select the existing game installation, then Install Arena Mod. Existing loader/conflict,
   backup, receipt and exact game-build checks remain in place.
2. Enter server IP/hostname, port and player name. These remain unsaved drafts
   until Launch Game. No manual player roles/secrets.
3. Choose game launch options, then Launch. Use the game's Battle→Online flow.
   Keep the launcher open: it owns that game's background LAN bridge.
   **Disconnect LAN** stops the bridge without killing the game; close the old
   game before starting the next session. Settings unlock after disconnection.

Launch first validates/saves the game-root JSON, updates existing exact
`UserName=` lines in `SparkingZERO/Binaries/Win64/steam_emu.ini` if present,
and saves the user preferences (including selected folder). These writes finish
before server preflight or any bridge/game process creation. Failure cancels
launch; saving does not depend on the server being reachable. Files are replaced
atomically individually, not as a multi-file transaction. If a later save fails,
an earlier file may already be saved, but neither process is started.
No INI or missing key is created, and unrelated lines/BOM/line endings remain.
UTF8, BOM-marked UTF16 and CP1252 are supported; invalid/unrepresentable content
fails closed. First modification keeps sibling `steam_emu.ini.szero-name.bak`;
subsequent launches never overwrite this recovery copy. Rename/copy it back to
`steam_emu.ini` with the game closed to restore the original. Only this username
field is touched, not account/ownership/authentication settings.
Typing, folder selection, mod install/uninstall and window close do not persist
the UI draft. Installation can still create its normal default JSON if missing.
No new native DLL/game patch or server restart is needed for this launcher update.

Last selected game folder is restored from:

- Windows: `%APPDATA%\SzeroLAN\launcher.json`
- Linux: `$XDG_CONFIG_HOME/SzeroLAN/launcher.json` or
  `~/.config/SzeroLAN/launcher.json`

Connection and game preferences are saved in the selected game-root
`SzeroLAN.json`. Unknown JSON keys are preserved; invalid/incomplete edits do
not overwrite the last valid settings. Older tools-folder setup.json is read
for migration. Settings are external writable JSON, not embedded into the executable
or written to its temporary extraction directory. Settings are locked during an
active bridge; each fresh launch gets a new runtime UUID as before.

### Launch options

- Display: game default / fullscreen / windowed / borderless.
- Resolution: game default or preset720p,900p,1080p,1440p,4K.
- Linux Wine executable and optional prefix. Empty prefix inherits WINEPREFIX
  or Wine's normal `~/.wine`; no game prefix is created or replaced by setup.

These are Unreal command-line preferences, not verified performance fixes;
the game's shipping build or saved settings may override some display
options. No frame cap, battle speed, timing or synchronization settings are
changed by these launch arguments. Save actions are separate and explicit.
The command preview shows exactly the game arguments.
Arguments use subprocess arrays, never a shell command. Linux requests the
native bundled dwmapi loader and preserves unrelated Wine DLL overrides.

## Build the executables yourself

Build dependencies are needed **only on the build machine**. Windows requires
Python3.13 (Python3.12 also works using the equivalent manual build command).
The pinned packager does not collect Tk9 zipfs resources from WindowsPython3.14;
the build script refuses that combination instead of distributing a broken UI.
End users do not need any of these tools. Windows:

```bat
lan\Build-Launcher.cmd
```

Linux (Python+Tk development installation and venv required):

```sh
bash lan/build-launcher.sh
```

Both write intermediate binaries to `.build/desktop`, outside `dist`.
For future deliveries, distribute only the complete ZIP: after both platform
builds are staged there, run `python3 lan/build_release.py` to update
`dist/SzeroLAN-Arena.zip` and its checksum. Do not copy standalone launchers
into `dist` or update the existing launchers there; leave those files untouched.
Build on Windows for the.exe and Linux for Linux;
one binary cannot run natively on both. The provided GitHub Actions workflow
`.github/workflows/desktop-build.yml` builds separate Windows/Linux artifacts
when the repository is hosted on GitHub; it is not a pre-existing hosted release.

For a portable Linux baseline using Docker instead of the host's Python/glibc:

```sh
docker build -f lan/Dockerfile.launcher -t szero-lan-launcher-builder:local lan
mkdir -p .build/desktop
docker run --rm --network none --user "$(id -u):$(id -g)" \
  -v "$PWD/.build/desktop:/output" szero-lan-launcher-builder:local
```

Build-time caches/output remain under .build/desktop/build. Resources are embedded
explicitly; proprietary game files, user configs and runtime logs are excluded.
PyInstaller applications unpack to a temporary directory at runtime; the bridge
uses the same executable's private`--bridge` entry, not an external python.exe.
Frozen library-search environment is sanitized before launching Wine/the game.
Unsigned Windows executables may show a SmartScreen warning; no certificate or
signature is fabricated. Native Windows validation and signing are separate
from Wine-based build/smoke tests.

Sources used for packaging/argument behavior:
[PyInstaller runtime information](https://pyinstaller.org/en/stable/runtime-information.html),
[external-program precautions](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html),
[Unreal command-line reference](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-command-line-arguments-reference).
