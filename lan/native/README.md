# Native helpers and source-only construction core

## Current image policy: adaptive bindings, no executable SHA

All six helpers now validate the loaded PE64/AMD64 image and required RVA bounds
without opening or hashing the game executable. Existing instruction-prefix,
vtable/pointer, thread, ownership and restoration guards remain. The backend
still hashes its OWN DLL for optional helper-identity diagnostics; that is not
an EXE compatibility gate. Canonical operation identifiers remain stable; their loaded addresses now come
from instruction and decoded-reference resolution.

The shared native_image.h is covered by a compiled fixture that accepts two
executables with different disk hashes but identical native layout, and rejects
bad PE architecture/headers/ranges and changed instruction prefixes. Older
sections below are historical; former EXE SHA gating no longer applies.
Operational backend revision is ranked-bindings1. Optional tracer schema6/bindings1
reports validation:native_layout instead of a target EXE digest. Console/session
reports use the same validation label, and audit.lua no longer compares a hash.


### Game v3020 and v3022

`native_bindings.c` resolves 147 reviewed operations/globals/table addresses on
worker threads before any callbacks are published. Unique instruction patterns
retain field offsets and local control flow; only decoded image-relative
references are normalized. Data addresses follow decoded RIP references, with
independent references and class-name constraints where needed. Missing,
ambiguous, conflicting or out-of-section results refuse with `binding_error`.
Original pointer, ownership, ABI, thread and hook-restoration guards still run.
Hook signatures use interior instructions so independently loaded helpers can
resolve after another helper installs its owned hook. The owning helper checks
its prologue and relative targets before installing its own hook.

Game v3020 and v3022 are user-confirmed tested, and both executables have
reviewed mappings. Similar future relocations
can resolve without a new EXE hash or a guessed global offset. Changes to
instruction shape, object fields, ownership or protocol still require review.
Matching old/new addresses does not prove cross-version multiplayer protocol
compatibility; use matching game versions for a tournament until tested.

Build all six DLLs with the existing MinGW compiler:

```sh
python3 lan/build_native.py --output .build/native
```

This stages DLLs without changing a game installation. To refresh the launcher's
source payload, copy the six resulting DLLs into
`lan/ue4ss/SzeroLAN/scripts/`, then rebuild both standalone launchers. Ordinary
builds use the checked-in catalog and do not need original game files.
Regeneration is developer-only and requires `pefile` plus GNU `objdump`:

```sh
python3 lan/generate_native_bindings.py --old /path/to/original.exe --updated /path/to/updated.exe
```

`native_bindings_recipes.json` supplies the reviewed metadata. It contains no
complete game executable. `test_native_bindings.c` uses synthetic code/data to
verify relocation, ambiguity, field/branch changes, reference checks and PE
bounds. The optional `test_native_bindings_image.c` maps explicitly supplied
executables as non-executable DATA and can inject relocation/prologue damage;
it never calls a game instruction. Actual two-PC game acceptance remains a
separate test.


## Operational ranked-result1 and optional postresult2 logging

No native session/backend diagnostic files are written unless
SZERO_LAN_MOD_LOGGING=1. Multiplayer operations still execute with it missing/0.
The backend now owns the exact-build FKoratBattleResult setter hook for ranked
result reporting even with logging OFF. It preserves borrowed data/RAX/LastError
and reports own Win/Lose/Draw through SERVICE5, fenced to an issued round code.
Complementary authenticated peer reports update persistent LAN Elo/counters.
The optional service observer additionally requires SERVICE_TRACE=1. Its
schema5/postresult2 skips that setter in operational native-session mode to
avoid duplicate hooks, preserving its other17guards and bounded recording.
Standalone observer fixtures retain all18hooks. See DEPLOYMENT.md and
analysis/operational-ranked-result-capture-2026-10-26.md. Actual updated-game
rating acceptance is unverified; the later result-menu exit error remains open.


## profile-sync1 follow-ups

SERVICE4 carries only recovered own card-badge/proficiency value DTOs. Fields
are selected from bounded original JSON without copying auth/tickets or arbitrary
body fields. Strict backend validators check exact fields and signed-byte types.
The original caller consumes common res0 only, after committed own-state writes.
Original JSON projection, service binding, coroutine cancellation and ownership
rules are retained. These operations provide no winner authority.


## battle-end2 backend extension

Normal P1/P2 end routes use bounded SERVICE3 frames containing only the issued
code, raw numeric outcome and own typed native-rank snapshot. P2 start requires
the issued code. Original JSON projection/result application remains intact.
Snapshot selection follows original category/extra lookup; the missing-entry
case mirrors the verified original constructor. Native cache values are not
changed by the adapter. No automatic Elo or force-end support is introduced.
Schema3 logs revision battle-end2. See DEPLOYMENT.md and the retained original
end-contract analysis for ordering, lifetime and actual-game limitations.


## battle-start1 backend extension

The existing scoped backend adapter now accepts exact
`/pvp/start_battle_player1.php` and `/pvp/start_battle_player2.php` routes. It sends
only route names over SERVICE1; no native request body is read or forwarded for
these operations. Original game JSON projection and native message delivery are
preserved. Server-side current-room/role/account validation creates a shared
match_code. Schema3/revision battle-start1 logs worker UTC exchange/refusal times.
Foreign-service start calls still delegate under the prior ownership rule and
emit a bounded refusal diagnostic. No new entry detour or allocator is introduced.
The postpair3 observer and native session helper remain byte-identical.

## postpair3 recorder lifetime

Initial service/menu recording remains5minutes; the same pinned wrappers then
forward quietly until selected preparation/connection begins, waiting at most
30minutes. One post-pair activation records5minutes, capped at35minutes total and
512events. Initial deadline and pair-wait deadline are separate. An intermediate
atomic claim publishes the active deadline before the worker uses it. No ring
reset, trampoline replacement or repeated renewal occurs. Borrowed outputs and
late return tokens retain the existing ownership rules. Tests reproduce first
connection after the old recording deadline, quiet forwarding and bridge stop.
See the current DEPLOYMENT.md section; older10minute descriptions are historical.

## Current modes4 multi-peer session path

HELLO5 advertises an immutable game port and up to64 distinct local proxy ports.
SESSION4 has the existing SESSION3 token order with capacity/member bound8.
Only LAN partition5 uses the new path; older two-member protocols are isolated.
Each remote LAN principal maps to its own stable proxy port, validated against
that advertised allowlist before native publication. Native DTO arrays, owned
identity projection and user-info cache all accommodate the same bounded roster.
The server validates sender, destination and session membership for each targeted
UDP datagram. No native combat payload interpretation or bracket simulation is
introduced. See DEPLOYMENT.md for deployment and actual-game limits.

The optional tracer now has17 verified entry wrappers and revision postpair2.
The first post-pair preparation/connection entry extends capture once by five
minutes, capped at ten minutes total and512events. It reads typed status only;
tag2 pointer payloads are never read as errors. The deeper observer preserves
working cards and all native results.

## Scoped backend_adapter.dll (2026-10-25)

Backend3 corrects completion handoff: after worker DONE and synchronous native
projection/cleanup, the hook releases DONE→IDLE before returning. Immediate
native continuations no longer depend on another worker poll. Worker cancelled-
job cleanup uses compare-exchange, never an unconditional IDLE store that could
overwrite a newly queued job. Cancellation still cannot reuse in-flight buffers.
The compiled fixture pauses the worker after publishing DONE: old code fails
the immediate-IDLE assertion, corrected code passes and accepts the next call.
The real bridge/server fixture now submits all five supported routes without
wait_idle calls or artificial delays between operations.

Separate from the byte-identical working session DLL. `145a9c800` is intercepted
only for the bound title backend and five exact route names; unrelated services
forward unchanged. Known game-thread calls yield via the original task scheduler.
Only the worker validates the loaded image, installs/restores its owned entry hook and
performs loopback I/O. Native image bounds, entry prefixes and the
borrowed-stream vtable slots are checked before publication. Unknown builds
refuse; DLL/trampolines remain process-pinned for suspended native fibers.

`backend_response.c` constructs an original64B raw HTTP value using the native
40B borrowed-view factory, original JSON projector and original owner/map
destructors. Tagged output is72B. Empty header-map pointers are self-relative:
never memcpy an initialized header map. Response storage stays immutable until
projection returns; cancellation cannot reuse a worker-owned buffer. Original
native parsing errors are preserved, not rewritten as success. URL small-string
limits are30 bytes without explicit allocator and22 with flag2; heap+24 capacity
and all ranges are bounded. Request bodies/tickets are never copied or sent.

The instance-scoped `.service.endpoint` is a decimal loopback port. IPC requests
are `SERVICE1 <launch-instance> /exact/route.php` plus newline. Reply is decimal
byte count plus newline and exactly that many UTF-8 JSON bytes, at most65536;
`ERR` refuses. Socket work has an absolute8s deadline and cancellation polling.
The Python bridge uses its existing live TCP peer; server accepts only empty
route bodies, isolates login records and clears them on disconnect. No official
endpoint, account ID or Steam authentication blob is forwarded.

Build from workspace root with the existing MinGW toolchain:

```sh
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -shared -static-libgcc -Wl,--no-insert-timestamp lan/native/backend_adapter.c lan/native/native_bindings.c lan/native/backend_response.c lan/native/vendor/minhook/src/buffer.c lan/native/vendor/minhook/src/hook.c lan/native/vendor/minhook/src/trampoline.c lan/native/vendor/minhook/src/hde/hde64.c -o lan/ue4ss/SzeroLAN/scripts/backend_adapter.dll -lbcrypt -lws2_32
```

`test_backend_response.c` checks layout, ownership, self-relative headers,
failure atomicity and canaries. `test_backend_adapter.c` uses real temporary
MinHook wrappers/Wine sockets with synthetic scheduler/allocator/projector;
`test_backend_bridge.py` adds actual GameBridge/TCP service traversal. They do
not execute the actual game's JSON parser or prove Ranked/card gameplay.
The hook has a1296B frame; the hashing worker has a131536B frame, not a512B
whole-helper stack bound. Portable ASan/UBSan was run with leak detection off.
See ../DEPLOYMENT.md for supported routes and remaining card/rank limitations.

## Optional service_trace.dll

See ../DEPLOYMENT.md for opt-in setup and limits. This separate exact-build
observer does not change native_search.dll. It statically links unmodified
MinHook v1.3.4 (vendor/minhook/UPSTREAM.md + LICENSE.txt) for ten temporary
in-memory entry wrappers. It always calls the original with the same Win64
scalar arguments, preserves the original RAX and LastError, and only reads
borrowed output status. Main-thread recording is bounded; validation/file I/O and
hook enable/disable are worker-only. Never remove hooks/uninitialize/free
trampolines: original native fibers may still be suspended inside them.

Schema3 adds inner login_provider (1458f19f0, four scalar arguments),
backend_login (145ad9b00, eight) and login_response (145ad0d20, three).
The provider has a tagged blob-or-error result: tag1 has an error at+8;
tag2 is an owned payload and is NEVER read as an error/status. code_valid=false
means the logged zero is a placeholder, not success. No payload is logged.
The fixture distinguishes identical outer errors originating before backend
submission versus in the backend response path. This is still diagnostics,
not a LAN service implementation or a Ranked fix.

Schema4 adds the Steam HTTP exchange14591cb70/seven arguments and two
shared helpers145851440/four and145811d40/two. The shared helpers record ONLY
11 exact original HTTP call-return sites (checked as original E8 instructions
before installation); every other caller immediately forwards with no recording.
failure_origin is a fixed branch label, never a return address or string.
The string helper records NO output status/payload. Async-holder errors need
not be remote HTTP errors; task abort/cancellation is not proof of user cancel.
Backend entry also snapshots its existing numeric status+468, with explicit
backend_status_valid. It never changes that status or the HTTP inputs/outputs.

Build with an existing x86-64 MinGW compiler, from the workspace root:

```sh
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -shared -static-libgcc -Wl,--no-insert-timestamp lan/native/service_trace.c lan/native/native_bindings.c lan/native/vendor/minhook/src/buffer.c lan/native/vendor/minhook/src/hook.c lan/native/vendor/minhook/src/trampoline.c lan/native/vendor/minhook/src/hde/hde64.c -o lan/ue4ss/SzeroLAN/scripts/service_trace.dll -lbcrypt
```

test_service_trace.c uses synthetic exported functions, test-only shortened
capture, real MinHook/Wine calls, distinct arguments/RAX and output canaries,
unrelated exception handling, non-recorded other-thread calls, event cap,
bridge-endpoint shutdown and a suspended Windows fiber resumed after disabling.
The actual production DLL is separately tested refusing the unknown fixture
EXE before any hook. These are not actual game or native-Windows acceptance.

## Current linked session-v3 adapter (experimental, not gameplay-verified)

Rooms1 adds exact `146d15df0`/kind1 capture with an allocator-less64-byte
header, inline bytes at+40 (not+48). Existing size/cursor/ownership/unknown-type
guards remain. Capture layout diagnostic5 identifies it. The compiled IPC
`create-inline64` regression exercises this through the real bridge/server and
synthetic native cache; this is not proof of native lobby/ranked gameplay.
The user separately reports fix8 Quickmatch worked. See `../MODES.md`.

Fix8 admits exactly native join flags0 and0x28. Real fix7 runtime attempted
0x28 and was refused by our blanket nonzero guard before IPC;1043 was our error,
not a platform/server rejection. Bounded original-byte audit confirms LOCAL
14592db10 only tests bit7 (empty transport address), whereas Steam1459269b0
does not read incoming R9 flags. Neitherbit3 norbit5 maps to a member flag or
server admission override. Other values still refuse; no arbitrary masking.
Compiled `quickmatch-lan` now passes0x28 and asserts native code0 after actual
worker/server join; classic0 and unsupported-value canaries remain covered.
This remains synthetic native ownership, not game/combat verification.

Fix7 adds `native_lan_identity.{h,c}` and the HELLO4 binding. Production session
mode requires a server-connection-bound `szlan:` principal, pinned with both
loopback ports for the process lifetime. Complete greeting validation precedes
publication. Logical directory frames stay in the LAN namespace; each decoded
owned DTO projects exactly the own member to the real native local pair before
materialization/localization/inspection/cache/diff. Search requires zero own
members, membership operations exactly one. No global user or Steam identity
is written, and no native self-match filter is removed. Classic HELLO3 remains
only for backwards diagnostic fixtures, not a launcher option.

The bounded original audit traces address-based channel bootstrap and UUID-based
member/channel/roster references (messages34/37/39). Optional post-join cache
lookup refreshes platform friend data without supplying LAN IDs to Steam calls;
this is not proof of complete offline startup or every optional profile UI.
The compiled `quickmatch-lan` fixture exercises the production dispatcher with
identical underlying primary/persona values on two clients, complete synthetic
native descriptor copies and one server session. Its callbacks are still not
the real game, and playable combat remains unverified.

Fix6 adds read-only `native_session_inspect.{h,c}` diagnostics on the ACTUAL
deep-owned returned descriptor, not merely its decoded source. It compares ID,
compatibility, numeric count/values, primary owner, capacity and member-count
byte with the source DTO (`native_copy_mask` bits1/2/4/8/16/32/64 respectively).
Numeric/OR compatibility and primary-owner self-exclusion are independently
predicted against bounded native reads; they do not call native functions or
modify candidate admission. Unknown=-1; require `native_inspection_read:1`.
Query+4d identity removal compares primary identities only; the native wrapper
skips the check when local primary is empty. Separate Steam accounts were
confirmed by the user, but their actual native identities have not been logged.
Sticky join-attempt/flags/plain-result scalars expose refusal before accepted
`join_calls` increments. Nonzero flags still refuse: no unproven translation.
These fields survive immediate create; they are NOT event-level title tracing.
Fix6 is diagnostic, not a completed match. Source-only controlled numerical
replay lives in `analysis/scripts/native_numeric_oracle.{py,c}`: exact original
pure predicate bytes agree with server matching in10,000 synthetic cases, no
game initialization/platform calls. This is stronger than mocked callbacks,
but still not actual gameplay or an actual runtime identity comparison.

Fix5 preserves sticky finite search request/result/count scalars across immediate
create/join, plus a bounded native context-vector count snapshot and service-kind
identifier. It never dumps identities, raw pointers or opaque stream contents.
The report is bounded to2048 bytes (also at maximum tested scalar widths), and
truncated JSON is never written. Buffers are static on the guarded polling thread.

Search/MATCH3 default compatibility normalization is derived from the owned
service's original+40 target: exact1411072d0=false (Steam/standard LOCAL),
1410fdcc0=true (fallback LOCAL). No arbitrary native callback is invoked;
unexpected targets fail capture. Explicit query+4e still overrides the default.
The original outer wrapper rechecks candidates with this same default.
This is a concrete correction, not proof of the supplied stall's runtime cause.

The compiled `quickmatch` IPC fixture runs a finite search then creates or joins
according to its returned owned vector, checks sticky evidence survives that
follow-up, and frees its own synthetic ID storage. Its Python test holds both
bridges connected and proves one shared two-member server session. The native
factory/descriptor clone/title decision remain synthetic; no battle is tested.

Fix3 additionally admits the exact runtime-observed146d15840 family: header48B,
read/write cursors+10/+18, length+20,capacity+28, embedded bytes at+30. Recovered
constructor145839350 and getter1424ae2f0 prove the layout. No unknown vtables
are admitted. Fixture create-embedded exercises this through C/RPC/server/codec
and synthetic native cache; actual game factory/battle remain unverified.

Earlier fix2 admitted two exact source layouts:147b43f10/kind1 inline header72B and
147b43960 vector header64B (data+20,count+28,capacity+30,allocator+38). Both
retain cursor+10/+18. Unknown layouts remain refused; no native getters or
destructors are invoked by capture. Reconstruction uses the existing known
borrowed inline source, preserving bytes/cursors through native deep-copy.
Scalar stream diagnostics identify the exact refusal boundary and bounded
static module vtable RVA, not absolute addresses. No gameplay result is claimed.

`native_search.c` compiled with `SZERO_SESSION_V3` now links the native
constructor/host/codec/search/transport components. The provider, lifecycle
and transport `.inc` files are implementation parts of that DLL, not standalone
mods. The normal launcher always supplies `SZERO_LAN_NATIVE_SESSION3=1`;
there is no mode checkbox or old-overlay fallback. Low-level legacy diagnostic
code remains separate and is not a supported normal launch path.
Do not describe synthetic callback tests as execution of the real game ABI.

Reproducible Win64 build from the workspace root:

```sh
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -DSZERO_SESSION_V3 -shared -static-libgcc -Wl,--no-insert-timestamp lan/native/native_search.c lan/native/native_bindings.c lan/native/native_session_host.c lan/native/native_session_adapter.c lan/native/native_session_codec.c lan/native/native_session_search.c lan/native/native_session_inspect.c lan/native/native_lan_identity.c lan/native/native_lan_userinfo.c lan/native/session_materializer.c lan/native/native_session_wire.c lan/native/native_lan_transport.c -o lan/ue4ss/SzeroLAN/scripts/native_search.dll -lbcrypt -lws2_32
```

For the actual compiled IPC worker fixture, replace `native_search.c` with
`test_native_session_ipc.c`, omit `native_bindings.c`, remove
`-DSZERO_SESSION_V3 -shared`, add `-DSZERO_BINDINGS_TEST_IDENTITY` for all
fixture translation units, and output to
`/tmp/szero-session-v3-ipc.exe` (the fixture defines its own test macros).
Set `SZERO_SESSION_V3_IPC_EXE` to that path for discovery tests, and select a
disposable `/tmp/szero-*` Wine prefix. The separate synthetic publication
fixture uses `native_search.c` plus both `-DSZERO_SESSION_V3` and
`-DSZERO_NATIVE_SEARCH_TEST` without `-shared`; it never opens the game.

Ownership is staged: construct/localize an independent native handle before
server ACK, cache-consume only after the matching COMMITTED reply, and release
on cancellation. Search returns a true finite zero/one owned descriptor vector,
not an empty success for a pending search. Unknown pair layout or failed abort
readiness quarantines ownership and stops subsequent native allocations.
Refresh uses owned native clones and the original in-place diff. All new LAN
native operations require verified image/selected-owned service/native-thread
guards. Original base task-queue ticking is preserved alongside bounded polling.

Fix1 leaves all borrowed settings inputs untouched. Original outer create
wrapper1458c84a0 destroys its settings after virtual+88 returns, including on
error; our value-copying provider must not invoke that native destructor too.
The old LOCAL provider moves ownership into its registry, which this adapter
does not. Settings capture has small individual Win64-O2 frames (<=512B),
formerly8592bytes in one function;
this removes avoidable fiber-stack pressure, not proof of the reported crash.
Reports distinguish capture refusal causes; no raw identity/pointers are logged.

The transport gate admits normalized mode2 only while the recovered channel
is idle, changes only the platform-transport override byte and never reinitializes
an active context. Bind and remote destinations use this process's distinct
game/proxy loopback ports; the bridge preserves both across reconnects. No
authentication or ownership check is replaced. Real game callback compatibility,
global shared-context safety and channel/combat progression remain unverified.

## Historical source-only components (superseded by linked adapter above)

The new files `native_session_wire`, `native_session_codec`,
`native_session_adapter`, `native_session_host`, and `native_lan_transport`
do not change the current DLL's search-only behavior. The host binding fills
guarded native callbacks, but no installed dispatcher invokes them. Do not
enable a partial provider or infer playable matches from these files.

Profile2 preserves a bounded known-layout stream and both cursors through
`szero_materialize_session_stream`; profile1 stays empty-stream only. Both
reject nonempty type-erased properties. The Windows host requires actual image,
thread/context/service/owned-vptr gates and validates the new factory pair
before localization/cache/release. SESSION3 data is bounded and pointer-free;
parsed views refer to their owning codec object, which must not be moved.

Create success is an OWNED native ID string, not the descriptor/control pair;
join is a plain40-byte error. Refresh uses original ownership-aware in-place
diff, not replacement of borrowed member nodes. Callback fixtures use stand-ins,
not actual game execution. Source transport preparation is never invoked by
the distributed search-only DLL. Remaining live-provider/RPC/cancellation and
channel work is documented in the workspace integration-status report.

## Opt-in native search/cancel provider (partial game evidence, not playable)

`native_search.c` is a separate helper, NOT the source-only materializer below.
It publishes a pinned immutable 28-slot selected-service vptr clone after exact
image and native layout checks. +90 copies bounded numeric query data into
worker IPC while the native task cooperatively yields. Native cancellation
deep-copies the real task error; borrowed queries are never freed by the hook.
+88 create returns tagged unavailable error (48 bytes); +98 join returns a
plain unavailable error (40 bytes). It does not fabricate successful results,
call the materializer, initialize UDP or touch authentication/readiness checks.

Enable only on a fresh launch with `native_search: true`; see ../README.md.
Selected services are shared: publication is service-instance-wide, not a
per-context redirect or proof of global quiescence. All other virtual methods
are forwarded unchanged. No hot unload/reinitialization is supported.

```sh
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -shared -static-libgcc -Wl,--no-insert-timestamp lan/native/native_search.c lan/native/native_bindings.c -o lan/ue4ss/SzeroLAN/scripts/native_search.dll -lbcrypt -lws2_32
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -DSZERO_NATIVE_SEARCH_TEST lan/native/native_search.c -o /tmp/szero-native-search-test.exe -lbcrypt -lws2_32
```

The conditional fixture uses synthetic owned service/context memory and task
callbacks only. It does not execute the game or verify the game's scheduler.

Revision `native-search-v2` additionally copies all32 bytes of each compound
OR-pair. BEGIN2 encodes both numeric predicates with unsigned64 keys and
signed32 comparison/value fields; allocator pointers never cross IPC. Counts
are bounded16 and checked against capacity. The server stores constraints
unchanged but does not yet evaluate them or return native results.

The compiled IPC regression includes the actual production `process_job`
lifecycle, not just synthetic command strings. It exposed the old Wine
whitespace/EOF endpoint-parser bug, now replaced with bounded ASCII parsing.
It exercises LF/CRLF, ordinary/compound predicates, pending/cancel, disconnect,
bad endpoint rejection and worker ownership until hook completion. Run with a
DISPOSABLE test Wine prefix and loopback access, never the user's game prefix:

```sh
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror lan/native/test_native_search_ipc.c -o /tmp/szero-native-ipc-fixture.exe -lbcrypt -lws2_32
# From lan/, after creating/initializing a disposable Wine prefix:
WINEPREFIX=/tmp/YOUR_TEST_PREFIX WINEDEBUG=-all SZERO_NATIVE_IPC_EXE=/tmp/szero-native-ipc-fixture.exe python -m unittest test_native_search_compiled -v
```

This fixture bypasses no production image-layout check: it compiles the same unexported
request-lifecycle function into its own test executable. No game/native task
function is invoked. The game log supplied before v2 proves hook publication
and one interception, not the new worker's success in an actual game run.

## Session materializer (not installed or wired into the game)

`session_materializer.c` / `.h` implement the bounded client-side translation
from pointer-free session values to a borrowed exact-build native descriptor.
The component invokes an injected owned-copy factory matching original
`145943940`. That native factory creates independent game-owned strings,
numeric values, member nodes and the reference-counted descriptor handle.
Temporary source storage is released with its own allocator after synchronous
copying; it is never passed to native destructors. Output native results remain
owned by the caller, including error results. Never CRT-free native outputs.

Profile1 supports explicitly empty properties and stream ONLY. It preserves
compatibility, positional signed numeric values, capacity, ordered member IDs,
identity strings, transport addresses, optional byte values and raw flags.
Owner identity is derived from the single owner member. It rejects unsupported
data instead of treating missing reconstruction as empty settings. This is a
partial construction profile, not evidence that real Quickmatch uses empty
stream/properties. Identity strings are not reclassified as authentication data.

There is deliberately no DLL export, hardcoded-address call, loader entry or
installed hook for this source. A future host still must verify the exact EXE
layout, calling thread/context lifetime and function identity, decode server data,
manage native results, install the provider and deliver membership updates.
Native member wrappers borrow node pointers: do not replace/free their nodes
without the original update lifecycle. No account/ownership checks are changed.

Standalone synthetic constructor fixture (no game/native factory execution):

```sh
gcc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -g lan/native/session_materializer.c lan/native/native_session_wire.c lan/native/test_session_materializer.c -o /tmp/szero-session-materializer-test
ASAN_OPTIONS=detect_leaks=0 /tmp/szero-session-materializer-test
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -c lan/native/session_materializer.c -o /tmp/szero-session-materializer-win64.o
```

ASan/UBSan fixture and Win64 object compilation pass. LeakSanitizer cannot
operate under this sandbox's tracer; leak checking was disabled for that run.
These results establish source layout/bounds contracts, not game integration.

## Optional native session-state capture

`session_probe.c` builds the third bundled diagnostic helper:

```sh
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -shared -static-libgcc -Wl,--no-insert-timestamp -o lan/ue4ss/SzeroLAN/scripts/session_probe.dll lan/native/session_probe.c lan/native/native_bindings.c -lbcrypt
```

It is explicitly enabled by `Start-Native-Trace.cmd` through
`SZERO_LAN_NATIVE_TRACE=1`, not loaded on normal launches. `session_trace.lua`
is called once per game-thread poll, including while unpaired. The helper
validates the loaded native image asynchronously before bounded own-process
ReadProcessMemory calls. Getter `1459d3680` reads native context global
`148cf84f8` (RVA8cf84f8); title constructor `145a52fd0` installs vtable
`147ba1bf8` (RVA7ba1bf8). Both identities are checked; no getter is invoked.

Whitelisted fields: session pointer `+40` as presence only; raw `+63c`, `+65c`,
bytes `+661/+662/+663/+665/+667` and task byte `+19d6`. No pointed-to session
data or raw addresses are serialized. Full snapshots use 13 bounded reads,
including context-pointer/vtable checks before and after; they are not atomic.
Unreadable/changed/wrong-class data produces an unavailable reason, not zeros.
No native engine/platform calls, hooks, network or game-memory writes occur.

Output: `session_trace_<instance>.jsonl` beside the DLL. It records only changes,
UTC and monotonic time, PID, exact image identity and whitelisted scalar values.
At most 300 polls/300 seconds after verification, max256 records. This is not
a native LAN backend or readiness check. Fixture compilation with
`-DSZERO_SESSION_TEST` exercises only owned synthetic memory and layout rejection;
test-only writes are excluded from the distributed DLL.

## Console registry helper

`console_probe.c` builds the bundled `scripts/console_probe.dll` with MinGW-w64:

```sh
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -shared -static-libgcc -Wl,--no-insert-timestamp -o lan/ue4ss/SzeroLAN/scripts/console_probe.dll lan/native/console_probe.c lan/native/native_bindings.c -lbcrypt
```

No third-party mod code or original game bytes are embedded. The module exports
one Lua C function that returns no values and uses no Lua API linkage. Lua calls
it only on the game thread after a match assignment. A worker first checks the
loaded PE64 image and required address ranges. Later calls
snapshot the own-process console registry through bounded ReadProcessMemory.
There are no hooks, engine-function invocations, game-memory writes, sockets,
platform/authentication calls, or setting changes. Image-layout failure disables reads.
The worker holds its DLL reference until it finishes, including during reload.

Layout is from `analysis/console-manager-layout.txt` and
`analysis/console-manager-lookup.txt`: manager RVA 0x8739b48, vtable RVA
0x6dc03c0, sparse array entries of 32 bytes. Bounds and pre/post headers are
checked, and `r.DumpingMovie` is a positive control. A stable header is not an
atomic process snapshot. Retained/unregistered objects may exist. Registry
presence does **not** prove command acceptance or successful session creation.

Reports: `console_probe_<SZERO_LAN_INSTANCE>.json` beside the DLL; `default`
for the optional legacy launcher. They contain only whitelisted registrations,
counts, image identity and process ID, never account/session data. The full
report is printed once into UE4SS.log; a summary appears in adapter diagnostics.
Missing loadlib/DLL or mismatched layout does not block the rest of the adapter.

Native Windows fixture test (not a game test): compile this same source with
`-DSZERO_PROBE_TEST`, without `-shared`, as a temporary EXE and run with Wine or
Windows. It tests owned synthetic memory, registration matching, invalid read
and corrupt-bounds rejection; it does not establish live game compatibility.

## Separate experimental native UI helper

`menu_bridge.c` is intentionally separate: unlike the console audit, it **calls
a native UI method** to bind only newly constructed LAN-owned native buttons.
It is enabled only by game-root JSON `native_menu: true` through setup_launcher.
It never calls matchmaking/authentication, changes original menus or travels.

```sh
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -shared -static-libgcc -Wl,--no-insert-timestamp -o lan/ue4ss/SzeroLAN/scripts/menu_bridge.dll lan/native/menu_bridge.c lan/native/native_bindings.c -lbcrypt
```

The Lua module writes a bounded per-process request containing current fresh
root/tree/button addresses and calls the helper in the same game-thread
callback while those objects are live. Validation requires supported EXE file
image, current PID, increasing serial, same calling thread, exact native class
globals/vtables, non-destroyed flags, tree ownership and distinct buttons.
Only then may it call the verified two-argument binding method at RVA 0x2b380c0;
the method's prologue is also checked. Bare native UI lifecycle/navigation
remain unverified and may crash in a real game. This is NOT the original
main-menu scene stack or a session bootstrap. Restart after updates; do not
hot-reload during a game.

Reports `menu_bridge_<instance>.json` and requests with suffix `.request` live
beside the helper and are generated runtime data. A fixture EXE compiled with
`-DSZERO_MENU_TEST` replaces the native binding call with a counter; it cannot
establish that real native widget lifecycles are safe or functional.
