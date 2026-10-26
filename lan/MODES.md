# Modes and save editing — rooms2 / Arena2

Latest Ranked update: typed native result reports now drive persistent LAN
Elo (1000initial/K32), counters and streaks after both players agree. The server
adds configurable±100Elo matching, expanding100every15seconds to±600, then any
Elo after120seconds, preserving native settings. Native Single/DP win-rate views
use confirmed lifetime totals, with no seasonal reset. Logging may remain OFF.
Rebuild server and reinstall OUR mod on BOTH closed clients from the full ZIP.
The remaining result-menu peer-exit network error is not fixed; committed results
remain saved. See DEPLOYMENT.md for exact policy, files and limitations.


Latest launcher update: Enable mod logging replaces Record online checks and
is OFF by default. Login selected on Launch verifies credentials/session FIRST
and stops immediately on failure. Uninstall deletes our mod payloads without
new backup copies. The optional postresult1 observer captures the game's named
Win/Lose enum for the next paired Ranked test. Automatic Elo/win-rate ingestion
is still disabled pending that actual game capture. See DEPLOYMENT.md.


Latest profile-sync1 update: paired captures confirm both normal finishes
succeeded. Recovered card-badge and proficiency follow-ups now save own-account
state in MariaDB and refresh login/cards. Rebuild server and reinstall OUR mod
from the new full ZIP on BOTH PCs. Display controls are removed, and account tabs
have equal size. Automatic Elo/native win-rate updates remain disabled pending
verified winner mapping; a selected player-card badge is not a match rating.
See DEPLOYMENT.md for evidence, upgrade steps and limitations.


Latest battle-end2 update: the user confirms Ranked combat works. Normal
post-match P1/P2 reporting is now implemented, with immediate per-player ACKs,
idempotent receipts and fresh codes for subsequent rounds. Existing native rank
values are preserved; automatic Elo/stat updates and force-end remain unsupported.
Rebuild the server and reinstall OUR mod from the new full ZIP on BOTH PCs.
Actual in-game acceptance of match completion/rematch is still unverified.
See DEPLOYMENT.md for the contract and exact installed-file change.


Latest battle-start1 update: native ranked preparation/connection now returns
success in the supplied traces. Separate player1/player2 backend start routes
were absent; the updated LAN backend issues a shared room-owned match_code and
keeps the game's original native command21 exchange. Both clients must log in,
and server plus client mod must update. This adds the recovered start handshake;
actual complete battles, rematches and native results/Elo ingestion remain
unverified or unsupported. See current DEPLOYMENT.md; older notes are historical.


Current modes4 update: user confirms player cards work. Tournament capture
requested8participants and was refused by the old two-member adapter. The new
bounded eight-member native DTO/materializer/user-info path and targeted UDP
relay remove that known refusal. Actual game tournament/bracket acceptance
remains unverified. All clients and server must update together.

Ranked is still unresolved after matching: native preparation succeeds and game
packets flow both ways. The new postpair2 diagnostic extends after pairing and
observes inner peer/future/commit/start branches. It is not a forced-success fix.
See the current section in DEPLOYMENT.md. Earlier notes below are historical.


Current accounts/cards update (2026-10-25): Quick play is casual-only; Account
login enables native Ranked entry. Website profiles and separate LAN Elo tables
persist in MariaDB in the single server container. Native result ingestion is
not implemented, so no automatic win/rating updates are claimed. Card target
mapping and the native `player_rank` presence contract are implemented; actual
in-game rendering still needs verification. Fresh clean LAN completion is100%:
the prior0% login value caused Ranked rooms requiring80% to reject both clients.
Native completion filters remain unchanged. See ACCOUNTS.md and DEPLOYMENT.md.
The older revision notes below are historical.

2026-10-25 backend update: five verified login/maintenance routes now use the
configured LAN server through a separate native response adapter. This addresses
the observed zero Steam HTTP request-handle boundary without changing the working
native-session DLL. Ranked UI uses its own original default-record creation when
the new LAN profile has no rank records; actual in-game acceptance remains
unverified. Player-card target mapping, ranked results/ratings and unrecognized
backend routes are NOT implemented. See the latest DEPLOYMENT.md section.

Modes3 adds exact40-byte borrowed-view settings capture for the observed
private-slot create refusal. This fixes a known capture boundary, not yet a
proven in-game private-slot flow. Ranked57C80000 remains unresolved; the generic
code has multiple original sources and no ranked LAN request is identified in
the available server logs. See DEPLOYMENT.md.

The rooms2 scoped LAN user-info adapter now admits exact0x200 only when its
validated service view is ready. It leaves real platform IDs/authentication
unchanged. The user confirms lobby mode works (2026-10-25). No larger lobby, multi-result browser
or ranked-result implementation is claimed.

The launcher now includes confirmed, backed-up DataVersion12 save unlocks for
verified base-game characters, character items and music. Other categories and
DLC are excluded. Copy-only codec/schema/atomic-write tests pass; acceptance of
an edited save is user-confirmed on Linux. The Windows timestamp check is fixed
and copy-write tested under its Windows runtime; Windows game-load confirmation
remains separate. See DEPLOYMENT.md.

Quickmatch worked in the user's fix8 test. Rooms1 preserves that path and adds
the exact previously refused `146d15df0` settings-stream layout. No original
game EXE/PAK, platform identity, authentication, DLC ownership or save is patched.

| Flow | Current evidence / limits |
| --- | --- |
| Quickmatch | User-confirmed fix8 success; compiled two-client regression retained. |
| Public two-participant rooms | User confirms lobby mode works with rooms2. No larger roster claim. |
| Private rooms | Server excludes exact `create_flags & 5` from discovery and allows known-ID joins. Native room-code parsing/invite mapping remains unverified. |
| Quick-search versus room browser | Existing bridge returns one result. Full multi-result room browsing remains unimplemented. |
| Larger lobbies / spectators | Not supported: member codec, native materializer and UDP peer routing are two-participant. Increasing capacity alone is unsafe. |
| Ranked | No completed native ranked-flow validation, LAN ratings or official result/rank submission. Mode-field meanings must not be guessed. |
| Save unlocks | Confirmed launcher actions for verified character/item/music entries; actual game-load validation pending. Originals excluded from distributions. |

The new stream is not inherently a lobby-only type. Its layout is established
from original constructors/getters, not inferred from a previous UI action.
Capture preserves payload/cursors and uses the existing native deep-copy path.
Unknown types and unsupported join flags still refuse.

The original compatibility constructor mixes a bounded input with a build
component. Widget modes and public reconstructed enum names do not prove the
meaning of that input or of opaque numeric search fields. Existing filtering
is preserved. Tests use explicitly opaque values rather than labeling them
ranked/casual without evidence.

## Save unlock safety

The supplied MainGameSaveData/SystemSaveData are transformed files, not plain
GVAS. The PAK key does not establish their encoding. Apparent native debug
methods SaveDataOpenAll/SaveDataOpenShop are no-ops in this shipping build.
Native save structs distinguish earned-content `bGamePlayUnLock` from
`bDLCUnLock`; those are not disk offsets. No blanket byte/flag patch is used.

Decode/encode integrity, DataVersion12 tag/container handling and atomic write
safeguards are now implemented. Copy-only game acceptance is the remaining
validation step. Confirmation, stopped-game checks, exclusive lock, verified
backup, fingerprint recheck and atomic replacement are mandatory. Unknown
fields, story progress, account data, rank and DLC ownership remain intact.

Research and exact next targets are retained in
`analysis/native-lobby-mode-research-2026-10-24.md` and
`analysis/save-format-research-2026-10-24.md` in the workspace/source repository.
