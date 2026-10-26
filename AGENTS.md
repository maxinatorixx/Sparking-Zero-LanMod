# Sparking ZERO LAN Multiplayer Replacement

## Objective

PUBLICATION (2026-10-26): user explicitly authorizes committing/pushing to
github.com/maxinatorixx/Sparking-Zero-LanMod and publishing full ZIP releases;
this supersedes previous no-stage/commit/push work-session notes. Preserve
existing remote initial main commit6f51e228e34402198e90fbaa79d521cc2e68426e.
Root README.md is current user/install/status/build/legal documentation;
lan/README.md is current code architecture map (old timeline preserved locally
in ignored analysis/historical-lan-readme-before-publication-2026-10-26.md).
User screenshots moved to docs/screenshots/{launcher,website}.png and embedded.
Public Git excludes game files, saves, runtime/secrets/logs, generated dist and
raw analysis; excludes retired stutter module/tests/vendor payload. Explicit
native backend/tracer DLL exceptions added; licensed pinned UE4SS retained.
Deploy private key is OUTSIDE repo in ~/.ssh; NEVER stage/copy it. .env.example
only. Do not force-push remote history. Taggedv* CI builds both fullsource
launchers, checks frozen GUI/resources, packages completeZIPs and uses scoped
job GITHUB_TOKEN(contentswrite) to publish prerelease. No personal API token
needed if repository Actions enabled. Existing standalone dist files preserved;
only fullZIP/checksums refreshed locally for README/screenshots inclusion.
Source public packaging now includes rootREADME+screenshots; all explicit
bundle dependencies must be tracked. Current docs keep result-exit UNFIXED and
actual-game rating acceptance unverified. No game/network logic changed during
publication work. Earlier 375test result includes local retiredstutter tests
that are not part of public clone; do not claim publicCI ran that fullsuite.

LATEST ranked-result1 / expanding Elo (2026-10-26): supersedes earlier notes
that automatic Elo/win-rate are disabled. Supplied a9b6 capture proves own typed
Lose2 at19:28:26.134UTC before endP2 response26.837; user confirms matsiWIN,
maxinatorLOSE. Operational backend owns exact-build SetBattleResult hook even
LOGGING0, captures enum1/2/3 only for current issued round, seals valid result
on end, new code resets. SERVICE5 adds rawcategory+typedresult separate from
completionoutcome. Optional postresult2 observer skips only result slot17 when
operational backend enabled; other17hooks unchanged. backend DLL54e3cdf1ddcda715a8585a34e5e184557ea8ddd466033dd4d8ea445f5e5c53c6;
tracer DLLd9173fa5ddb621230c4d55ccf9ded671804f05856966828b93f14cf03e9689c5.
Session DLL/Lua unchanged from preceding release. Each authenticated own report
persists before immediateACK; complementary Win/Lose or Draw/Draw samecategory
commits once transactionally. Durable ranked_reports inbox and event-id fence,
1000/K32 separateSingle/DP/Team, no self-play/unknown/conflicting awards. Native
normal-end outcome1/2 NEVERwinner. Streak columns migrate existing databases.
Native Single/DP sessionkind2/3 statistics show confirmed lifetime counts in
both native period1/2 views (explicit no-season policy); no fake fighter/title
progression or Team->kind0 mapping. Cards/login load current DB stats.

New elo_matchmaking.py adds default±100,+100/15s,cap±600,anyratingafter120s,
longestwait then nearestElo; settings server.example.json elo_matchmaking.
Original145923850 namespaces*1000+sessionkind;1459eac70 kinds2/3=RankMatch,
1459ea4a0 Single1->2,DP2->3,Team3->0. Apply only provenRankedSingle/DP AFTER
native eligibility BEFORElimit; casual/lobby/tournament unchanged. Account
ratings freshlyloaded with5s cache/invalidation, retryage retained, abort/mode/
leave/disconnect cancels. Directory sharedpolicy survives transaction previews.
Source/report: analysis/operational-ranked-result-capture-2026-10-26.md,
server-ranked-consensus-2026-10-26.md,
runtime-a9b6-ranking-and-result-exit-2026-10-26.md.

RESULT-MENU EXIT REMAINS UNFIXED: creatorleave deletesroom, remainingPOLL3EMPTY
removes native cache with actualSessionLeft57C3A7BB. Keeping descriptor until
bothleave alone not proven: removingcreator leaves noowner, ghosthost cannot
answer, promotion/rematch handshake unknown. No forced success/state/retention
patch. Actual updated-game ratings/finish flow unverified. Confirmed result
commit independent of later error; receipts survive firstleave600s. Readonly
Docker snapshot/tmp/szero-a9b6-server-readonly.log. Original bounded read-only
result controller/rematch traces retained, no livegame/server/DB/prefix writes.
Install delta ONLY Win64/Mods/SzeroLAN/scripts/{backend_adapter,service_trace}.dll
or detected Win64/ue4ss/Mods variant; close BOTH games/reinstallOURmod+BOTH
newlaunchers; rebuildserver preserving.env/data. FullZIPsonly, preserve ALL
dist root/desktop standalone files; stage.build/desktop. No gitstage/commit/push.
FINAL validation:375Python tests PASS NOskips321.867s, all6Lua mocks PASS.
Includes actual staged Linux/Windows-under-disposableWine GUI+embeddedbridge,
compiled typed-result LOGGING0worker->realbridge/TCP+SQLite Elo1016/984,
realTCP Elo1901vs1000 excludedinitially/accepted120s+lateleave/report exactlyonce,
nativehook ABI/thread/roundfences/restore, all8peer/56UDP andlegacy regressions,
isolated Docker MariaDB two-peer DP consensus/replay/containerrestart andnative
card50% verified. Initialfullrun373pass/2testfailures: diagnostic expected old
earlylimit(scan1vsnow2), authenticated fixture deletedendpoint beforeworker
observedit. Corrected native-eligibility counterexpectation andTESTONLY atomic
observedendpointwait. Finalclean375passabove. Freshproductionstrictbuild with
sameImageBase verifiedbyteidentical existingDLL; no prodpatch forfixturefix.
Final log/tmp/szero-ranked-final-full-clean.log; isolatedserverimage
db573bf995a27cb4904a92c4b8575b50996cd5e33a7982659513cad0da9fdf40.
FullsourcePython3.13.7/PyInstaller6.16 Windowsbuild under disposableprefix
/tmp/szero-ranked1-build/wine, LinuxnormalDocker; stagedONLY.build/desktop.
Linux61d03fbeaba7a7bbf9b68c275f6eddb48fce9b330aa80959528af16b063ec2c1;
Windowsa693b5f720ab95046adaea2deefe27beab3e20cb00fe60d9f44ed0e61f28cdf7.
Bothfrozen6Lua+3nativeDLL+MinHooklicensebytesverifiedexact. FINAL32entryArenaZIP
cd937e2c59a2b4fbcc3576c27ae045b4d232620211ccfbf42b338176d1fc387b;
200entrysourceZIP6f63a6f07c26e7d2861319ec9a6d77eae8307de1ff70f63507f6dbcfe9da2988.
Everyarchivemanifestentry/exactstagedonefiles/serverElo/sourcepayloadverified;
.env.exampleonly/no.env/noStart-Server. All4diststandalonebinaries unchanged
against/tmp/szero-ranked1-dist-before.sha256; originalShippingSHAe54e79...unchanged.
Actualgame/nativeWindows/result-exit acceptanceNOTclaimed. No newREAproject
open, no livegame/userprefix/server/container/DBwrites, no gitstage/commit/push.

LATEST logging/login/uninstall/postresult1 (2026-10-25): useraddsOFFdefaultall
ourmodlogging,replaceRecordonlinechecks,LaunchLoginFIRST/no launchonfailure,
no uninstallbackups. Implementedmod_loggingFalse schema/UI;service_tracealways
mirrorsnewflag,legacytracealoneNOenable. ExplicitSZERO_LAN_MOD_LOGGING1/0to
bridgeANDgame. CurrentpasswordauthFIRST beforeprefs/config/INI/preflight/process;
blankpasswordverifiesscopedrememberedtoken. Failedlogin stops withclearerror;
usernames/passwordsnotlogged,newplaintextpersistNOTintroduced. Allotherfields
saveONLYLaunch.38focusedUI/login/supporttestsPASS2.182s. UIprofileearlierchanges
retained(displayremoved/tabequalsizing). Uninstallpayloads/receiptdeletedDIRECT,
NOnewuninstallbackupdirs/copies;priororiginalinstalltimebackups/unrelatedmods/
sharedloadersretained,inmemoryrollbackonlyonwritefailure.27focusedtestPASS.

PythonbridgemainNO.client.logconfigure/offloggerunlessexplicitmodlogging1.
SixLua scripts localLog wrappers,NOglobalprintoverride;offmode skipsaudit/
sessiontrace/servicetrace/load/readreport butnative/backend pollingcontinues.
Native_search.c report returnsbeforeformat/openwhenoff; backendworkerNULLlog
whenoff,network/ownershipunchanged. Runtimeendpoint/policy/UIcontrolfilesstill
requiredNOTdiagnosticlogs;UE4SScoreengine loggingnotcontrolled.9Pythonlogging/
lifetimetests+6Lua mockspass.8focusednative/profile/reportgatingPASS60.771s
(includesactualcompiledprofileupdatesLOGOFFnofile, nativeJSONreport0vs1).
Native_search.dll6f716041541e004b2b48a224e961f75c48d4c47660de82ad9efae54b17ba4ef3;
backend_adapter.dllf6ef2c756d471e88acae6b245674a8620c28c84070fa6b2031bb62886d0433ea.

USERclarifiesmaxinatorWIN,matsiLOSE,maxinatorGokuSSJ4;thesearetagsNOTdynamic
winnerauthority. ActualFKoratBattleResult reflectionrecovered:BattleWinLose+0,
SetBattleResult native1423d76a0fromexec141f32200 copies0x230toSSGameInstance11c8.
Enum0None1Win2Lose3Draw4Timeup5RingOut6Win1P7Win2P. Separate142216650 usesfield1
withactualWINstring,elseLOSE. GetWinner/IsWinner discoveredearlierareIMPACT/
CLASHanimationONLY,NOTmatchresults! context17fa remainsunverifiedside/result
selectorwrittenAFTERnormalend. NoElofromendoutcome1both,noinferredwinner.

NEWOPTIONALtracerpostresult1schema5 adds18thexactprefix/SHAguardedSetBattleResult
wrapper,readsborrowedbyteBEFOREoriginalcopy,publishesONLYenum/readable/valid/
fixedlabelAFTERoriginalreturns. Sameargs/RAX/
LastError/borroweddata/thread/512ring/lifetimes/pinnedrestore;nostatewrite.
BothMOD_LOGGINGandSERVICE_TRACE1requiredBEFOREfile/hook. Focusednativefixture
53.648sPASSall8enums/invalid/unreadable/NULL/foreignthread/canaries/restore+quiet
productionDLLnofile. TracerDLL3420419c90aad27beffec5ec3bbd14f23692ad48aa1b5e1828cb66be28741778.
Reportanalysis/native-battle-result-observer-2026-10-25.md+selectedoriginal
native-reflected-battle-result/named-resultconsumertraces. NeedONEfreshshort
RankedmatchwithEnablemodloggingONBOTHclients→Next→bothnative_service_trace+
backendtraces,knownwinner/loser. Nootherpersonal/characterdetailrequired.
AutomaticElo/winrateSTILLdisableduntilactualRankedtypedresult/timingobserved.

Installeddeltafromend2: scripts/backend_adapter.dll,native_search.dll,service_trace.dll,
main.lua,native_search.lua,native_menu.lua,panel.lua,audit.lua,session_trace.lua
underWin64/Mods/SzeroLAN(orue4ss/Modsvariant). NewZIPclosegames+reinstallOURmod
BOTHclients;serverREBUILDforprofilepersistence. NativesessionDLLONLYdiagnostic
reportgatechanged,NOtransportlogic. OriginalEXE/PAK/loaders/saves/othermods
untouched. Priorbaseline345testPASS302.188s(beforelatestusersteering);FINAL
validationFINAL350Python testsPASS NOskips316.995s inclrealstagedLinux/
Windows-under-disposableWineGUI/resources/embeddedbridge,newlogging0/1native
fixtures,postresult1observerfixtures,DBgameTCPprofilepersistence/restarts,
allprior8peer/session/UDP/save/launcher/ownershipregressions.All6Lua mocksPASS.
BothFULLsourceonefilesrebuiltSTAGEDONLY.build/desktop;all6frozenLua+3nativeDLL+
MinHooklicensebyteidentitiesverified. Linux5d30d69446bbc7e6bbbc2180a55b9498fe3fd350c412bdade73b158d5292b933;
Windows6e4eae2493468b39878c8ad1ebdb806731c2aadf89067c8a75f539ef756175d2.
Testserverimage917d3b45e49e02a72901d9a23162216e5d08f11c573b46e4c139be3c8908a5b2.
FINAL31entryArenaZIPb43b1b4af856d01bd93b72c6275f397cfe7aaf984e01ef5d7b5fbb8eff735112;
197entrysourceZIPbe2ed8863b14e503aba97f20183df848f48400244c474f2fbf1b99a971ede309.
Archivesallmanifestentries+actualonefiles+serverpayloadsverified/noactual.env.
ALL4distroot/desktopstandalonebinariesUNCHANGEDfromturnstart.CurrentShipping
SHAe54e79...unchanged. ActualgamepostNextfix/resultenumcaptureUNVERIFIED. Freshlegacy/sessionIPCfixtures
now/tmp/szero-backend3-verify-FXDRZg/{legacy-ipc-logging,session-ipc-logging}.exe.
No livegame/prefix/containerwrites/gitstage/commit/push;REAclosed/projectfree.

LATESTcef295winner/35efadloser profile-sync1 (2026-10-25): USERconfirmsboth
Victory/DefeatcorrectbeforeNext. BOTHend2normalendroutesstateok21:46:38.795/
39.194UTC,rawoutcome1BOTH,rank_defaulttrueBOTH. Winnerunsupportedproficiency
21:47:04.621;loserunsupportedrank21:47:06.186;winnerleave21:47:19.707. TCPnot
initialfailure,UDP5360/5339packets. ReadonlyDocker snapshot/tmp/szero-cef35-
server-readonly.log; pairedreportanalysis/runtime-cef35-paired-finish-2026-10-25.md.

Recoveredoriginalupdate_player_rank.phpONLYplayer_rank signedint8, cardbadge
preferenceNOTmatchrating. update_proficiency_rank.phpONLYcharacter_idstring+
character_proficiency_ranksignedint8. Bothcommonres0ACK,no typedresponse.
ImplementednativeapprovedfieldselectionSERVICE4,strictPythonexactfieldtypes,
commitbeforeACK,ownaccountnative_profile_statetable/account_storeget/put;
gueststateconnectionephemeral. Login/cardsloadfreshDBstate, no stalehello
profile;selfandcurrentroomopponentownershippreserved. Parentproducerstrips
nativeauthenvelope,notarbitrarybodyforwarding. Newnative_profile.py andtests.
NativeDLLrevisionprofile-sync1 SHA25a62aac4f2d4c883b494918cbdb44546717ed1f45c9735285debd10ef2f72dd.
ServerREBUILD+BOTHclosedgameOURmodreinstallrequired;installeddeltaONLYscripts/
backend_adapter.dllunderWin64/Mods/SzeroLAN(orue4ss/Modsvariant). SessionDLL,
Lua,tracer/cardidentitymapping/originalEXE/PAK/loaders/saves/othermodsunchanged.

UseralsorequestedremoveDisplaysettingsandequallysizedQuickplay/Logintabs.
Removeddisplay/resolutionwidgets+variables;LaunchwritesGame defaultlegacy
optionsBEFOREprocesses. Equalwidth14/paddings in BOTHselectedstates (actualTk
182pxeach). SaveonlyLaunch/loginsemanticsretained. 36launcher/login/savetests
PASS2.176s. Focused35profile/IPC/compiledWin64/storage/ownershiptestsPASS34.432s.
RealMariaDBtestnewownupdatesovergameTCP/currentcard+login/accountisolation/
DBreadback/worker+containerrestartPASS11.860s. No livecontainerwrites.

AUTOMATICELO/WINRATESTILLDISABLED. Nativeendoutcome1BOTHcannotbeinterpretedas
ownwin. Shared/globalwinnercandidaterequiresfurtherproof;context17fa is side/
resultselectorNOTverifiedownwin, andwrittenAFTERendHTTP. No guessedpointwrites.
RawcategoryLABELSproven1Single2DpBattle3TeamUnlimited by originalenumstrings;
rankcachelookupfolds2/3 so DO NOTusecachedrank.battle_typeformodeauthority.
user/update_player_match.phpONLYsession_kindint32 BEFOREstart,NOTwinner.
set_battle_result.php isSEPARATEqueuedop37event (not currentHTTPseam), detailed
resultdatawinnersemanticsstillunknown. Recoveredreportsanalysis/rank-followup-
contract-2026-10-25.md/proficiency-followup-contract-2026-10-25.md andselected
originaltraces. Cardsprojectreleased,noREAopen/noactualgameexecution.

LATEST295f normalbattle-end2 (2026-10-25): USERCONFIRMSactualRankedcombat
ranperfectly;postmatchfailed,reportedwinnermaxinator. ReadonlyDockerbothstarts
ok20:43:16.784/17.130UTC,4673/4701UDPpackets;request_scope20:44:12.765before
nativeleaves20:44:12.942/.948;TCPstayedliveuntil20:45:39/20:46:52. Exactold
refusalrouteNOTcaptured. Nativeendrouteswereabsent. Boundedreadonlyoriginal
145a81ca0/145a2ae40/145a27380/145a66930proveendP1/P2schemaandordering:P1HTTP
BEFOREfinalnativeconnect,P2AFTER. MustACKeachvalidownreportimmediately,NEVER
waitbothbeforeP1ACK. Force-end/drawnotimplemented;NOautomaticElo/statwrites.

ImplementedSERVICE3exactcode/outcome1or2/ownrank_snapshot,notnativeenvelope.
P2startnowrequiresexactissuedcodetofencestaleround. rank_snapshotselectsown
category/extraoriginalcache;11typedfields/float32bits,finiteUTF8bounded. Guarded
getter145a77090/categorylookup145ad7410;absententrymirrorsEXACToriginalzero+
RAWcategory/extraconstructor. Echoownrecordbecauseoriginalresultapplication
otherwiseZEROSnativecache. NeversubstitutewebElo. Noauth/tickets/bodylogging.
BackendnormalendownershipfixedTCP/account/role/code/bothstarted;cachedACK,
conflictingduplicatesrefused;600second1024boundhistorysurvivesfirstnativeleave,
newP1roundrotatescode,lateendscannotmodifynewround. Nativeforce-endstillclosed.
Productionfilesbackend_adapter.c/DLL,backend_rpc.py,backend_services.py,new
native_rank.py;Docker/releaseallowlistsupdated. DLL73f384b038784c74fa13170fc6ed14d00177e190c6cdfc6cd24589ca4e1729c0.
InstalleddeltaONLYWin64/Mods/SzeroLAN/scripts/backend_adapter.dll(orue4ss/Mods
variant). ServerREBUILDandBOTHclosedgameOURmoduninstall/reinstallrequired.
SessionDLL2530e0aa...,tracer86dd4191...,Lua278eb901...UNCHANGED.Cardsunchanged.
Reportsanalysis/ranked-end-response-contract-2026-10-25.mdandruntime-295f-
postmatch-independent-audit-2026-10-25.md;selectedoriginaltracesretained.
41focusedtestsPASS33.499scompiledWin64worker→realbridge→TCPend1/end2,
nonzerorankpreservation,lateend,rematchcode,malformedframes/bounds. BothFULL
sourceonefilesrebuiltSTAGEDONLY.build/desktop;frozenhelperreadbackverified.
Actualgamecompletion/rematchwithend2UNVERIFIED. NoREAopen/livegame/prefix/
containerwrites/gitstage/commit/push. FINAL337Python testsPASS NOskips295.779s includingcompilednativeend1/end2
→realbridge/TCP,actualstagedLinux/Windows-under-disposableWineGUI/resources/
embeddedbridge,legacy+8peerfixturesandisolatedDockerMariaDB/accounts/UDP.
All6Lua mocksPASS. Actualgame/nativeWindowscompletionSTILLunverified.
StagedLinux01ed8bc6c29089fe111938bc58dfa572a27c891d1d226bdd7b89cb6996e15156;
Windows0bdcab1dd671d31ed0713b7efd6f59ee8e1e7b122ff89afa8705d9735235796e.
Testserverimage0ccb372437e04d1fe0dfc9a813c1673f03bc0828fbec265d7ee5c38f6e41ff1e.
Final30entryArenaZIP2a6168ea165a774b4308655b5e263e6d8f4eb4ecc0278e9ec9ee8deefa264348;
194entrysourceZIPccbfcd4b04767e169f34480b161bc16624b4bcf983d4179f6d50423bf54366f8.
Archivechecksums+allmanifestentries+native_rankpayload+bothonefilesverified.
OriginalShippingSHAe54e79...unchanged. ALL4distroot/desktopstandalonebinaries
verifiedUNCHANGEDfromcurrentturnstart. Noactual.env/gamefilespackaged.

LATEST985e/812b battle-start1 (2026-10-25): suppliedpostpair3NOWcapturesnative
prepare0/futureresult0/peerstart0/connect0,commit90legitimate. ThesearetwoSEPARATE
attempts, notbothendsofonepair. NativeconnectionUNKNOWNboundaryresolvedsuccess;
laterSteamHTTP57C8create_requestunparented, NOTprovenexactAPIattribution. Readonly
Docker8cbd...snapshot/tmp/szero-812b-server-readonly.log confirmsfirst648966
644/671UDP, second a583703/681UDP,max212/159. FirstDBrestartAFTERleave, secondno
restart: don'tblameDB. Independentanalysisreportsruntime-985e-812b-independent-
audit-2026-10-25.md andranked-after-connect-independent-2026-10-25.md.

DEEPORIGINALfinding:145a81010 requiredrole-specificpvp/start_battle_player1.php
orplayer2.php (strings147ba1e90/1eb0 confirmedRIPLEA145a8188e/a1). P1roleifnative
firstmemberlocal14594e110(session,0); parser145a27f90 readsROOTmatch_code string
(147ba2500,len10) +match_phase int(147ba24f0,len11).145a833d0 storescontext1968,
sendsnativecommand21via1459c2bb0; P2wait145a733d0 requirescodecontext14b8. Received
21→145a7a0b0 onlyacceptsexpectedFIRSTmember145a1bbe0. OURpriorC/Python/server
whitelistsomittedBOTHrequiredroutes. ImplementedthisKNOWNmissingcontract, NOT
claimedruntime57C8exactbranchproof. Nochangecheck_transactionphase(theverified
consumerignoresit), noforcednativeflags/identity/filter/readiness.

NewCbackendexactroutes6/7, BackendServiceRPC SERVICE1route{} only, NOrequestbody/
officialID/ticket/selection forwarded. Pinnedloginservice/thread/SHA/prefix/native
borrowedresponseownershipguards retained. Foreign/unboundknownstartstilldelegates
unchanged plusboundedbattle_start_foreign_or_unbound_service diagnostic. Newhelper
schema3/revisionbattle-start1 UTCworkerexchange/refusaltimes(refusal=BATCHflush).
Backendservices/Serverresolve_battle requirebothauth+LANlogin,currentCOMMITTED
nativev2profile2cap2partition4/5,orderedrealTCPpeerroles. P1creates32hexmatch_code
perroom+orderedroster+nativeGUIDsignature; retryidempotent,P2requiresP1record.
Returnres0/code/phase0(knowninitialparsedphase,noprogressflagwrite). Membership
notifications/disconnect/lazyrevalidationprune stale/crossroom/rejoinstarts; bounded
MAX_PEERSrecords. Sameunchangedrosterrematchreusescode: per-round/end-battle/
automaticresult/Eloingestion STILLUNSUPPORTED, doNOTclaimcompletedRankedbattles.
Cards/native_sessionDLL2530.../Lua278e.../postpair3tracer86dd...UNCHANGED.
Onlyinstalledgamedelta scripts/backend_adapter.dll underWin64/Mods/SzeroLAN or
installer-detectedWin64/ue4ss/Modsvariant. NEWDLLSHA
6f3280085b7ca598daf434e675de7164c8f8a84a02756d179c9c70e8c39d6fe5.
UserMUSTrebuildserver newZIPservercontext dockercomposeup-d--build ANDclosegames/
uninstall-reinstallOURmodBOTHPCs usingnewZIPlaunchers. Oldserverhasnobattlestart.

Focused31testsPASS39.149s inclcompilednativeworker→2AUTHGameBridges→realTCPserver/
currentroom/codebothroles, outputcanaries/LastError/ownedcleanup andunreadable
nativebodypointerprovingnoread/forward. Server10tests includerealTCPauth/ownership,
wrongrole/P2beforeP1/bodyspoof/guests/cap8/crossroom/leave-rejoin/GUIDfence/bounds.
AdditionalURLguardtest-onlyfixtureeditsincludedfinalsuite. Independentoriginal/
sourceauditconfirmschema/role/no materialownershipissue; rematchlimitationnoted.
Newreportsranked-battle-start-backend-2026-10-25.md+three bounded original start-
battle/contract/battle-id traces andsixagenttitle-messagecontinuationtraces.
REAoriginalSHAe54e79...boundthenCLOSED; staticselectedread-onlyGhidra PE.pdata/
chainedunwindbodies/noanalysis, noactualgame/externalservice/runtimehookexecution.

OnlyfullZIPdelivery. FullLinuxDocker/WindowsSOURCEPython3.13.7/PyInstaller6.16
buildstaged.build/desktop; actualfrozenDLL/Lua/license readbackverifiedboth.
NewstagedLinux02ba5aa8cd3a2e93449d58f02b788c57ef7d6315bebb4b4f1834e86a22065199;
Windows99f070a3244b4bbc91e3ab10e7d6e74693ac6755923f235cac21e7f90f796508.
Isolatedtestserverimagef6c515dd7969063e46d0a7c4593c8be45186621335e5b72182d7789f9e04d093.
ObservedexternallyupdateddistrootNOW92f210ef...Linux/81944c00...Windows; allfour
existingdistroot/desktopstandalonespreserved. Noexternalgame/userprefix/liveDocker
mutation andnogitstage/commit/push/reset. FINAL312Python testsPASSNOskips292.921s
includingactualstagedLinux/Windows-under-WineGUI/embeddedbridgeHELLO5/SESSION4,
newcompiledbattle-startworker→2authenticatedGameBridges/currentroom/server,
allnativeobserver/backend/8participant+56UDProutes/legacy/accounts/save/lifetime/
isolatedDockerMariaDB/web/TCPUDP regressions. All6Lua mockcontractsPASS. Both
frozenDLL/Lua/licensepayloadsexactreadbackverified. FullWindowsSOURCEbuild3.13.7/
PyInstaller6.16 underdisposableWine, LinuxnormalDockerbuild. NOTactualgame/native
Windows/Rankedbattleacceptance. Independentreviewconfirmsknownschema/role/no
materialownershipissue; repeatedsame-rosterrematchnotimplementedperround.
Final29entryArenaZIP SHA256
4e13257af9cb20a527b541f44416fa8ea771cbfff0a89ffe0da096f433518f58;
191entrysourceZIP16d0a46b79236d84bfa99b15f66f4d73d5077cfb124f7b1f9e2c74a5645166f8.
Allarchive/source/manifests/exactstaged/serverpayloadsverified,.env.exampleonly/
noactual.env/noStart-Server. All4diststandalonesverifiedunchangedfromthisturn
snapshot/tmp/szero-battle1-dist-before.json. OriginalShippingSHAe54e79...unchanged.
Noexternalgame/prefix/livecontainerwrites; REAoriginalclosed. OnlycompleteZIPs.

LATEST ef680 Ranked / postpair3 (2026-10-25): userreportsRankedsamefailure.
Cardsremainworking. Suppliedtrace6467d1a457c3f188e6307ee765f910181fe7c9a3d41b0dc379b3616eeb958886
has84entered/84returned, ZEROpostpair, timeout/restoredtrue/inflight0/extensionfalse.
Tracerequest17:26:24UTC, firstsearch17:32:06/07 AFTERinitial5minrecordingexpired.
ReadonlyDocker8cbd888a13a3 snapshot/tmp/szero-ef680-server-readonly.log: shared82ea
joincommitted17:32:48.571/flags43at49.648;1039/1032forwardedpackets9006/8680bytes
max241/196. Leaves17:34:26. Secondshareddbe822197/207packetsbeforeleave. Noactual
innerconnectionfailurecaptured; DO NOTclaimRankedfixed. Original1459aecb0 uses
upper24statusbits; lowbyte90/ADNOTautomaticallyerror, commit145993410 legitimately
90absentoptionalaction. Noidentity/filter/successforcingjustified.

postpair3 ONLYservice_trace.c/DLL+tests: initial5minmenu/backendcapturethenQUIET
waitingforselectedprepare/connect up30minfromhookstartup; firstpostpairactivates
one5mincapturewindow, hard35mintotal/512events. Quietunrelatedcallsforwardwithout
records. Same ring/serial/pendingreturntokens, noreset/reinstall/freeofhooks;
workerreactivationusesatomic-1claim/deadlinepublish/1active toavoidlateactivation
race. Metadatawaiting_for_pair/pair_capture_started, explicitpair_wait_timeout/
capture_timeout. Prefixes17/nativeargs/RAX/LastError/threadscope/bridgecleanup/
ownedrestore/pinnedtrampolinesunchanged. Strictbuild+9actualWin64fixturemodes+
productionunknownhashrefusalPASS46.116s; newlatecasefirstconnectAFTERinitial
window +quietserviceforwarding, noactivationrenewal, idlestop/quietbridgecleanup,
fiberresumption/eventcap stillpass. NewtracerDLLSHA
86dd41917a033955e23507b91012be0f3e96f08621e7d23c94c36d05845157d1.
Clientszero_lan.pyTARGET_DATA firstreceive nowlogs sameboundedmetadataaslegacy;
previouslycountedreceivedpacketsbutomittedfirst-log. NoUDPbehaviorchange.
Native_searchDLL2530.../backendaaa7.../Lua278e...UNCHANGED. Installedgame delta
ONLYscripts/service_trace.dll underWin64/Mods/SzeroLAN orWin64/ue4ss/Modsvariant.
Closegames→newZIPlaunchers→uninstall/reinstallOURmodBOTHclients. NoSERVERrebuild
requiredfrommodes4/protocol5. Noactualgameexecution. IndependentREAaudituses
retainedselectedoriginaltraces/runtimeevidence, no newglobalbinaryanalysis.
Reportanalysis/runtime-ef680-ranked-recorder-2026-10-25.md.

ReleasepolicyONLYfullZIPs; buildstaged.build/desktop, preserveALLdiststandalones.
ObservedexternallyupdateddistrootNOWa3e30305...Linux/7b2a7147...Windows;
dist/desktop7a81918b.../66e9b3ec...preserved. Noexternalgame/userWine/livecontainer
mutation andnogitstage/commit/push/reset. FINAL301Python testsPASSNOskips278.437s
inclactualstagedLinux/Windows-under-WineGUI/HELLO5SESSION4embeddedbridge, new
postpair3compiledWin64observerfixtures,8membernativeworkers+56directedUDP,
alllegacy/backend/account/save/lifetime+isolatedDockerMariaDB/web/TCPUDP.
All6Lua mockcontractsPASS. WindowsFULLSOURCEbuildPython3.13.7/PyInstaller6.16
underdisposableWine;LinuxnormalDockerfullbuild. ActualfrozenDLL/Lua/license
bytesverifiedBOTHonefiles; session2530.../cardaaa7.../Lua278e...unchanged.
StagedLinux92f210efa0725762656a2ecbb1eb93cc7a5641e6eaf65860a1146d969064ad5c;
Windows81944c00fadcda0c25945874a551c8eca9dec651eb660b67cef2d2571aba9fa2.
Isolatedtestserverimage dfd011859fd938bdef2bb1f2624f96ebca2c00de8f56b934f18ab058043123f2.
FINAL29entryArenaZIPSHA256
52ae0d8ccadec1ab52b097a0cdd775b9a44ea91b4416eba355b2df6f571bee58;
189entrysourceZIP898ad2e44678adffc5e34708db8d922dbfe7f5a8c177d0bbba407d5e0147391c.
Archive/source/checksummanifestsverified,exactstagedonefiles/servercontext,
.env.example/noactual.env/noStart-Server. All4diststandalonesunchangedandoriginal
ShippingSHAe54e79...verifiedunchanged. NOTactualgame/nativeWindows/Rankedfixproof.
Independentread-onlyreviewconfirmsnoABI/ownershipissue; exact30minhardcutoffmay
missjuststartingcapture(boundedevidence), don'tclaimeverycutoffraceeliminated.

LATEST tournament/Ranked investigation (2026-10-25): user CONFIRMS cards work.
Preserve backend_adapter.dll aaa7f38ae5f525f0f676aa6c19bffe0ee196af5590f67f78ffebf4421fb8ce03
and Lua/card contracts. Latest bec068 capture tournament16:41:23UTC refused
member_capacity code8 BEFOREserver: requested capacity8, notgenericerror8.
Implemented bounded8 sessioncodec/materializer/ownedidentity/userinfo path,
HELLO5/READY5 immutable up-to64proxyport allowlist, SESSION4 sameorderasSESSION3,
partition5 only; existing HELLO4/twomemberpartitions preserved. Nativehelper
revisionmodes4. Main NativeSearchRPC deepcopiesdescriptor and selects stable
per-remoteTCPUUID proxy. Everyremote keepsdistinct loopbacksocket forprocesslife,
neverreassignedafterdeparture; lifetime64 identities. Serverkind4 targetprefix
upstream/different senderprefix downstream, sameTCPUDP27150; validatesregistered
source/session/partition5/currentdestinationmembership. Legacykind3 refused in
partition5 even2memberrooms. ControlMAX32768 for8member+4096stream, initialhello
still8192. No bracket/actualtournamentcombatsuccessclaim. New2realTCPUDPtests
PASS2.467s all56directedpairs/maxstream4096/noextra broadcast/outsider/departed/
legacyrefusal/nonreusedports. Fixedfirstpacket source race: snapshotassignment/
routemap AFTERselect wakes. Existinglegacytwo-roomrelay alsoPASS.

Ranked STILLUNRESOLVED: readonlyDockerlog3c18549... retained/tmp/szero-bec068-
server-readonly.log; sharedf3ec... hostcreate16:37:19/join27.646/flags43at28.582,
leave16:39:18;923/946forwardedpackets4596/5490bytes sizes1..157/219. Nativeprepare
1459bd290 returns0at16:37:33.485; connect1459aecb0 enters thenoldpostpair1trace
expires16:37:39, inflight1/restoredtrue. NOTproofcrash/hangforever/restorefailure.
postpair2 tracer adds member1459c9fd0/taggedarg2, wait145985340/taggedarg1,
waitresult1459acbf0/plainarg2, commit145993410/plainarg2, peerstart1459b86c0/
plainarg2 onlyselectedpostpairscope. Tag2payloadNEVERreadaserror.17prefixguards
independentlymatchedoriginalSHA. Sameargs/RAX/LastError, noforcedresult. First
postpairentryextendsONCE5min capped10mintotal/512events.9compiledWin64fixture
modes+unknownproductionEXErefusalPASS39.282s. service_traceDLL SHA
9a290e7a030973bad2b6076765f15156273e9d7bb8a455e54cf343596fcb3cc4.
Reportsanalysis/runtime-bec068-ranked-connect-inner-2026-10-25.md and
tournament-multi-transport-2026-10-25.md. REAskillauthorizesboundedparallelwork;
selectedreadonlyretainedGhidra/originalbytes, noactualgameexecution/livewrites.

InstalleddeltasTHISrevision: ONLY scripts/native_search.dll andservice_trace.dll
underWin64/Mods/SzeroLAN (orinstaller-detectedWin64/ue4ss/Modsvariant).
UseNEWZIPlaunchers, uninstall/reinstallOURmod ALLclients withgamesclosed,
rebuildserver dockercomposeup-d--build. Native/newpartitionrequiresALLpeersupdate.
OriginalEXE/PAK/loaders/othermods/saves/cardbackendunchanged. ONLYcompleteZIP
releases; stagebuilds.build/desktop, preserveALLdistrootanddesktopstandalones.
Observedthisturnuserexternallyupdateddistrootto8dd6b860...Linux/0d377670...Windows,
DO NOTrestoreearlierhashes. Noexternalgame/prefix/liveDocker/gitstage/commitwrites.
FINAL301Python tests PASS NOskips275.006s includingactualstagedLinux/Windows-
under-WineGUI/HELLO5SESSION4embeddedbridge, compiled8nativepeers+leave/rejoin,
new2playerQuickmatchHELLO5regression, all56targetedUDProutes+max4096stream,
legacy/native/backend/account/save/lifetime andisolatedDockerMariaDB/web/UDP.
All6Lua mockcontractsPASS. FreshlyrebuiltlegacyWin64IPCfixturealsoPASS1test33.490s
againstrealbridgeafterfullsuite. FullWindowsSOURCEbuildPython3.13.7/PyInstaller6.16
indisposable/tmp/szero-backend3-verify-FXDRZg/wine; normalLinuxDockerfullbuild.
NOTactualgame/nativeWindows/tournamentbracket/Rankedcombatacceptance. Native
DLLfinal2530e0aa8089d7bc2fa2adfac975536a6531a625dd85c4fcb86da4b352200e61.
Compiledfixturesession-ipc-multi.exefreshv2includesalllegacy/newmodes; atomically
refreshedfixtureonlybeforefullsuitereachednativecases. Productioncodeunchanged.
Native-specificreportanalysis/tournament-eight-peer-transport-2026-10-25.md.
ActualfrozenDLL/Lua/MinHooklicensebytesverifiedBOTHonefiles. FinalstagedLinux
 a3e303051a4dff79763b9fb45e960ba0588a6f5566ba8a5de717b5865a7e2d53;
Windows7b2a7147b62ad078fff7f1ba9e0a7f0a39d2ea4e276398773df4337ff1b8351e.
Isolatedserverimage820e392a0ed90e8a506f7111ebd480494215ee28a067d0f68aee699e250d48e4;
4Docker testsseparatelyPASS13.166s. FINAL29entryArenaZIP SHA256
8301ee37ff992cc6df9924d7651aa00e4495857ee5ccea4ff5959d1495061daa;
189entrysourceZIPfa60fc742706d05fd5210ae1a2b07a51c9e8ecee7d15718e8b1c6d0d72c4c1c6.
Allarchivepayloads/manifestshashesverifiedagainstfinalsources/stagedbinaries;
.env.examplepresent,no.env/startscripts. All4diststandalonesUNCHANGEDverified,
originalShippingSHAe54e79...unchanged. No livecontainer/externalgame/prefixwrites,
no gitstage/commit/push/reset. OnlycompleteZIPdeliveries.

LATEST game-port login / supplied36e2+fcd97 (2026-10-25): user requests login
ONLY through gamehost/port27150, no second websiteaddress/webmanagementbutton,
PLAYER Quick play/Login tabs with casual-onlyremark, explicitLogin+remembering.
Implemented account_client TCP opaccount/version2/actionlogin(username/password)
oractionme(token), bounded8KiBrequest/64KiBreply. GameServer one-shot async
handler, realAccountStore, nopeer/UDPallocation, genericerrors/nocredentiallogs,
24attempts/min/IP/2048buckets/8authworkers. Launcher explicitLogin savesONLY
protected0600scoped(host/port/username)sessiontoken immediately; otherdraftsONLY
Launch, optionalINI beforeallprocesses retained. No plaintextpasswordsaved:
reusabletoken rememberslogin (mainexplainedtouser); hashcannotbereplayed.
Restoredlogin launcheswithoutpassword; credential/servereditsrequireLoginbutton.
Launch actionme revalidatesprofile/displayname beforeprocesses; quickbridgesend
tokenEMPTY whilekeepingrememberedaccountprivate. Oldaccount_urlremoved/migrated.

CARDDEPLOYMENTMISMATCH FOUND: externalcurrentgamebackendDLL6e0bdc15...backend3
NOcardhandler, whilebothpreviousZIPonefilesembedded42c687c5...WITHcardhandler.
ActualreadonlyCArchiveinspection+externalfilehash provesCURRENTmismatch, NOT
historicalversionduringlogs (schema1omittedidentity). Newunconditionalpreflight
comparesbackend_adapter.dll ANDnative_search.lua ANDsessionDLL againstbundle,
BEFOREanyprocess; stale/missing refuseswithreinstallinstruction. Tracerchecked
whenenabledasbefore. Noexternalgamewrites. Newbackendhelper schema2readyrevision
accounts-card2+workercomputedownSHA, boundedprivacy-safepreIPC refusalcounters,
knownunsupportedrank/proficiency/cardupdateENUMrefusalONLYpinnedservice, no raw
URL/body/ticket/platformIDs/pointers. Strictbuild+2nativefixturesPASS13.773s.
backendDLLSHAaaa7f38ae5f525f0f676aa6c19bffe0ee196af5590f67f78ffebf4421fb8ce03.
Reportanalysis/runtime-36e2-fcd97-card-deployment-2026-10-25.md. Correctoriginal
platform_user_idkeyconfirmed; NOlooseningtargetschemas/owncardforunknownpeer.

RANK LOADING NOTFIXED: stoppedDocker197256af102f logs readonly retained
/tmp/szero-latest-server-readonly.log. 36e2/fcd97 bothmatch+joincommittedtwopeers,
bidirectionalfirstUDP2B, hostflags40→43, laternativeleaveafterloadingdelay.
fcd97UTC14:50:39.643join,40.012/013UDP,49.586flags,14:51:53leaves; servermanual
shutdown14:53:04 later. First-packetlogNOTproofonly2Btraffic; NativeIPCdisconnect
pendingFalse normalpercommandcloseNOTgameTCPdrop. OriginalboundedreadonlyGhidra
14599c540 waits2members+1459515c0 beforehostflags3, then1459bd290(peerprepare)/
1459aecb0(connect); NOexactruntimebranch/statuscaptured. Existingnative_search
DLLmodes3 EXACTunchanged10af...df1d3f. No guessedtransport/filter/successpatch.
NewOPTIONALservice_trace12wrappers (prior10+these2), schema4probe_revision
postpair1, plain40arg2/7and4scalarABI. OriginalSHA+all12prefixguards; independent
originalPEprefixbytesverified; same512events/5min/knownthread/pinnedtrampolines/
ownedrestore/LastError/RAXpreservation. Nativefixture adds postpairmode with
distinctreturnedcodes/canaries/allargs/restoration; previousfiber/thread/cap
contractskept. TracerDLL6fe6064b1b3ba3275d6ae6b30cb3d0cb00a90d9841be25877ff9d11103b0a280.
Serveradds fixedperpeeraggregateUDPcount/bytes/min/max onnativeleave/disconnect,
no payload/addresslogs orrelayadmissionchange. Reportanalysis/runtime-36e2-fcd97-
ranked-loading-2026-10-25.md and2retainedoriginalcontinuationtraces. Needfresh
logged-inRankedwithoptionaldiagnostics toidentifyactualpostpairerror; oldmixed
helperrunNOTnewcardacceptance. Actualcardrendering/Rankcompletion/resultingestion
STILLUNVERIFIED/unsupported asapplicable. No actualgameexecutionthisrevision.

BothonefilesFULLsourcebuilt/stagedONLY.build/desktop (freshWindowsPython313
Wineprefixretained); frozenresourceidentitiesreadbackPASS. NewstagedLinux
8dd6b86049b34b210a01a379ed2eb0ef299b89c099495e7d000a627fe9c9f79a;
Windows0d3776700dfb9cf2b770293a9d252643e53e18fef17149b4edfea528024c4753.
SourceGUI9TCPaccount+18setupfocusedtestsPASS; new7accountconnectionPASS0.253s,
5UDPmetadataPASS; nativepostpairtracefixturePASS30.120s. Sourcepreviewbothtabs
visuallyinspected, fixedLaunchfooter reachable. Isolatedserverimagee449077...
rebuilt; no usercontainers/prefix/game/savesmodified. Standalone distrootnow
externallyupdatedto81162abb.../445443...; preserve, NEVERrestorehistoricalhashes.
OnlyfullZIPdeliveries. Installedpayloadchangesvsprioraccounts ONLY
scripts/backend_adapter.dll +scripts/service_trace.dll (detectedWin64/Mods/
SzeroLAN orWin64/ue4ss/Modsvariant). Closegames→uninstall/reinstallOURmodBOTH
clientswithnewZIPlauncher; rebuildserverComposekeeping.env anddata/logvolumes.
FINAL292Python testsPASS NOskips218.930s inclbothactualfrozenUI/embeddedbridge,
TCPloginrealMariaDB/sessionpersistence/adminrestart/Docker+UDP,compilednative
backend/schema2/refusals/postpairtracer/allpriorlifetime/save/sessioncontracts.
All6LuamocksPASS. InitialfullruninterruptedafteroneNEWtestincorrectlycompared
theentireprofilebefore/aftertrustedrankupdate; changedtestchecksstabletoken/
identityANDupdatedrating1016/games1. No implementationerrorhidden; cleanfinal
fullsuiteabove. No gitstage/commit/push/reset. ActualnativeWindows/gameproofNOT
claimed; WindowsGUItestedunderWine. Docsclarifybrowserlogoutonlyownsession,
launcherrememberedtokenrevocableserver-side throughaccount_sessions.
Final29entryArenaZIP77c0530a48a575161d66c9264ecbbe92c7dd13cae5d4cdd722cb5c2f1489a2b4;
186entrysourceZIPdd0c21b70d8f272fe1b2c43e209a3d6ab37399a30117d65c01fcc054b7e7a15b.
Source/archivepayloadmanifestsverified; bothactualfrozenDLL/Lua/licenseidentities
verifiedagainstsource. OnlyZIPs/checksumsdistupdated, standalonefilespreserved.

LATEST secret policy (2026-10-25): user requires ONLYlength>1 forpasswords/admin
token/DBsecrets. arena_supervisor.read_secrets nowlen>=2, NOcharacter/upperlength
restriction; movedpymysqlimporttomainforpurevalidationtest. Websiteaccountpassword
server+HTMLmin2/no128cap. AdminbootstrapconstanttimecompareUTF8bytes supports
Unicode tokens; generatedopaque sessiontokens remainrandom/notuserpasswords.
Updated.env.example/ACCOUNTS. SixaccountstoretestsPASS0.336s including2char
password/Unicodeadmin/punctuation/longsecret/0or1charrefusal. DBexternaluser
arena_editor/ARENA_DB_EDITOR_PASSWORD/schemaarena; internalapparena password
ARENA_DB_PASSWORD. Server-onlyrevision, no launcherrebuild/clientrepatchneeded.
ThreeHTTPtestsPASS1.607s; rebuiltisolatedimageac6949...;4realDockerMariaDB/
web/accountpersistence/UDPtestsPASS13.411s withEXACT2charpunctuationsecrets.
FinalArenaZIP6b5b4280e776cd302eec75cbeb012e4447c7bbde5c31acd8622aef22c14b165e;
sourceZIPe2edcd0ce169ba9b202c616d7969be972af5c39f35ddce6e9d9f64466fbad294.
Archive/sourcechecksums+actualupdatedform/helperpayloadsverified. No livewrites.

LATEST Compose-only setup (2026-10-25): user explicitly rejects generated.env
and start scripts. Newlan/.env.example included in BOTH completeZIPs as
server/.env.example /lan/.env.example. User copies to.env and supplies allthree
secrets; docker compose up-d--build (or docker-compose) is sole deploymentflow.
Removed Start-Server.sh/.cmd AND setup_server_env.py fromsource/Docker/allowlists;
no server writes.env. Compose requires nonemptysecretvariables beforestartup;
supervisor retains24..128 URLsafe validation withclear manualsetup message.
README/DEPLOYMENT/ACCOUNTS/START-HERE updated. Historicalnotesbelow referring
to generation/startscripts are superseded. No client rebuild/patch needed,
standalone distroot/desktopbinaries preserved. OnlycompleteZIPs regenerated.
Verification:4accountstoretestsPASS0.315s; Composeconfig --quiet refusesempty
example/acceptsfilledtest.env withoutservices; rebuiltisolatedimage7736fee...
and4realMariaDB/web/persistence/UDPsmokesPASS13.252s. No livecontainerchanged.
Final29entryArenaZIP65fc6b89a678013db151f4fd90efd88082b91cdd115e3d594ad30d287a98ac09;
186entryfulltoolsZIP7f88ae19c341c3e75d9136a2769a440ab4a77eac81c3341d9145c22658ef4278.
Archivechecksums/sourceallowlistsverified, .env.examplepresent/noactual.env/
noStart-Server/nosetupgenerator, bothpackagedonefilesbyteUNCHANGED.

LATEST accounts/cards + supplied3d729 (2026-10-25): implemented ONE nonroot
container with MariaDB3306/external schema editor, themed Python website8080,
gameTCPUDP27150. Start-Server scripts build/generate private.env via Docker;
first registration requires ARENA_ADMIN_TOKEN and becomes admin. Later users
need username/password only. Salted scrypt passwords, hashed30day sessiontokens,
revocation, displayname/avatar/banner preferences, separate single/dp/team
ratings/stats, admin200line logs and fixed game-worker restart. NoPHP/shellbridge/
Docker socket. Readonlyroot, persistent server-data/server-logs, newaccount_store,
arena_web,arena_supervisor,setup_server_env,web/ assets. docs lan/ACCOUNTS.md.
LAN Elo1000/K32 transactional/idempotent record_result exists ONLY trustedserver
boundary; AUTOMATIC NATIVE RESULT INGESTION STILL UNSUPPORTED. Web saysso.
DoNOTclaim native/officalrankpersist or completedrankedbattles.

Launcher Account login vs Quick play. Token verified by real gameTCPserver,
server profile displayname overridesname; invalidtoken NEVERguestdowngrade.
Token ONLY private0600launcherpreferences/bridgeenvironment/preflighthello,
NOTpasswordpersist/gameconfig/gameenvironment/argv. SaveONLYLaunch incloptional
INI BEFORE allprocesses. GuestnativeRankentrycategory2denies usinginstance
account.policy enabledONLYauthenticatedwelcome; loggedstartup leavesmaintenance
entryUNPATCHED foroptionaltracer. Guestsdiagnosticenv0/disabledcheckbox. Local
policy is cooperative UI restriction, NOTananticheat/auth credential. Existing
sessionrelay(native_search.dll10af...df1d3f)/Lua/tracerUNCHANGED.

Nativecard SERVICE2 forwardsONLY exactself orszlan:<peeruuid>. Localnormalization
compares actualguardednativeprimary, NOTguessallunknown=self; noofficialplatform
ID/body/ticketforwarded. Serverremote resolution ONLYcurrentroomparticipant;
selfactualTCPpeer. Original1454f9ec0 checksoptionalpresence+98; originalparser
requires card.player_rank SCALAR atcardroot, NOTnested details/object. Implemented
knownrootdefaultfields/explicitfalsebooleans inlogin ANDstandalonecard. Website
artwork IDs deliberately NOTinvented nativeassetIDs. ActualGAMEcardrendering
stillunverified. NewDLLbackend_adapter SHA256
42c687c5add08b209c773ce80a0536e171a4e2ae480dd424417a10ca1c7898e4.
Onlyinstalledgame deltafrombackend3scripts/backend_adapter.dll underWin64/Mods/
SzeroLAN orinstaller-detectedWin64/ue4ss/Modsvariant. Closegames→newZIPlauncher→
uninstall/reinstallOURmod BOTHclients. ServerREBUILDvia newStart-Serverrequired.
OriginalEXE/PAK/loaders/othermods/savesunchanged; noexternalgame/liveDockerwrites.

Supplied3d729 actual2playerRankedfailure NEWROOT: Dockerread82fdd6cb887d11:57UTC
shows candidatesexistbutbothreject numericindex5/key7/comparison2/query0/
candidate80; two creates/nojoins, notidentityexclusion. Nine typedlogin/backend
returns0,7maintenance0;81traceenters/81returns;50adapterreplies. Nofootermeans
incompletesnapshotNOTcrash. Five otherSteamcreatefailures noUIattribution.
EXACToriginal145a5d990 key7MINIMUMCOMPLETIONthreshold, notrank! attr6ownrate,
attr7requiredminimum(setting+50:2→70,3→80,4→90); key7<=ownrate andkey6>=minimum.
OriginalJSONmatch_completion_rate+244→cache+60/+1e4→service+2d4→141f9be90/
145cb2da0→query. OURlogin0 caused80<=0reject. CorrectfreshcleanLANprofile100%,
preserveoriginalfilter/sessionDLL. Regressionred0/green100/stillreject70under80.
DefaultisLANpolicy, NOofficialcompletionhistoryclaim. Futureverifiednative
completion/disconnectevents mustdrive metric; actualRankbattlepostfixUNVERIFIED.
Reportsanalysis/runtime-3d729-ranked-cards-2026-10-25.md,
ranked-key7-completion-filter-2026-10-25.md,accounts-native-cards-2026-10-25.md.
REAoriginalbound/closedbycardtask; freshboundedreadonlyGhidraCardsproject/tmp/
szero-cards-ghidra withnoanalysis/selectedPEunwindbodies+originalobjdump. No cold
globalREAqueries oractualgameexecution. Retainednewtracesinanalysis/.

FULL286Python tests PASS NOskips223.674s includingrealMariaDB/external3306,
accounts+ratingpersistenceacrosscontainerrestart,adminworkerrestart,compiled
nativeSERVICE2secrecy/gate/policy,legacy/modes3TCPUDP,GUI+embeddedbridgeboth
actualonefiles,existinglaunch/save/lifetimecontracts. Addedoneadditional
opponentroomownershipregression afterward:5accountconnectiontestsPASS0.229s.
All6Lua mocksPASS. Nativefocused2testsPASS13.941s. WindowsFULLsourcebuildfresh
officialPython3.13.7+PyInstaller6.16indisposable/tmp/szero-backend3-verify-FXDRZg/
wine (NOresource-refreshshortcutthisrevision). Windowssource34testsPASS5.230s;
actualfrozenWindowsGUI/bridgePASS11.154s underWine, NOTnativeWindows/gameproof.
LinuxfullnormalDockerbuild.stagedONLY.build/desktop, exactfrozenDLL/Lua/license
readbackPASS. StagedLinux81162abb666e49d500095c70c178e7b8e08da9f1e55d66c53610c0d8d70d9820;
Windows445443788c470f553237fec1717e8bd3b2cbf33305df914b8e968c2d5474da77.
Isolatedtestedserverimageaccounts-test001db0986457edf56797e49db5179dd42fd38b89ed7b34c8a4003b80164561e6;
sourcehashverifiedbackend a286dab33c88be747dbbca226a839648a4ccd57ce884f23b6d6256851ed961de,
envwriter ec1d43979c820e7cb6ca5596eb496be179d75f8606208155e05c26fdc9baa3f0.
OnlycompleteZIPdeliveries; existingdistroot/desktoplaunchersNOTwritten/deleted.
FinalArena31entriesZIP SHA256
d9c6ed8b4ca1de05f8e90b74a5c94ac98c16fc8fe21edf78c57327b78223b8e1;
fulltools188entriesZIP b3430cd6e93c98a1afd5b3d9f6e40e5438fb28576dfac29e7b9dedf5484318fc.
Bothsource/archivepayload/checksummanifestsverified; no.env/gamefilespackaged.
No gitstage/commit/push/reset. Userexternallyupdateddistrootto priorbackend3
90558ad...Linux/0c513284...Windows; doNOTrestorehistoricalhashes.

LATEST backend3 / f207 (2026-10-25): backend2 DIDpassnativeLogin! Adapter12
exchanges=10login661B+transaction68B+banner36B. Trace62entered/62returned;
firstlogin_response10:55:11.907UTC→code0 at10:55:12.307,backend/servicealso0.
9laterlogin_response57C80000mostlyinstant, nofurthertransactionIPC. Ranked
mask32/category2laterpropagateserror. 3separatelowerSteamcreate_requesterrors
stillpresentbutownershipunknown; doNOTconflatewithLANresponsesreceived.
Nofootersinthesnapshots; NOTproofcrash/restorationfailure. MetadataSHA256
a7b1728687185c7c465034083fa6ed817145c4eaaca45d71ec49b6efd01aea09(adapter)/
ed30bb722eb801b34bd9aa4505179f49f54d84081eebf52bc93742c62502445d(trace).
Finalsessionreportmodes3installed/thread572matches/noquarantine/nooperations.

SOURCEBUGreproduceddeterministically: normalexchange leftjobDONE/hook_done1
onreturnuntilworkerpollresetIDLE. ImmediatefollowupCASexpectsIDLE→OUR57C8
beforeIPC. Oldtestswait_idlehidgap. NewTESTONLYworkerpauseafterDONE makesold
codeFAILjob.state==IDLE(exit3). FixednormalhookreleasesDONE→IDLEafteroriginal
projection+cleanup,BEFOREreturn. WorkerusesCASDONE→IDLE, NOTunconditional
storethatcanclobbernewQUEUEDjob. Cancelstillretainsworker-ownedbufferuntilACK.
One-inflight/unknownroute/thread/SHA/vtable/auth/readiness/refusalguardsintact.
Reproducedbugconsistentwithuserpattern, NOTactualgamebranchinstrumentation/
proofevery57C8samecause. No forcedsuccess/filter/identity/accountchange.

Onlyproductionchange native/backend_adapter.c+rebuiltbackend_adapter.dll SHA
6e0bdc152c3684eec1f34937f3dd1f8d7e407283df634b59d4a43e9f5383d5c6.
InstalleddeltaONLYSparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/backend_adapter.dll
(orWin64/ue4ss/Modsvariant). Closegames→newZIPlauncher→uninstall/reinstallOUR
modonBOTHclients. Serverunchangedbackend2(res0),NONEWserverrebuildrequired.
native_search.dll10af5494...df1d3f/Lua/server/save/config/EXE/PAK/loaders/othermods
unchanged. ActualgamenewRankacceptanceUNVERIFIED; cardtargetmapping/results/
ratingprogressionSTILLunsupported. No newREA/nativeoriginaldecompneeded; source
concurrency+compiledWin64fixturework. Reportanalysis/runtime-f207-backend-
handoff-2026-10-25.md. NeedNOnewidenticaltesttorediscoverthisknownsourcegap.

Old/tmpfixtures/buildprefixesVANISHED. FreshdisposableWineprefix
/tmp/szero-backend3-verify-FXDRZg/wine initialized; legacy/sessionIPCfixtures
rebuiltfromsource. InitialoldpathWinefailurewasenvironmentNOTregression.
18focusedbackendtestsPASS21.573s afterred/greenproof. ActualWinfixturepreserves
cancellation/canaries/threadscope/errors/ownership/hookrestore and nowrealbridge
5consecutiveroutes WITHOUTwait_idle/delay. StrictproductionDLLbuildpasses.
Linuxonefilefreshbuild .build/desktop; WindowsbuildPythonalsoabsent, instead
refreshONLYbundledDLL inpriorunsignedonefileusingpinnedPyInstaller6.16 API.
analysis/scripts/refresh_windows_resource.py verifiesoldPEchecksum, allpayload/
bytecode/runtimeidentity, bootloaderexceptchecksum, originalPython313cookie,
refusessigned/appendedinputs. NewPEchecksumchecked; actualWindowsGUI/bridge
underfreshWinePASS10.646s. NOTfullWindowsrecompile/nativeWindowsgameproof.
NormalBuild-Launcher.cmdfullsourcebuildstillavailable. No dependencydownload/
userprefix/externalgame/liveDockermutation. StagingONLY.build/desktop, existing
distroot/desktoplauncherspreserved. FINAL263Python testsPASS NOskips201.494s,
all6Lua mockcontractsPASS. ActualstagedLinux/Windows-under-WineGUI/resources/
embeddedbridge, refreshedDLLnativefixture/5routechain/legacy+modes3TCPUDP/
same-platformLANidentity/readonlynonrootDocker/save/launcherregressionsallpass.
NOTactualgame/nativeWindows/battleacceptance. FinalArena22entryZIP SHA256
05a864c1d3c0844085226bbc4fadbaa3ba32c812cbd834111f6e8076318fcfef;
fulltools174entryZIP464e38ac01649a4079a5becd5c1c310401dbdd4cf94a8132d1e1f384b744432a.
Source/archivepayloadmanifests+bothfrozenDLL/Lua/licenseidentitiesverified.
FinalstagedLinux90558ad15b8be001feaa0958898434e8f4d649163bbf07e427ef557e84f9f663;
Windows0c5132848c3f26fd3605779f3f8468b39a3a4e1306f9357998ecf1b9c7f43c9d.
OriginalShippingSHAe54e79...unchanged, servermoduled056f11f...unchanged. Existing
distrootf8f9.../f424...anddist/desktopoldbinariesuntouched. No gitstage/commit/
push/destructivecleanup, noexternalgame/prefix/liveDockerwrites.

LATEST backend2 / supplied1080 (2026-10-25): userRankedthencardboth55E5E2BF.
Adapter8loginrepliesRECEIVED653B, trace40entered/40returned;8backend80088/
providerTAG2→55E5E2BF, ZEROlogin_response entries. ThisisNEWboundaryvs466,
notoldtransportfailure. RootcauseOURbackend1omittedrootintegerres. Existing
retained145ad0500 commonwrapperlooks147bab894(len3), originalboundedobjdump
confirmsres/msg/server_time. Missingres+HTTP2xx EXACT55E5E2BF beforetyped
handler;resnonzerooriginalerrorconvert,res0leavesvalidreply. Priorpayload653B
reproduced,corrected661B. NOTcapturedplaintext/actualbranchbreakpoint; shipped
source+runtimecode/callbackabsence/sizecorroboration. NeedNOnewidenticallogs
forTHISknownomission. Reportanalysis/runtime-1080-backend-envelope-2026-10-25.md.

SERVER-ONLYproductionfix lan/backend_services.py: requestvalidatesandexecutes
knownhandlerFIRST, thenaddsres:int0toactualsuccessfulpayload. Unknownroutes,
nonemptybodies/missinglogin/ownershipinvalidstillERROR, no forcednativecode0/
genericunknownsuccess/datawrapper/authchange. All5knownroutesneedcommonres.
Testsupdatedservice/bridge/compiledworker/Docker/bothunchangedfrozenclient
runtimes tocheckrootres0. Newall5routecontractregression. Previousfixtureonly
checkedtypedkeys/mockprojector andmissedcommonwrapper; earlierpassingtests
didNOTproveactualgamecontract. Cardtargetmapping/rankedresults/progression
STILLunsupported. Usercardfailureconsistentwithloginfailure, no tracedUIparent
attributionforlaststandalonelogin; doNOTclaimcardfunctionalityfixed.

NOclientrepatch/rebuildneeded: clientonefiles/nativeDLLs/LuaBYTEUNCHANGED.
InstalledgamefiledeltaNONEthisrevision. FullZIPcontainssamecompatiblebackend1
clients+correctedservercontext. ExtractZIPserver/, dockercomposeup-d--build,
restartgames. OldofflineimageMUSTNOTreuse. Liveusercontainer/externalgame/
systemWineprefixuntouched; isolatedtestimageonlyrebuilt ee08f9f8fd1303879bad74f80a2f55caee528a4c686d6cc9f000f01d80426ed1.
REAoriginalSHAreboundandCLOSED; no newcoldquery/globalanalysis/gameexecution.
OriginalEXE/PAK/save/config/loader/othermodunchanged. Currentdistrootlaunchers
observedf8f9b13e.../f4249512... matchingpriorZIP (externallyupdatedsincelastturn);
doNOTrestorehistoricalhashes. ThisturnonlyZIPs/manifestsupdated, nostandalone
dist/desktopfilesoverwritten. FINAL263Python tests PASS NOskips204.863s,
includingcompiledWin64worker→realbridge/server,res0contractall5routes,
actualunchangedLinux/Windows-under-Wineonefileswithnewserverandisolated
nonrootreadonlyDockerbackend/nativeUDP,allpriornative/identity/session/save/
launcherregressions. All6Lua mocksPASS. Noactualgameacceptance/newbattleclaim.
Fulltools174entryZIPc889b0bd04e0ef8f41f7d41be5648d5ea851bbede18389e1b497b77036871544;
Arena22entryZIPbfc5409b3b64130ce25c2a8b73b6a5eab25ff16742844bd49605acaa38182151.
Manifests+archivepayloadidentitiesverified. ServermoduleSHA256
d056f11f1cc9601ed254e17aae0e6e0aa81d5d35e96b628ff167faeddf8ca325.
Unchangedonefilesf8f9b13ee0dd9ad08a2590f8a65a03dbd7547f0ff18d897fb2ac791e404f79be/
f42495128941a7630b87c36d50344394255c9122ca0ed97688fbe6a1261346be.
No gitstage/commit/push/destructivecleanup. OriginalShippinghashunchanged.

LATEST backend1 implementation (2026-10-25): supplied466 trace SHA256
f93871a2a31560b74e4d9a0d8c4abb57fef29b9dcda5469314b3ca3b1b2a2154
CONFIRMS49entered/49returned, ALL10HTTP attempts exactcreate_request zerohandle
BEFOREsend, all7backendready80088. Rankedmask32/category2 samefailure.
DoNOTaskanotheridenticaldiagnostic/accounttest. NEWOPERATIONALLANbackendadapter
implemented, NOT merelytrace: separate backend_adapter.c+backend_response.{h,c},
backend_rpc.py,backend_services.py andGameBridge/serverintegration. Exactfive
routes login/check_transaction/notices/reportcounts/banners; routeONLYIPC,
NOtickets/auth_info/requestbodies/platformIDs/officialnetwork forwarded.
TCPpeer/name ownsnew ephemeralLANsession;bodymust{},unknownroutefails; live
binding loss refusesrebinduntilgamerestart. Existingnative_search.dll EXACT
unchanged10af5494e201ff9a24df05ca3ead8a23d24aecafe07471f3d18986dd67df1d3f.
No readiness/authentication/platformcheck forcedsuccessful. Original145a9c800
3argborrowedrequestseam, original64BrawHTTP/72Bprojectedtaggedresponse,
40Bnativeborrowedstream14591c800→14593dbb0 originalJSON→nativecleanup.
Header40Bmapselfrelative;nevermemcpy. NativeSBOinline30withoutallocator,
22withflag2;heap+24capacity verified1458c04a0. SHA+7entryprefix+viewvtable/
slot/thread/URLscope/pinnedservice guards. Onlyworkerdoesnetwork/hash/hooks;
gamethreadcooperativelyyields,8sabsoluteI/Odeadline,cancelbufferACKbefore
reuse,pinnedtrampolines/ownedprefixrestore. NativeDLLfinalSHA256
b04829637047030be51b9ee1af6e71b513f752e83d37746a8e4fed5f9b732c5d.

NativeRankwindow145a66930 invokesoriginal145ad7410(create=1), soemptyLANrank
listusesGAMEdefaultrecordconstruction, NOTinventedcategoryrecords. Scalar
getters/identifiednullableconsumers empty-safe. ThisdoesNOTproveactualgame
Rankedentry/match/resultacceptance. CardtargetmappingNOTimplemented:145ad77c0
consumestargetstring andvalidatescard1454f9ec0; neverreplyowncardtoopponent.
Rankresults/persistentLANratings/officialprogression/unknownlaterbackendroutes
remainunsupported. DonotclaimfullRanked/cards/Shopfix. Nativeprojectorusedin
productionisoriginal; testfixtureprojector/scheduler/allocatoraresynthetic.
Fullreport analysis/lan-backend-adapter-2026-10-25.md +independentHTTPownership/
payloadreports +retainednative-backend-adapter-*-2026-10-25-trace.txt.
REAoriginalSHA boundandCLOSED; findingsfromboundedreadonlyretainedGhidra+
originalobjdump, notcoldREAquery/runtimeinstrumentation/globalanalysis.

Onlyinstalleddeltasvspriordiagnosticpackage: NEW
SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/backend_adapter.dll andUPDATED
scripts/native_search.lua (orinstaller-detectedWin64/ue4ss/Mods/SzeroLAN).
Normalclosedgameuninstall/reinstallOURmod onbothclients. ServerDockercontext
addsbackend_services.py: REBUILD/recreatewithdockercomposeup-d--build. Existing
offlineimageislowerrevisionandMUSTNOTbereusedforthisbackendupdate. Testimage
szero-lan-server:launcher-dev f2a090e90534f6c3259fe58c385977a15230b3610f18938466a11c2f19941179.
LiveuserDocker/externalgame/systemWineprefixleftuntouched. NooriginalEXE/PAK/
save/loader/othermod/configchanged. OriginalShippinghashreverifiedunchanged.
BothonefilesrebuiltSTAGEDONLY.build/desktop, frozenpayloadidentitiesverified;
distrootanddist/desktoplaunchersNOTchanged. OnlycompleteZIPdeliveries.
Newtests test_backend_adapter.py/test_backend_bridge.py/test_backend_rpc.py/
test_backend_services.py;17focusedtestsPASS20.537s beforefinalSSOcorrection,
finalnative2testsPASS11.122s afterward. RealcompiledWin64hook→loopbackIPC→
GameBridge→realTCPserverpath passeswithsyntheticnativecallbacks, NOTactualgame.
All6Lua mocksPASS; lifetimeclose/killedparent8testsPASS. PortableASan/UBSan
detect_leaks=0PASS, NOleakcheck/performanceclaim. Hookframe1296B/worker131536B,
notwholeDLL<=512. FINAL262Python tests PASS NOskips205.249s, inclactual
LinuxonefilewithnoPythonPATH,WindowsonefileunderdisposableWine UI/resources/
embeddedbridge+backendIPC,compilednativeworker→bridge→TCPserver, existing
legacy/modes3sessions/same-platformidentityLANpairs/bidirectionalUDP,and
isolatednonrootreadonlyDockerbackend+UDP. All6Lua mocksrerunPASS. First262run
hadONLY3failures: acceptedcloseRSTexpectation, synthetic__new__bridge missing
backend_rpc, installerexpected19notnew20files. FixedRSTtestallowance,getattr
disconnectguard,andinstalledfilecount/newDLLassertion. Focused18testsPASS
12.455s thenrebuiltbothonefilesbeforeFINALcleansuiteabove. Noactualgame/
nativeWindows/Ranked/card/performance/leakcheckacceptanceclaimed.
SourcefullZIP174allowlistedentriesSHA256
5fc4b970e0f464bec8ae3155f7bbf10d092699df6f15d6e7251a76e1ce65ffc1;
Arena22entryZIP9f13b6c431f076586be726bfb393a887c8f99b6b45821f3c8f51ee944502dccb.
Bothmanifest/archivepayloadidentitiesverified. FinalstagedLinuxonefile
f8f9b13ee0dd9ad08a2590f8a65a03dbd7547f0ff18d897fb2ac791e404f79be;
Windowsf42495128941a7630b87c36d50344394255c9122ca0ed97688fbe6a1261346be.
Diststandalonehashesbefore/afterunchanged; originalShippinghashunchanged.
No git staging/commit/push; existinguntrackedworkpreserved.

LATEST4b6backend submission (2026-10-25): suppliedSchema3traceSHA
c874c11b5ec668d838bf8f969c99a162d6418ab710fc7fb174aed716fef49e64:
51entered/51returned;13providerTAG2,13backend_login57C80000,NOlogin_response.
Nofooter; doNOTinfercrash/restoration. TAG2doesNOTvalidateticketcontents/remote
auth. NologinresponseisNOTproofofNOlowerHTTPcompletion/packets. Actualmask32/
category2propagatesbackendfailure. Newanalysis/runtime-4b6-backend-submit-
2026-10-25.md +6native-backend-*-trace.txt +independentauditreport.

Recovered145a99bc0 cachedservice+468must80088 (constructorinitializesit), else
copiesstatus; doNOTforceitready. Session/URLemptygiveDIFFERENTcodes55E5E221/
57C779B7. Eligible→145ad0500→145a9c800→bundle+38HTTPservice→14593e7d0→
14593e4b0→vptr+40. Steamvptr147b95128/+40=14591cb70, local147b95950/
+40=1458af000. NativeSTEAMHTTP_INTERFACE_VERSION003 context1485d76a8.
CreateHTTPRequesthandle0 emits57C80000BEFOREsend; otherexactsetup/async
branchesalsoemiterrors. STATICbranchesknown, user'sEXACToneNOTyetobserved.
NOaccountcause/faketicket/forcedsuccess/officialrankclaim. RequiredownLANHTTP/
profile/rank/maintenancecontractsNOTimplemented. Workinglobby/QuickmatchDLL
modes3EXACTunchanged10af5494e201ff9a24df05ca3ead8a23d24aecafe07471f3d18986dd67df1d3f.

OptionaldiagnosticSchema4now10wrappers: addsHTTP14591cb70/7args, sharedstring
145851440/4 anderrormove145811d40/2. SharedhelpersrecordONLY11exactoriginal
HTTPcall-returnRVAs; unrelatedcallersforwardimmediately. ALL10entryprefixes
AND11E8targetscheckedbeforehooks; independentlyverifiedagainstoriginalSHA.
failure_originENUMonly(noRIP/URL/headers/tickets/body), backend_status_valid/
backend_statussnapshot+468. StringmarkersNOoutputread/code_validfalsebydesign;
HTTPsuccessblobnotreadaserror. async_holder_error !=remoteHTTPerror; abort/
cancel !=userclickedcancel; missingholderincludesIDmismatch. Sameargs/RAX/
LastError,512event/5min/knownthread/endpointstop/pinnedtrampolinerulesretained.
NativehelperSHA3b4bd9dc4be093f52fd452c2f26cec89c66daa3e8ea7905b3ab52a5b1ad9541c.
Fixturetransportmodeverifies7argforwarding,unknowncallerNOevent,11origin/
neighbor/familyclassifiers,backendstatusvalid/changed/overflowreadguards. Earlier
focusedfixturepass27.349s. FINAL245Python tests PASS NOskips178.314s inclactual
stagedLinux/Windows-under-WineonefilesGUI/resources/embeddedbridge,compiled
legacy/modes3IPCworkers/TCPUDP andisolatedreadonlyDocker. All6Lua mocksPASS.
Initial243suitehadONLYtest_container UDPportcollisionErrno98 BEFOREcontainer
start; addedbounded16pairedportselection/contextcleanup +2mockregressions in
test_container.py. Focused3Docker/porttestsPASS4.060s; full245rerunaboveclean.
Productionserver/networkcodeunchanged. No leakcheck/performance/gameclaim.
Noactualgameexecution/Rankfix. Onlyinstalledmoddelta scripts/service_trace.dll
underWin64/Mods/SzeroLAN orinstaller-detectedWin64/ue4ss/Mods variant.
OnefreshRanked-entrycaptureONLYwillidentifyfailurebranch; noidenticaloldbuild/
serverlogs/allmenustest/accountchange needed. Normalclosedgameuninstall/reinstall
OURmodwithupdatedZIPlauncher. NoServer/protocol/save/configchange.
REAoriginalbound/closed; substantiveboundedreadonlyretainedGhidra+objdump,
notcoldREAdecompile/runtimeinstrumentation. Originalhashunchanged; newwrappers
192..240Bstackmeasured, notwholeDLLstackbound. NewactualonefilesSTAGEDONLY
.build/desktop andfrozenDLL/Lua/licensepayloadsverified; existingdistlaunchers
NOTupdated. Noexternalinstalledgame/prefix/liveDockermutation/gitcommit.
FinalArenaZIP9e847428055b6c3691e7975df0115b96307244ab5bcfcb26030e90a1122ad6a8;
fulltools162entriesZIP453117c4a85f4d0d04ad1c4d5b8c087e2895b79bc682a3e95998884985fb5108.
Manifests/archivepayloadsverified. NewstagedLinux6dfc3e137ccffcd09b407c3cdf3bf99abc9a155ad93d91697860ea3a93094250;
Windows1c43f1f1a8b55d402a31fa08785338a3a0b0c53e40d0d7c453c48a3a0e9bff0a.
CurrentdistrootlaunchersobservedmatchingPREVIOUSZIPe75c78c7.../dd337cbd...,
notthisbuild; dist/desktopstill7a81918b.../66e9b3ec.... DoNOTrestore/overwrite
theseexternalchangesbasedonhistoricalhashes; thisturnbuildsstagedoutside dist.


LATEST a696 inner-service investigation (2026-10-25): supplied traceREADONLY
153138bcfbd5cd3689597b0924a2ed779ec2932f51e27de893749ff9c94dbd1b.
27completecalls,14service_login57C80000,8outererrors,mask8success. Actualmask32
maintenancecategory2 propagatesloginerror; noUIclicklabels/fiberparentproof.
Footerrestored1/inflight0/io_ok1; workingnativeDLLmodes3unchanged. NO Rank/card/
Shopfixyet. Newreport analysis/runtime-a696-service-login-2026-10-25.md.

DeeperreadonlyretainedGhidraPE.pdata bodies +originalbytes recoverprovider
1458f19f0 tagged1error/+8 vs2OWNEDBLOB(noerrorat+8). 145acf6a0 errorreturns
BEFORE145ad98c0/backend145ad9b00; providerfailurecanmimicHTTPfailure. Backend
145ad2820→145ad2760;145a9eee0 invokesresponse145ad0d20→145ab0a50 parser.
Responseincludes session_code/rank_match_info_list/player_card/followlist/
penalties/maintenance notices andservicecachepopulation, notjuststatus0.
StaticfieldnamesNOTverifiedLANschema/defaults. No ticketforgery/forcedsuccess/
cachedstringwrite/maintenanceflagclear; needownserverbackedservicecontracts.
New4analysis/native-service-login-{deep,request,response,schema}-2026-10-25-
trace.txt generatedselectedstaticbodies, noactualgameexecution/globalanalysis.

Optionaltraceupdated ONLY service_trace.c/DLL +fixturetests/docs. Schema3,
7wrappers(previous4 +provider4args/backend8args/response3args), SHA+7prefix
guards,512events/5min/knownthread unchanged. code_valid=false zeroisplaceholder
NOTsuccess; providerblobNEVERread/logged. Sameoriginalargs/RAX/LastError.
Existingendpointstop/pinnedfibertrampolines retained. TestsdistinguishIDENTICAL
outer57C8fromproviderfailurebeforebackend andafterprovider-successbackendparse.
All6nativefixturemodes/productionunknownEXErefusalpass22.982s underDISPOSABLE
Wine. NativehelperSHAa908bee4917af2ddb7defaa18391ed54f483ae3311551684d1d6d173a15d5cab.
Bothstagedonefilesactualresourceinspection confirmsnewtraceandEXACTold
native_search.dll10af5494e201ff9a24df05ca3ead8a23d24aecafe07471f3d18986dd67df1d3f
andnative_search.lua. InstalledmoddeltaONLY scripts/service_trace.dll at
Win64/Mods/SzeroLAN orinstaller-detectedWin64/ue4ss/Mods/SzeroLAN. Normal
closedgameuninstall/reinstallOURmod; no serverupdate. Noexternalgame/save/
prefix/liveDockermutation. Buildstaging .build/desktop, NEVERdistlaunchers.
FINAL243Python tests PASS NOskips174.869s withactualstagedLinux/Windows-under-
WineonefilesGUI/embeddedbridge,compiledlegacy/modes3IPCworkers/realTCPUDP and
isolatedreadonlyDockerfixture. All6Lua mocksPASS (initialinvocationusedwrong
cwd, thentypednonexistenttest_session_probe; correctedtest_*.lua passesall6).
Noactualgame/nativeWindowsacceptance/newRankfixclaim. New7wrapperframes
112..176B measuredwithWin64-fstack-usage, notwholeDLLstackbound. REAoriginal
boundandclosed; no newcoldREAdecompile/runtimeclaim. OriginalShippingSHA
unchanged. No gitcommit/staging/push/reset.
Fulltools162entriesZIP72e5eceb3537efdd603ee901551f0175fb295a85bbe4a01989f0799775580fc0;
ArenaZIP9ec10ac3a5f17f4cb0e7adae30e489f94fe15417f76b3877a8f5bdfe733c27a9.
OnlyZIPs/checksumsupdatedindist;ALL4existingroot/desktoplaunchershashverified
UNCHANGED7a81918b...(Linux)/66e9b3ec...(Windows). Newstagedonly .build/desktop
Linuxe75c78c7bac195315a6b0a39158faaad67bf2f26ebf38c7d2a5a390c6d3cc4e2;
Windowsdd337cbd0425a9d2abb2976aed6556efb88c90e55b2e68d459b133a45d406c7e.
BothactualfrozenresourceidentitiesandfullZIPpayloadidentitiesverified.
Nexttest freshgameoptionalRecordonlinechecks→Ranked/cards/Shop→new
native_service_trace_*.jsonl; no identicaloldtrace/serverlogrequestneeded.

RELEASE POLICY (2026-10-25): user requests future deliveries ONLY as the full
package ZIP, not updated standalone Windows/Linux launchers in dist. Preserve
existing dist launchers (including dist/desktop); do not copy new binaries there
or delete old ones. Stage both platform builds in .build/desktop (gitignored),
then build_release.py packages dist/SzeroLAN-Arena.zip plus checksum. No new
binary build or release archive was produced for this policy-only change.

LATEST optional online-service trace (2026-10-25): userasksimplementtargeted
Ranked-entrytrace andNOWalso57C80000 own/opponentplayercards(lobby/mainmenu),
Shop&Customize. SAMECODEdoesNOTproveSAMEproducer; NONEofthesefeaturesfixed
thisturn. NEWREADYdiagnosticfornextusergamerun, NOactualgameexecutionhere.
NativeQuickmatch/lobbyproviderDLLmodes3EXACTunchangedSHA
10af5494e201ff9a24df05ca3ead8a23d24aecafe07471f3d18986dd67df1d3f.

DeliveredNEWoptionalservice_trace.dll, modifiednative_search.lua isolatedpcall,
strictdefaultfalse launch_options.service_trace +UIcheckbox'Record online
checks(5mindiagnostic)'. SavesONLYLaunchGame withallotherfields/optionalINI
BEFOREpreflight/bridge/gameprocess; oldautodebounce/closeflushNOTreintroduced.
Flagoffexplicitlysetsenv0, helperNOTloaded. EnabledlaunchverifiesinstalledLua
andtraceragainstbundle; missing/outdatedfilescancelbeforeprocesscreation.
Gamesclosed→updatedlauncher→uninstall/reinstallOURArenaMod todeploytheseTWO
gamefolderdeltasONLY: Win64/Mods/SzeroLAN/scripts/native_search.lua andNEW
service_trace.dll (orinstaller-detectedWin64/ue4ss/Mods/... variant). Normal
receipts/backups; noEXE/PAK/loader/othermod/save/account/auth/readinesschange,
noserver/protocol/restartchange. Externalinstalledgamesnotmodifiedbydevwork.

ProbeEXACToriginalSHA+4runtime16Bprefixguard (independentlycomparedoriginal).
FourWin64scalarABIwrappers:145a7e7c0/6args/checkmaskR8/plain40+0;
1458b1e90/4args/TAGGED48tag+0/code+8;145ad9740/6args/plain40+0;
145ada640/9args/categoryarg6/plain40+0. Allargs/originalRAX/borrowedoutputs/
LastErrorpreserved; noforcedsuccess/flags/identity/tickets/nativecallbackguess.
TemporaryIN-MEMORYnativeentrydetoursareUSED, NOTdiskpatches. PrivateSTATIC
unmodifiedofficialMinHookv1.3.4commitc3fcafdc10146beb5919319d0683e44e3c30d537;
source/BSDnotices +vendor/MinHook-LICENSE.txt bundled. Nodownload/installfor
players. Workerhashes/installs/logs/disables; mainthreadboundedimmutable512ring.
Wrapperframes128/112/128/160B measuredbeforefinalnonframe-changingedits.
KnownGAMEthreadONLY, boundedrecordsNOTallAPIs/threads/fullpcap; candidate_parent
explicitlyINFERREDsame-threadcorrelation, notfiberownership. Nativecallmasks
areOBSERVEDdata, doNOTequatecookedRanked16withinternal32/64blindly.

Logscriptfolder/native_service_trace_<launch-id>.jsonl; LuaUE4SSprintsfullpath.
TestRanked→owncard→opponentcard→Shop&Customize within5minutes; noteorder/times.
Neednewtracefile(+UE4SSifmissing/nomarkerready), NOTidenticaloldserverlogs.
Capturestops5min/512/logfailure orseeninstanceendpointdisappearingonbridge
cleanup(includinglauncherEOF/kill). Owninstalledprefixcheckedbeforerestore;
stopped.restored reportsactualdisableoutcome. NEVERRemoveHook/uninitialize/
freetrampolines: suspendednativefibersmustresumevalidcode. Disablefailure
leavespinnedpass-throughwrappersnotexceptiontraps. Footerinflight/lateuncaptured
returns/unreadabledataareINCOMPLETEevidence, notnativeerrors/success. No raw
pointers/IDs/tickets/packetbodieslogged. Freshgamerequiredforanothercapture.

HardwareprototypesDISCARDED/NOTshipped: externaldebuggerfailedforceddeathand
normalWinecleanup; inprocesshardwaretestsdeliveredZERO DR6/DR7contexts/current
query, soownershipcouldnotbesafelyverified. Nofailedprototypeintoproduction,
andthisisNOTevidencethatWinecausesuser57C80000. FinalMinHookfixturepasses
actualWin64syntheticargument1..9/distinctRAX123/456/789/987/output/tag/LastError,
unrelatedexceptionpassthrough, otherthreadforwarding(norecord), original32B
instructionrestore, eventcap512whileALL100callsrun, endpointstop, andREAL
Windowsfiberpausedinsideoriginalwithwrapperinflight1 thenresumedUNCHANGED
AFTERdisable. ActualPRODUCTIONDLLonunknownEXEhashrefusesBEFOREanyhook.
Focused27Python tests pass22.781s; WindowsPython/Tk26tests pass2.889s under
DISPOSABLEWine. All6Lua mockcontracts pass, includingoptionalprobefailure
isolation. FINAL243Python tests PASS NOskips176.107s, actualcompiledlegacy/v3
workers/loopbackTCPUDP, bothrebuiltonefileGUI/resources/embeddedbridges and
isolatedreadonlyDockerfixture. InitialfullrunhadONLYoutdatedinstallerexpected
18vs19files (newDLL); correctedtestexplicitlyassertsnewhelper. Oneintermediate
test-onlyindentationmistakewasfixed+py_compileverifiedanditsownedtestrun
interrupted/restarted; finalcleanfullrunabove. Synthetic!=actualgame/nativeWindows.

REAoriginalboundandclosed; substantiveoriginalselecteddecompfromretained
earliertraces+neworiginalprefixverification, NOcoldREAdecompile/runtimeclaim.
Reportanalysis/service-trace-implementation-2026-10-25.md andarchiveverifier
analysis/scripts/verify_frozen_service_trace.py. BothACTUALonefilearchives
independentlyreadbackEXACTDLLs/Lua/MinHooklicense; no.su/stutterpayloadadded.
TracerSHAec472148d909eb4acf44d6044743f456b09f3bdb4ba70a292371202da519b2aa;
Linuxonefile7a81918bc0cec251cb0cc09325eddea273a51ab627656af34f79080c22ae87a8;
Windows66e9b3ec85c08cf45d4e32065ac88db273c6573ce5207ce550b21450ffd9618f.
dist/rootcopiesidenticaldesktop. ArenaZIP64097981b08a1593c988ba9c950842c75862e05d4f8ebbd61a9aecd300675986;
fulltools162entries/2dba5d0b98a8813cac5879b6b0c794105247d2126b281cd94fd9865fdc35701a.
Manifests/archivepayloadsverified. No gitstage/commit/push/reset.

LATEST launcher launch-only save (2026-10-25): user explicitlyrequestsALLUI
settingssaveONLaunchGame, NOTinput/close, andexistingWin64/steam_emu.ini
UserName=syncBEFOREgameprocess. Implementedsetup_launcher.py: tracesnowonly
preview/unsavedstatus; nodebouncetimer/autosave/closeflush/manualsavehandler.
Folderselection/modinstall doNOTsaveUIdrafts; selection/runtimeinmemoryuntil
Launch. InstallerstillcreatesnormaldefaultJSONifmissing. launch→save_fields
(gameJSON→optionalINI→userpreferences) finishesBEFOREpreflight/bridge/game
Popen. Anysaveerrorcancelspreflight/ALLprocessstarts; individualatomicwrites,
NOTmultifiletransaction (earlierfilemayalreadysaveonlaterfailure). Allnormal
connection/display/resolution/Wineoptionsandlastfolderrestorepreserved.

OptionalINIexactpath game/SparkingZERO/Binaries/Win64/steam_emu.ini, ONLYexisting
exactUserName=linesreplacedwithvalidatedtrimmedUIplayername. Missingfile/key
NOTcreated; comments/indenteddifferentkeys/otherfields/BOM/CRLFpreserved.
UTF8/BOMUTF16LE/BE/CP1252; invalid/unrepresentable/NUL/oversize>1MiB/symlink
refuse. Firstchangecreatesexclusive steam_emu.ini.szero-name.bak originalcopy,
neveroverwritesbackup; checksoriginalunchangedbeforeindividualatomicreplace.
Noaccount/auth/ownershipsettingschanged. ExistingnativeDLLmodes3EXACTunchanged,
SHA10af5494e201ff9a24df05ca3ead8a23d24aecafe07471f3d18986dd67df1d3f.
OriginalShippinghashreverifiedunchanged. Noexternalgame/prefix/liveDocker/save
mutation. RankedNOTfixed/requestthisturnonlyasksnextstep: scopedclienttraceof
checkmaskandactualresultatservice-login/maintenanceboundariesBEFORELANadapter,
thenrankwindow/search/continuation. Existingserverlogscannotrecoverthosecalls.

NewtestsINIencoding/missing/duplicate/exactline/backup/failure, GUIeditwait>
old650ms/closeNOwrites/reopen, launchPopenassertsALLsavedfirst, INIfailure
NOpreflight/Popen. Focused26tests passWindowsPython3.13underDISPOSABLEWine;
initial25Linuxfocusedtests passafterXvfbsocketapproval. FINAL242Python tests
passNOskips149.752s, including26focusedtests, bothactualonefileGUI/resources/
embeddedbridges, actualcompilednativeworkers/loopbackTCPUDP andisolatedreadonly
Dockerfixture. WindowsunderWine, NOTnativeWindows/gameplayacceptanceclaim.
SandboxinitialXvfb/Winefailedlocalbinding; rerunwithapprovedescalationworks,
NOTtestfailureshidden. Bothactualonefilesrebuilt, nopythoninstallneeded.
LinuxSHA42e82a44f46680a2eaf64d2674719884594c0fb647f2f3ea703fb83c5bf8bbc6;
WindowsSHAd43661159ff3113cee35d42a1bd15280092a968bee769dcbef3facfa3c9b20fd.
dist/desktopandrootcopiesidentical. ArenaZIP84696b9c0f2e1650adb18f91669e36bdf16b45760f28d56ecd680cc4cb4e5493;
145entryfulltoolsZIPebf75b8c79d960897620c25c134ed8c59f966b16a82fd1d32464080a9b34a48e.
Manifests/archivepayloadcheckpasses. Changedsetup_launcher.py,2testmodules,
README/DEPLOYMENT/build_release START-HERE,generateddistributions,AGENTS.
NoDLL/server/protocolchange/newgameplayclaim; nonewmodpatchrequiredifmodes3
alreadyinstalled. Useupdatedlauncherexecutable; oldsettingsmigratereadonopen.

LATEST Ranked entry research (2026-10-25): user confirms57C80000 IMMEDIATELY
on clickingRanked, beforefighters/settings/search. NO Rankfix/newrelease this
turn. Exact cooked MainMenuListMenuData Rankedbutton ST_UI_MAINMENU_BT_0015
bNeedOnline1/OnlineCheckMode16 CheckMaintenanceRankMatch; embeddedsettingssame,
RankMatch_UserWindow referenced. Rawcooked16 != internalmask! Originalenum
145a19650 jumptable mapsinternal32 toRanklabel145a19778,64anothercategory.
1427aa9e0 shiftsincomingbyte2 butrawcookedcallconversionNOTestablished; doNOT
patch16/64blindly. Checktask145a44940→145a23a10(64B,vptr147ba5108)→exec
145a6a3e0→145a7e7c0; internalbit5/category2 calls145ada640, whichFIRSTcalls
145ad9740→uncached145ad94e0→145a9e6a0→145acf6a0(service-login/provider+40)
beforemaintenance. Separateoriginalservicecontract NOTimplementedbyLANsession
relay. ThisisSTATICchain, NOT actualobserved57C8producer. OriginalServiceError
nameconfirmed; user+1c0fullcheckfailurewould57C10621, NOT57C80000. Preserve
genuineplatformchecks; noflagclear/forcedsuccess/faketicket/Quickmatchrelabel.
RankwindowexportFAILED CanvasPanelschema, nocompleterankdatacontractrecovered.
Need scopedcheckinput/resultboundaryobservation+LANserviceadapter, notidentical
serverlogs. Report analysis/ranked-entry-service-boundary-2026-10-25.md andsix
native-ranked-*-tracefiles. Newanalysis-onlyfind_rel32_calls.py exactSHAE8/E9
BYTEcandidates (notinstructionproof), syntaxcheck/scanspass. REAboundoriginal
andclosed; substantiveboundedreadonlyGhidra+objdump, nocoldREAdecompile/runtime
claim. Original/helperhashesunchanged; noDLL/launcher/server/config/save/external
install/Dockermutation, nonewfullsuite/gameexecution. Modes3baselinepreserved.

LATEST Modes3/private slots + Windows acc74 (2026-10-25). User reports ordinary
lobby WORKS; private-slots>0 CREATE fails00000413, ranked57C80000. Docker logs
read-only from525a50226147/server-server-1 show prior valid roomdc201463 create,
two-member join and UDP forwards, update+leave. Linux9daa22:20:18UTC/00:20:18
Berlin and suppliedWindowsacc7422:25:33UTC/00:25:33Berlin independently show
OUR CREATE capture_refused stream_unsupported, exactvtableRVA0x6d36f80; this
refusal is BEFORE RPC. Windows thread11888 matches, no quarantine. Its
last_request39/create_calls1 refer PRIOR successful leave/create, NOT refused
create. Windows searches0/native_search_request0. Later bridge connectionclose
00:31:06doesNOTexplain earlier refusal. Report analysis/modes3-private-slots-
and-ranked-2026-10-25.md. Do not ask another identical oldbuild test for THIS.

Implemented exact40B BORROWED VIEW146d36f80 capture, append diagnosticlayout6,
not blanket unknownstream acceptance. Original145923a50 alloc40/zero+8/+10/
+18/+20;1429146a0 nonemptyviewrd+10,size+18,data+20. Originalvtable+80readrd,
+88zero,+90/+98readsize,+280readdata,+2b0zero independentlyconfirmed. Capture
reads40Bprefix+boundedbytes, wr0, preservesrd; existing4096B/readability/
overflow/cursor/failureatomic guards retained, no nativecalls/destructors/
inputwrites. Both empty-present andnonemptyviews supported. No wire/server/
visibility/filter/capacity/identity/auth/readiness changes. Working0/0x28/
scoped0x200 join unchanged. Actual PRIVATE-SLOT GAME ACCEPTANCE NOT yet proven.

Native revisionnative-session-v3-development-modes3; DLL SHA256
10af5494e201ff9a24df05ca3ead8a23d24aecafe07471f3d18986dd67df1d3f.
Only installedgame deltafromrooms2: SparkingZERO/Binaries/Win64/Mods/SzeroLAN/
scripts/native_search.dll (or detectedWin64/ue4ss/Mods). Gamesclosed→updated
launcher→uninstall/reinstallOURmod onALLclients. No serverrestart/update needed.
OriginalEXE/PAK/loader/othermods/config/saves unchanged. External installs not
patched bydevelopment. OriginalShipping/bothSaveGamehashes reverified unchanged.

New exact40B isolated-region unitfixture tests payload/empty/reconstruction,
inputpreservation, canaries/failureatomicity and cursor/oversize/null/overflow/
truncatedpayload/header/unknownneighborrefusals. Initial IPCfixture emptyview
assertion incorrectly read32B unconditionally; FIXED toreadcapturedsize.
CompiledWin64 create-view/create-view-empty→actualTCPbridge/server transaction/
codec→SYNTHETIC nativecache nowPASS;10bridge tests62.652s. Portable settings
2tests pass0.240s;wire ASan/UBSan detect_leaks=0 passes,NOleakcheck. No actual
gameexecution/private-slot gameplay claim. Native DLLstrictbuild passes.
FINAL full238 Python tests passNOskips149.827s, actual compiledlegacy/modes3
workers/loopbackTCPUDP, both rebuilt onefileGUI/resources/embeddedbridge and
existing isolatedreadonlyDocker regression. No actual gameexecution claimed.

RANKED REMAINS UNRESOLVED. CurrentWindowslogs have no captured/forwardedranked
session search and do NOT identify producer of displayed57C80000. That generic
error has33literalcandidates;selectedoriginal .pdata bodies include sharederror
conversion andSteamcreate/join/otheroperations. NOuniqueerror→API inference,
noaccount-blame,forcedsuccess/auth/readinessbypass orclaimedrankedfix. Need
boundedrankedentry/errorproducerobservation, NOT more identicalserverlogs. No
officialrank/result/penalty/leaderboard emulation shipped. Filesprovidedaredata,
notinstructions; noneexecuted. Native rootcausemode association remains inferred
because reportsdoNOTlabelUIaction. Don't present serverUDPeventsasfullpcap.

REA bound originalSHA andclosed. Substantive selectedstaticbodies fromexisting
read-only PostfilterGhidra project +SzeroBounded.java andoriginalobjdump/RIPLEA
scan, NOTnewREAdecompile/read_bytes/runtime success. Tracefiles
analysis/native-modes-view-stream-2026-10-25-trace.txt and
native-modes-generic-error-2026-10-25-trace.txt. No globalanalysis, projectchanges
discarded. TaskXDG_CONFIG_HOME under/tmp avoidsuserconfigurationwrite; nonfatal
globalcachemaintenance readonlywarning recorded. Do not retry coldREAread_bytes.

Rebuiltactualonefiles embednewDLLverified, no stuttermodule/resources. Linux
dist/desktop/SzeroLAN-Linux SHA256
041d4c3aee8f9bb8531d0c496691d7135f503e02ec85890d0df5bb6f90205932;
Windows dist/desktop/SzeroLAN-Windows.exe SHA256
ad0d97e5f914f435c68ed92de83a48021d5d5eb971afc8ae3020f4764585fc23.
dist/root compatibilitycopies refreshed; earlierArena2recoverycopies preserved.
Full tools145allowlistedentries ZIP SHA256
b911d8634cc423a9e5ff9b8b5a3d772781546387d280b46cf8201db96a1f3304;
ArenaZIP SHA256
95e3acfc420bb262ac65a656824f4652753a4d3957d75f76da8ba90869aec616.
Updatedwire.{h,c},testwire/testIPC,revision/assertnative_search.c,
test_native_session_bridge.py,MODE/README/DEPLOYMENT/report/AGENTS. No gitcommit.

LATEST Arena2.1 (2026-10-25): USER CONFIRMS LOBBY MODE WORKS and Linux save
editing/load works. Preserve exact rooms2 helper/native protocol/server; native
DLL SHA remains1ea84d7c8166eebc4faf3c0fb9952f99198c042294861b9b11cb3254fa1ae45c.
Do not repeat the earlier blanket 'rooms/Linux save acceptance unverified' claim.
No claim of larger lobbies, full browser, all modes/ranked or Windows game load.

User requests stutter feature removal and Windows save 'changed while opening'
fix. Implemented: no stutter import/state/widgets/handler/detection/renderer
Wine overrides; build_desktop now explicit UE4SS vendor files, not whole vendor;
both actual executables verified contain NO stutter module/resources/render DLLs.
Full tools allowlist removes8stutter entries (145remaining). Historical local
source/resources remain only for recovery, not imported/distributed. No already-
installed rendering files silently removed. With games CLOSED use OLD launcher's
checkbox to uninstall/restore managed originals BEFORE replacing it. Prior exact
Arena2 launchers retained separately at dist/recovery/SzeroLAN-Arena2-Linux and
SzeroLAN-Arena2-Windows.exe for that recovery ONLY, excluded from new archives.
Receipt/backups stay Win64/SzeroStutter-install.json + SzeroStutter-backups/.

Windows root cause reproduced READ-ONLY under same WindowsPython3.13.17 Wine
build runtime: lstat/fstat dev3967673800,ino56624713,size98770,mtime_ns
1792845660271820100 identical; ctime_ns1792845660271820100 vs1792845660272161600.
Old _identity cross-API comparison falsely refused same unchanged file.
savegame._same_open_file compares dev/ino/size/mtime across APIs ONLY on Windows;
Linux retains full comparison. Full5field comparisons still independently run
descriptor-before/after AND path-before/after. Added descriptor regular/single-
link check. Hash/fresh plan/confirmation/stopped-game/backup/atomicwrite preserved.
No global ctime omission or content/race bypass. New tests reject changes in any
shared field and actual descriptor ctime change during read; allow stable cross-
API ctime mismatch. Report analysis/arena2.1-windows-save-and-stutter-removal-
2026-10-25.md. Windows game loading remains user-validation; 7Windows-runtime
tests on DISPOSABLE COPIES pass2.081s, including character/earned unlock,
idempotence, confirmation/running/stale/forged refusal and replace-failure backup.
Linux11save tests pass1.735s;14GUI pass0.471s;8settings tests pass1.396s.
FINAL full237 Python tests pass,NO skips,151.825s: actual rebuilt Linux and
Windows-under-Wine onefiles/UI/codec/embedded-bridge cleanup, compiled native
workers and existing isolated Docker/TCP/UDP fixtures. Old local stutter recovery
tests still run in workspace but module/resources are excluded from distributions.
Initial unprivileged GUI attempt could not access display, corrected withXvfb.

Rebuilt onefiles: Linux SHA256
a9341b72f2d07d893a17e8ad74e804318a3654c6a79b1176b8b51383d4ae6ecb;
Windows SHA256
c66cb032b2de7a1acc7338d64b431c2324fd7d761722c3d093fcaca66ccaee32.
dist/desktop authoritative, dist/root copies identical. Native helper unchanged
verified inside both actual archives. Source and archive manifest identity pass:
full tools145entries SHA256
bdef41dce6f73834b69797376967eae01b358866c2cb7f63df37a07bb8c62b12;
Arena ZIP SHA256
5b0eaa65b62958166fd0149acb4b340447957d09bc345fcbeca6f33dbcd5a641.
No server/image/config/native/installed-game changes; no repatch/server restart
needed. Original supplied Main/System SHA256 unchanged. No game/PAK/originalEXE
or external Wine prefix modified, no gitcommit. Latest source changes ONLY:
setup_launcher.py,launcher_theme.py,launcher_support.py,desktop.py,
build_desktop.py,build_bundle.py,build_release.py,savegame.py,save/UItests,
README/DEPLOYMENT/MODES and this handoff/report; generated launchers/archives.

LATEST IMPLEMENTED Arena2 / rooms2 (2026-10-24). Supersedes the research-only
save/no-unlock and no-room-adapter statements below. User requested launcher
cleanup, supplied reversible Stutter Free install, earned unlocks and room fix.
Read analysis/arena2-implementation-2026-10-24.md + lan/DEPLOYMENT.md first.

Launcher: ARENA branding; original four-star PNG/window/Windows ICO; separate
Select Game Folder (NO installation) and Install/Uninstall Arena Mod; other
options disabled until valid selection; restores previous folder/settings and
autosaves valid edits. DX11/skip-splash controls AND old config keys/arguments
removed. Display/resolution/Wine settings retained. Unknown JSON fields retained.
New game_process.py checks all game instances before destructive UI actions.
Uninstall backs up/removes ONLY receipt-owned unchanged SzeroLAN mod files,
disables own mods.txt entry, preserves shared loader/other mods/config/saves.
Reinstall clears old uninstall marker. Close games; uninstall/reinstall our mod
with the new executable on EACH client to update; server protocol unchanged.

Stutter: five user-supplied hash-pinned files embedded under lan/vendor/stutter
in both executables; copies to SparkingZERO/Binaries/Win64/d3d11.dll,d3d12.dll,
dxgi.dll,dxvk.conf,D3D12/d3d12core.dll. stutter_mod.py detects absent/managed/
exact-manual/conflict; confirmation, original backups, write-ahead pending
receipt, exact hash/type/link guards and reversible restore. Receipt at Win64/
SzeroStutter-install.json, backups SzeroStutter-backups/<uuid>/. Exact manual
files have no pre-install backup. No DLL execution/performance guarantee;
upstream version/license review required before public redistribution. Supplied
root folder ignored; only the explicit five resources/provenance are bundled.

Save editor NOW shipped: savegame.py + explicit save_catalog.py. Verified
seed0 xorshift128/interleavedMD5 +02/Zstandard; native tagged DataVersion12
MainGameSaveData only. Characters action and Earned Content action (characters,
character items, BattleBGM/BGM ONLY; NOT all cosmetics/stages/titles/story/DLC).
Eligibility from original asset Default/Shop allowlist AND DLC flag0; unknown
keys excluded. Change bool0→1 + Lock→New enum, fix enum/map sizes; unrelated raw
bytes preserved. Supplied copy previews62characters or865total (62+661+45+97).
Confirmation, known-stopped callback checks, exclusive lock, fresh exact plan/
fingerprint, no symlink/junction/hardlink/read-only, verified private sibling
backup, verified temp, atomic replacement. Backup .SzeroLAN-backup-*.bak beside
selected file. No supplied original modified. Exact compression-envelope
roundtrip and recompressed structural/idempotence/copy-write tests pass;
ACTUAL EDITED-SAVE GAME LOAD STILL UNVERIFIED. Keep backup; do not call this a
proven universal unlock-everything. No third-party full save/account/DLC edit.

Rooms2: native_lan_userinfo.{h,c} + provider.inc scopes known validated LAN
principals away from Steam user+98 numeric parser; real platform IDs delegate
original, mixed input deepcopies native-owned real strings (original can move/
compact/destroy), all-LAN moves existing native record vector. Exact 20-slot
Steam user vptr clone changes ONLY +98 after hash/service/thread/slot validation.
Known principals only from validated owned/projected server DTO; lifecycle frame
clear removes views. No global user+200/Steam identity/auth/ownership change.
Exact0x200 admitted ONLY ready adapter;0/0x28 unchanged; other flags refuse.
Native DLL revision native-session-v3-development-rooms2, SHA256
1ea84d7c8166eebc4faf3c0fb9952f99198c042294861b9b11cb3254fa1ae45c.
ONLY installed native-runtime delta from rooms1 is Mods/SzeroLAN/scripts/
native_search.dll under Win64 or detected Win64/ue4ss. No originalEXE/PAK patch.
Portable namespace/ownership/heap-move tests + exact publication/clear/0x200
guard tests pass; real compiled 0x28 two-client bridge retained. NO ACTUAL
ROOM JOIN/COMBAT, larger lobby/multiresult/private-code/ranked completion claim.

Parent liveness: GUI holds private stdin pipe for embedded bridge. Close/kill/
crash closes writer→EOF normal TCP/native cleanup, including frozen --windowed
Windows GetStdHandle fallback. Catchable signals stop bridge; no fabricated
disconnect packet. OS/network failure falls back to heartbeat timeout. Game not
killed. Actual Linux and Windows-under-Wine onefiles verified EOF/server cleanup.

Verification: full234 Python tests, NO skips,143.300s (compiled legacy/v3 workers,
actual Linux+Windows-under-Wine onefiles, Docker real TCP/UDP, GUI, save copies).
After final backup-permission/installer marker rebuild:9save tests pass1.433s;
actual final onefiles2tests pass12.421s;14GUI tests pass0.376s including new
disabled-controls/confirmation test. All6Lua mocks pass. StrictWin64DLL build
and publication test pass. New portable userinfo ASan/UBSan detect_leaks=0 pass,
NO leakcheck. Portable userinfo stack<=512 passes. Whole legacy native_search.c
strict512 stack check does NOT pass (existing worker/hash/lifecycle large frames);
do NOT claim all native frames bounded512. No actual game execution this turn.
Original Shipping and BOTH original save SHA256 reverified unchanged.
No external installed game/systemWineprefix/livecontainer changes; no gitcommit.

Artifacts rebuilt: Linux x86-64/glibc2.35+ dist/desktop/SzeroLAN-Linux SHA256
b170fed996b79f972eaaefd015ab0fd3cf78f3f52b4440bb4869146ba39f9a1d;
Windows dist/desktop/SzeroLAN-Windows.exe SHA256
b1b05f829b7e390751277295c8d1e7f46daf618ad88e586f01aa3d40ec219eca.
Generated dist/root same-name compatibility copies refreshed identically.
Both executable embedded native DLL hashes match rooms2. End users need no
Python; Linux still needs Wine. Server image rebuilt without restart: local ID
sha256:f50cff155b8b11c17ee314df25867b246786e9945021a416049c4f61d0811007;
dist/SzeroLAN-server.tar.gz SHA256
a118589fa618503bd2fe6f36ff7efe1d933926b2aa8e206ec72a9638220de3d1.
Full tools153allowlistedentries ZIP SHA256
74fa63a3f37088e2fcfe16cd42db4479847eb4a7cca2bc7e6bedbd976ea6faa8;
ArenaZIP SHA256
568bd3308f4b3e962f2450449801804a57095cf9ff455f7903721075a53179f0.
Source+archive manifests and payload identities verified. Latest production
changes include setup_launcher,launcher_theme/support,installer,ingame_client,
desktop,build_desktop/icon,build deps/allowlist,game_process,lifecycle,stutter_mod,
savegame/catalog,native_search/provider/frames,userinfo. Full file ledger in
DEPLOYMENT and implementation report. No live REA runtime claim; original-body
evidence retained in analysis/*usercheck*/*ownership-join*/*room-join-0x200*.

LATEST diagnostics/save-codec (2026-10-24): actualDocker server-server-1 logs
pulledread-only, pluscurrentLinuxexternal038f report. Roomscreateworksuserreport;
latest14:21:55UTC/16:21:55CESTrpc344returnsPlayerroomed97311..., result1,
inspection1/copy0/numeric1/self0. Nextrecordedreport14:21:56UTC proves OUR
join_flags_refused flags512(0x200)/code1043 beforeIPC. join_calls1belongsprior
quickmatch, notthisroom. NeedNOmorelogs/identicaltestforTHISrefusal. Earlier
rpc274compat20006vs20004 mississeparate; doNOTrelaxfiltersorassignsemanticnames.
Report analysis/runtime-rooms1-join-refusal-2026-10-24.md +native-join-0x200-
provider-audit-2026-10-24.md. AtproviderLOCALonlybit7,SteamignoresR9, BUTbit9
consumedupstream1459b2d30 ownerprimaryuserinfo check. 1458def80→1458d3700→
1458da040 removesrealself/cachedIDs,1458da730 sendsunmatchedIDs touser+98.
Steam+98=1458fa310 parsesIDs1459425a0 andcallsSteamFriends APIs. Cachehit
canavoidfallback; NOactualbreakpointtraceofthatbranch. NeedscopedLANuserinfo
adapter/contracts, notglobalflagclear/fakeSteamID/forcedsuccess. Noproduction
fixshippedthisturn. Container/clientsleftuntouched, no newgametest.

SAVEENCODINGNOWRECOVERED fortheTWO suppliedsamples: sourceanalysis-only
analysis/scripts/save_envelope_probe.py. Original145bb34f0 transform,seed0,
xorshift128 keyedbyteXOR +interleaved16B MD5; verifiedMD5 onbothfiles; inverse
encode(decode(original)) BYTEEXACT. Decodedpayload starts02+Zstandardmagic;
decompression Main9,091,775B/System191,649B, markerstringsincludeUnLockDetail/
bGamePlayUnLock/bDLCUnLock/ShopItemDataList. CharacterDataList@415isaSUBSTRING
insideKoratCharacterDataListtype, NOTverifiedmap. Mainindependentlyran
proofsuccess onbothoriginals, hashesunchanged. Thisroundtrip retainsORIGINAL
compressedpayload, NOT recompression/editedsave/gameacceptance proof. Stillno
safe mapeditor/unlockbutton/productioncodecshipped; preserveDLC/account/story/
rank/unknownfields, needtagcontainer/versionparsing, backup+confirmation and
copy-onlyrealgameloadvalidation. DoNOTrepeatold'envelopeunknown'claimbelow.
Newreportandoriginaltracesinanalysis/save-format-research-2026-10-24.md.
Proofisreadonly, printsboundedmetadata, usesoptionalsystemlibzstd viactypes,
writesneitherplaintextnorsaves. Nodistribution/DLL/config/loaderschanges.
REAopenboundoriginalSHA; rawread_bytescoldquerytimedoutafter300seconds;
substantivefindingsfromboundedread-onlyretainedGhidraPE.pdatadecomp+original
objdump, NOTsuccessfulREArawread/runtimeinstrumentation. REAtargetclosed.
No broadtestre-run needed/claimed forresearch-onlychanges.

LATEST rooms1 (2026-10-24): user requests public/private rooms with/without
quick-search, ranked and confirmed save-unlocks in launcher. RESEARCH + bounded
stream fix delivered, NOT full mode/save completion. User-confirmed fix8
Quickmatch success remains baseline; do not regress/force filters or platform
checks. New exact146d15df0/kind1 allocator-less64B prefix stream capture,
bytes+40, enum5 INLINE64. Original constructors/getters independently verified;
NOT inherently lobby-only. Unknown types/flags, size/cursor/ownership guards
unchanged. No server/wire/config/capacity/identity change. Revision
native-session-v3-development-rooms1; DLL SHA256
ebcc6349f8ff26d20de358c04b29f18abe08013c3106fdf2feff864e6c201147.
Only installed-game delta fromfix8:
SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/native_search.dll
(or detected Win64/ue4ss/Mods/SzeroLAN/scripts/native_search.dll). Normal setup
with games closed; both rebuilt standalone launchers embed it. No external
installation, original EXE/PAK/loaders/othermod/config/save modified.

Changed native_session_wire.{h,c}, test_native_session_wire.c, revision/assert
native_search.c; compiledIPC create-inline64 fixture and bridge test added.
New test_native_room_modes.py verifies existing profile2 flags&5 discovery,
hidden known-ID prepare/commit join, owner-only flag updates, opaque numeric
matching separation, partition/capacity/hostdeparture refusal. Server unchanged.
Native private room-code parser/invite mapping NOT established; API known-ID
tests do NOT prove game UI private joins. End-to-end capacity2 / one-search-
result / UDPsinglepeer remains; larger roster/spectator/multiresult requires
coordinated codec/materializer/projector/routing work, not a constant increase.
Widget settings enums and reconstructed Rank1/Quick2/Player4 must NOT be
equated with native compatibility param. Original145923850 encodes bounded
param2+145941730(0)*1000; direct145a14560 caller passesliteral1, mapping still
unknown. No ranked result/penalty/official rank emulation or gameplay claim.
See lan/MODES.md; analysis/native-lobby-mode-research-2026-10-24.md and selected
original traces. Existing search, visibility and numeric admission unchanged.

Supplied SaveGame Main98770/System5409 remain byte-identical SHA256
110e57e39f88a88acba1ba7855e0949fa8bfe437afa690634062e007b2c0279c /
c16145d3a91dd839ef4e95ea032fb3ab215ee36b7ea44397b67397f4e0715a6c.
/SaveGame/ now gitignored, never in distributions. Encoded envelope/integrity/
serialized map layout NOT recovered; no parser/editor/unlock button shipped.
SaveDataOpenAll/OpenShop shippingnative141cea190→1410fd050 are NO-OP; don't
invoke names blindly. SSUnLockDetail bGamePlayUnLock vs bDLCUnLock setters
1410fd510/+0 vs141566650/+1 are IN-MEMORY, NOT disk offsets. Earned-content
editing must preserve DLC/account/story/rank/unknown fields. Need exact codec
roundtrips, verified container/version handling, then explicit launcher
confirmation, stoppedgame, exclusive verified backup/fingerprint recheck and
atomicwrite. Never overwrite supplied originals or import a thirdparty fullsave.
See analysis/save-format-research-2026-10-24.md for recovered loader chain and
next targets. PAK key is not established save key. No save-load success claim.

Verification:198 Python tests NOskips139.239seconds; rebuiltactualcompiledv3
worker create-inline64→realTCPserver→codec→syntheticnativecache, retained
two-clientLAN0x28quickmatch, actual Linux/Windowsonefiles +readonlyDockerUDP.
All6Lua mockcontracts pass; strictWin64DLL/fixture builds pass. Focused wire
ASan/UBSan detect_leaks=0 passes, NOleakcheck. Native capture frame224B, others
<=512B. No actualgame execution/newlobby/ranked/saveacceptance claim. Original
Shipping hash reverified unchanged. Normal Docker server image/protocol stays
unchanged. Full source/player distributions rebuilt, manifests checked below.

Rooms1 artifacts: fulltools130allowlistedentries ZIP SHA256
23f8efb94c29f5db1e0c38ed878a4296aa53e17e4d7082c43278b9b3a34f4da8;
Arena ZIP SHA256
93c9da9570058435d00628dc3fe8d3bc177e20b50b0f733f27b12b604e5dc14c.
Linuxonefile SHA256
e1dbce74de47fff1dc5775df5d846d18b9d0feb4d20495a397a945f22062e08f;
Windowsonefile SHA256
4a82ff43cf57c5902cfb8d4ebc1965c922f2f106e4b6d3049da26160335cfd08.
Botharchivepayloadidentities verified; originalgame/savehashes unchanged.
REA targetclosed afterboundedanalysis. Local source changesonly; no gitcommit.

LATEST: LAN Arena desktop/Docker release (2026-10-24). USER CONFIRMS fix8
worked; preserve that native implementation. This pass changes UI/distribution,
NOT native multiplayer/protocol. Native DLL remains exact fix8 SHA256
f1978b3a38414580a93b65d437b71c2317864552045a7f16c28b48116982bacd.
Original Shipping hash reverified unchanged. No original game/PAK/save/othermod,
external installation or system Wine prefix modified by build/test work.

New modern original vector/Dragon Ball-inspired Tk UI (orange/blue/dark,4-star
orb), no extracted game art. setup_launcher.py +new launcher_theme.py and
launcher_support.py. Last game folder in user preferences, valid fields autosave
after650ms and flush on close/launch; game-root SzeroLAN.json retains connection
and launch_options. Unknown fields preserved, invalid drafts do not replace last
valid config. Reads legacy tools/setup.json; native Linux migrates Wine Z: paths.
Preferences: APPDATA/SzeroLAN/launcher.json on Windows; XDG_CONFIG_HOME/SzeroLAN/
launcher.json or ~/.config/SzeroLAN/launcher.json on Linux. Never save to onefile
extraction dir. Settings lock during active bridge, explicit DISCONNECT LAN
stops own bridge (does not kill game), then unlocks controls. No native-mode UI.

Options: optional -dx11 (off=no renderer flag), default/fullscreen/windowed/
borderless, bounded resolution presets, -nosplash. Engine hints, not performance
claims; game can override some. No fps/timing/sync/save edits. Linux Wine
executable/prefix configurable; empty preserves WINEPREFIX/~/.wine. Argv arrays,
no shell. Frozen LD_LIBRARY_PATH/Windows SetDllDirectory sanitized for external
game launch; unrelated Wine DLL overrides preserved, dwmapi=n,b requested.

desktop.py supports GUI and private --bridge entry so frozen child does not
invoke external Python. Actual onefile executable embeds bridge,Tk,loader/mod
resources. build_desktop.py +build-requirements.txt, Build-Launcher.cmd,
build-launcher.sh; per-OS artifacts, NOT universal binary. Windows builds use
Python3.13/3.12; pinned PyInstaller6.16 cannot collect Tk9zipfs on WinPython3.14,
so that combination explicitly refuses. Initial3.14 prototype failed and was
REPLACED by verified3.13.17 artifact. Build deps only in disposable /tmp prefixes.
Linux portable build via Dockerfile.launcher Ubuntu22.04 Python3.10/glibc2.35.
Current Linux binary x86-64/glibc2.35+, needs desktop/XWayland and Wine for game.
Windows build and GUI/bridge smoke under Wine, NOT native Windows/game claim.
.github/workflows/desktop-build.yml gives separate Windows/Linux builds when
repo is hosted; NO remote push/workflow run/release performed. Git remains dirty/
untracked as before; no staging/commit/reset. Scripts and artifacts documented
in lan/DEPLOYMENT.md. No new installed game files vsfix8; normal setup preserves
own backups/loader/other mods and applies existing resources only.

Server Dockerfile: pinned official Python3.12-slim-bookworm digest, exact8module
stdlib source allowlist; no game/loader files. compose.yaml publishes both
TCP/UDP27150 (SZERO_BIND_IP/SZERO_PORT optional host mapping), bind0.0.0.0 inside.
UID/GID10001, read-only root, cap_dropALL/no-new-privileges, tmpfs and named
rotating-log volume. Existing server/admission/transport source unchanged.
Start-Server.cmd/sh now Compose. No auth added: trusted LAN firewall required.
Image szero-lan-server:local ID
sha256:9b4c42cda57d27bb84f3267d6725a167b6291192674f6c1d53b53e3c873430cd.
Offline image dist/SzeroLAN-server.tar.gz SHA256
c1617647f99e537593eb7edeabc8b8cba25248a039592fa9728d778b5004f06e.
docker load -i thatfile, then compose up -d --no-build. Test containers removed;
only requested generated images/build caches/artifacts remain. Tournament port
was not taken: tests used ephemeral loopback publications.

Verification:190 Python tests,NOskips,134.678seconds, allactualcompiledlegacy/v3
workers +actualLinuxonefile(withPATHcontainingNO Python)+Windowsonefileunder
Wine GUI/resources/embeddedbridge +realnonrootreadonlyDocker2playernative
session/bidirectionalUDP +autosave/reopen/invaliddraft/argv tests. All6Lua mock
contracts pass. No actual game launched; user reports gameplay success separately.
Windows packaging tests in /tmp/szero-windows-build-6VClYK (NOT ~/.wine); native
fixtures in original disposable /tmp/szero-fix6-verify-eZSnYE. No new sanitizer/
leakcheck/native binary rebuild/REA work. UI screenshot visually inspected.

Artifacts: dist/desktop/SzeroLAN-Linux SHA256
86679a55efa29d967d0d1148dfae7f012c26e2407f3fc42cfab763addff815a7;
dist/desktop/SzeroLAN-Windows.exe SHA256
0e59de5ae85bf7235bad26215f3a4b61d149198e236f23d71da98197169fab1c.
build_release.py creates explicit minimal dist/SzeroLAN-Arena.zip containing
both executables and server/ Docker context; full source tools archive remains
build_bundle.py allowlisted. Full tools128entries SHA256
105102b9733580cca21245bcdf3d7aeaeb28fe17868f5cf00bf6650e18eb553d;
Arena release ZIP SHA256
5b58c94dc687e953cb5777d023dfd1b1d9eee1c7a96fe98a20de5b99ee9af1fd.
Both source manifests/archive payload identities and release per-file identity
verified. Standalone and offline image checksum files supplied beside artifacts.

CURRENT fix8 (2026-10-24 supplied8115): Fix7 DID separate LANprimary ingress
(38bytes, crossprimary_equal0), nativecopy0/numeric1/selfprediction0, but OUR
block_join refused observed nativeflags40(0x28) before IPC, wroteplain1043
(0x413). SuppliedMaxinatorreport3attempts/flags40/code1043,zeroacceptedjoins;
finalcachedoperation1 is subsequentCREATE, NOTjoin. Server repeatedlyreturns1
thencreate1member, NOjoin/2membercommit. Firstrecordedsample11:09:11UTC/
13:09:11CEST afterrpc40search13:09:10.999; notexactnativecalltimestamp. Only
UDPregistrationevents, notfullcapture. Playerserverbehavioralone doesNOTprove
itsnativeflagcode. NormalperoperationNativeIPCdisconnect!=serverdisconnect.

Fix8 allows EXACT0and0x28; allotherflagsstillrefuse. Originalbyteauditcaller
1458c2900ushort→R9D; LOCAL14592db10capturesR9W,ONLYbit7suppressesaddress;
0x08/0x20 ignored. Steam1459269b0neverreads incomingR9flags. No memberflag
translation/blanketmask/drop/auth/readiness/serveradmission relaxation. Bit7
staysunsupported. Evidenceanalysis/native-join-flags-0x28-fix8-trace.txt and
analysis/runtime-8115-join-flags-fix8.md. No furtherlogsneededforTHISrefusal.

Changednative_search.c +compiledIPCfixture +test_native_session_bridge.py;
LANfixture now usesactual0x28 andrequiresflags40/code0 instead ofonlyflags0.
Oldtestcoverage missedrealQuickmatchflags; refusalsnowtest0x08/0x20/0x29/
0x80/0x128/UINT32_MAX withoutputcanaries. Classic0coveragepreserved. NoPython
production/wire/configchangefromfix7. Onlygameinstalldelta:
SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/native_search.dll
(or detected Win64/ue4ss/Mods). Fullbundle/setupfreshlaunchasnormal; server
sameprotocol. Nooriginals/loaders/othermods/saves/externalinstallschanged.
Revisionnative-session-v3-development-fix8;DLLSHA256
f1978b3a38414580a93b65d437b71c2317864552045a7f16c28b48116982bacd.
Verification179Pythontests,noskips,119.486seconds; rebuiltactualcompiledlegacy/
v3workers, realTCPUDP, disposableWine/Xvfb; LAN0x28nativeguard→IPC→serverjoin
code0/2membercommit, syntheticnativefactory/cache/title only. All6Lua checks,
strictWin64DLL/fixturebuilds pass. Refused-flagcanaries include0x80. No new
sanitizer/leakcheck. OriginalShippinghashreverified unchanged. Packageidentity
Fix8distribution108allowlistedentries; archiveSHA256
08fd0d726be403c2e084b8f6d1888755d59995d4447b487231a67a85ba442adf.
Source/manifest/archivepayloadidentity verified via build_bundle.py --check.
Actualgameacceptance/channel/combat remainsUNVERIFIED; no playableclaim.

CURRENT fix7 (2026-10-24): LAN identity separation IMPLEMENTED, replacing the
diagnostic-only36b2 milestone below. Playable Quickmatch/combat still NOT proven.
Each actual TCP client UUID owns explicit38-byte szlan: principal; LAN partition
protocol4 vs classic3. HELLO4/READY4 pins principal AND two loopback ports before
hook publication; full greeting validated before state changes. Capabilities
native_lan_identity:int1 required by launcher. Startup-before-bind retry works;
disconnect/change after binding refuses until game restart (no silent identity
swap). Legacy HELLO3 remains diagnostic fixture only, no normal mode option.

Bridge translates deep-copied outgoing own primary; server validates actual
connection binding before direct/transaction writes and rejects namespace mixing.
Logical snapshots stay LAN; native_lan_identity_project validates owned codec,
canonicalIDs/members/bounds then projects ONLY own member to real local pair.
Search requires0own; create/join/refresh requires1own. Every decode path uses
provider_addresses before materialization/localization/copy/cache/diff. Raw frame
cache remains logical, unchanged polls preserve cursors. No global user+200
write/identitysetter/SteamIDforgery/filterremoval/auth/readiness bypass. Native
UUIDs/order/ownerflags/settings/opaque streams unchanged. Same-account LAN is
intended and synthetic-tests supported, not actual-game/platform-offline proof.

Bounded original audit: address-based1459ac3c0 channel bootstrap; memberUUID
getter14594a840 in channel completion/messages34/37; message39 BOTH strings
resolve memberUUIDs via14594ec60→14594b9f0, NOTaccount/persona serialization.
Owner authorization14594e5e0 checks channel handle. Refresh1458caf50 cache-only.
Postjoin1459891a0 may invoke1458ca6f0(1,0)→1458df190; downstream Steamuser+90
1458fab50→1458f9e30 enumerates existing friends with constants/indices, no LAN
IDlist passed to Steam; LAN list compared locally afterward. Platform may still
be read; all optionalprofileUI/serializers/offline startup NOT exhaustively
verified. Preserve retained+28init; normal launcher gives no connect_lobby args.
Evidence: analysis/native-lan-identity-fix7.md +7native-lan-view-*-fix7-traces.

Changed server/client tools: lan/native_search.py,ingame_client.py,szero_lan.py,
setup_launcher.py; NEW lan/lan_identity.py beside them. Full tools update on ALL
clients/server +serverrestart +freshgame/setup required. Existing IP/host/port/name
editor and JSON unchanged; no secret/role/checkbox/hosts edit. Native sources:
native_search.c,native_session_provider.inc; NEW native_lan_identity.{h,c}.
ONLY game-install deltafromfix6:
SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/native_search.dll
(or detected Win64/ue4ss/Mods/SzeroLAN/scripts/native_search.dll).
No originals/loaders/othermods/config/save/externalinstallation touched. Differing
own mod DLL backed up by normal setup. Revision native-session-v3-development-fix7;
DLL SHA2564f964efbe27867372ce1aa1e6d7cd152c768c8afd358fb7e86801c62db29f8b8.
OriginalShippinghashreverified unchanged. All6Lua mockcontracts pass; strict
Win64 DLL build passes. Final Python suite179tests,no skips,116.153seconds:
actualcompiledlegacy/v3worker, realTCPUDP, disposableWine/Xvfb; syntheticnative
callbacks/titledecision, NOTgame. NewHELLO4compiledsearch→create/search→join
case same underlyingprimary/persona, copy0/selfprediction0, exact1own in
membershipview, consistentowner/sharedID/stream. New4clientLANUDPcase proves
2isolatedpairs bidirectionally withsameunderlyingidentity. Portableprojector
failureatomicity/ownership/pointer/duplicate/bounds tests; strictWin64frames
<=512B. ProjectorASan/UBSan detect_leaks=0, NOleakcheckclaim. Separate8LANtests
10.656s; publication/maxreport contractalso passes. Fix7distribution108explicit
allowlistedentries; archiveSHA256
bcf91fd75542d3bfb64ace5216e81725eeff97909a5666ef22f3edd51cdba8cd.
Source/manifest/archivepayloadidentity verified via build_bundle.py --check.
REA binaryclosed after bounded audit. No actualgame/runtime/channel/combat proof.

LATEST36b2run2026-10-24: NEWservertracing CONFIRMSnativeprimarycollision at
INGRESS, notjustclientprediction. Maxinator7048f484645e47b69587fb043cf07015
andPlayer9963a3ee4adc4c4898aa900034522079 submitEQUAL17byteprimaries but
DIFFERENTsecondaries(length4/5). Firstcrosscomparison02:08:41.136CEST;
returned-owner02:09:15.854(Maxrpc34)/02:09:35.348(Playerrpc48) same1/0.
Linux36b2rpc34return1/result0/read1/copy0/numeric1/selfprediction1/joinattempts0,
fix6Steamkind1/thread2164matched,noquarantine/captureerror. Serverthenseparate
CREATEs, nojoin/2membercommit. FinalJSONrpc97return0/inspectionunknownEXPECTED:
bothroomsleft02:10:16.585/.942beforesearch02:10:16.986. DoNOToverwriteearlier
rpc34evidencewithfinalemptysnapshot; leavecauseunknown, notprovenmanualcancel.
ONLYUDPregistrationevents; noDATAforwarded/dropcategoryrecorded, notfullpcap.
PrimaryequalityALREADYinclientsubmissionsrulesoutservercreatingcollisionon
return. ActualnativeID/API/configcauseunknown; doNOTblameGUIaccountselection,
requireswitchingaccounts/changeplayernamesorclaimobservedgamebranch.
native_self_exclusion is OURprediction, serveringresscomparisonisnewindependent
evidence. Nativeuseridentitysource/isolation+properLANprincipals remains the
implementationgap. No furtheridenticaltest/newdiagnosticrelease neededto
rediscoverthisknownboundary. Same-accountLANremainsREQUIREMENT. DoNOTblindly
overwriteglobaluser200/useconsumingidentitysetter/drop4d/forcejoin/forgeSteamID.
Report:analysis/runtime-36b2-ingress-collision-2026-10-24.md. THISPASSdiagnostic
report+AGENTSonly; noDLL/server/runtime/packagechanges/newtests/battlesuccess.
Existing102entrybundle verified via build_bundle.py --check unchanged.

LATEST f7ab/2026-10-23: user DEFINITELY useddifferentSteamaccounts, stillsame
behavior, explicitlyaccountsMUSTNOTberequirement. Prioraccountcauseclaim/
suggestion toswitchaccounts is WITHDRAWN; doNOTblameaccountselection. Linux
f7ab(Maxinator ab3273799f144c91b5fd67c53df63335) rpc49/89 BOTH return1/result0,
read1/copymask0/numeric1/selfprediction1/joinattempts0, Steamkind1thread1872
matched,nocapture/quarantine. Server returnsPlayer dcede7aa1b684245a0a121030d8e1478
room18:07:10.854/18:07:49.144CEST; thenseparateCREATE eachtime. Initial
18:06:17.535search0expectedfirsthost. server.log APPENDSolder17:48run; don't
conflateUUIDs/timelines. No2membercommit/join, hence novalidnativegameplayrelay
route established; thisdoesNOTprovenostray/droppedUDPpackets. Field
native_self_exclusion is OURread-onlyprediction basedonoriginalrule, NOTgame-
emittedfield/observedremovalbranch. Equalityobserved; causeofequalityUNKNOWN.

Deepaudit originalSteamidentityproducer1458fae90→1458f9980→1458e0ad0→1458e0150:
nativeSteamAPIIDformattedprimary, persona secondary; baseconstructorstarts
empty. Actualuserbackend/APIreturnedvalue intheuserprocessstillunknown.
Server→transaction→Python/Ccodec→materializer audit plusfocusedcompiled test
findsnorequesteridentitysubstitution;HOSTidentityretained. Globalidentitysetter
isNOTsafeisolatedLANfix: changingpublic+200triggerscacheclears/events/readiness;
consumesnativeownedstrings;userisshared; Steamcreate serializespublicpairinto
platformmetadata. Nooriginalcallerprovesindependentpublic/platformalias.
Noaliaswrite/settercall/filterbypass/authchange shipped. ProperLANprincipal
scope acrossnativeconsumers/lifecycle/transport remainsunimplemented.

Userasksseeeachsubmittedmessage/matchandcontinuefix. ImplementedSERVERONLY
traceupdate: newlan/native_identity_diagnostics.py +integrationlan/szero_lan.py.
RetainslastVALIDATEDpairperliveTCPclient(max256), clearedondisconnect. Logs
ingress primary/secondary lengths, atmost4crosspeer equalitydetails+aggregate
counts; firstguestCREATEexposescollisionwithoutanothersearch. Candidateowner
comparisoncorrelatesrequest/session/memberUUID; unknownrequester=-1. Neverraw
identity/hash/address/opaque/pointerlogging. Thisisobservability, NOTplayablefix.
NewboundedLANUDPfirstevents registered/no_route/peer_unavailable/forwarded,
eachonceperlivepeer; registrationheartbeatNOTgamedata, forwardedNOTbattle.
Admission/response/UDPwire/routingchecksunchanged. Newtests:
lan/test_native_identity_diagnostics.py andlan/test_native_udp_diagnostics.py.
README/buildallowlist/manifests/distribution updated. DeployFULLservertools
includingnewmodulebesideszero_lan.py,restartserver. Existingfix6clientsneed
NOrepatch; DLLunchangedSHA256
3ed8e8ec4c27c7fac65e8336b2f95cc206f5aab569d6383fe90b92091ecef579.
Originalshippinghashreverifiedunchanged; externalinstalls/config/loaders/other
mods untouched. Report:analysis/runtime-f7ab-identity-provenance-2026-10-23.md;
4newanalysis/native-identity*/native-steam-identity*f7ab-trace.txt preserve
boundedread-onlyGhidraselectedbodies; REAoriginalidentitychecked/closed.
Finalverification:169Python tests pass,noskips,98.045s; actualcompiledlegacy/v3
workers/disposableWine+Xvfb/realTCPUDPloopback plus14newdiagnostictests.
NewrealTCP2clientcase proveshostdescriptorunchanged,initialmissingingress=-1,
firstguestCREATEsharedprimary/differentsecondarycomparison,disconnectcleanup.
UDP4tests checkonce-only/size-onlylogging, sourcerejection, no_route vspeer
unavailable vsactualforwardingwithunchangedpacketbytes. No newnative/Lua edit,
DLLrebuild/sanitizer/leakcheck/gameexecution claimed. Distribution102explicit
allowlistedentries; ZIP SHA256
2d09dc2d934f685eff6d878437e85f12bbe35a0eba9ab9c3be0319f83418c08f.
Bothmanifest/archivepayloadidentitiesverifiedvia build_bundle.py --check.
Onlynewinstrumentedserverrun canprovidemissinghistoricalingresscomparison;
oldunrecordedidentitybytescannotberecovered. DoNOTaskforanotheraccountchange.

LATEST REQUIREMENT2026-10-23: user has ONE Steam account and explicitly
requires same-account offlineLAN. Do NOT prescribe buying/using a second
account as the solution. Earlier distinct-account suggestion was a diagnostic
workaround for current adapter, NOT a fundamental limit on custom LAN design.
Currentfix6doesNOTsupportthisrequirement. Need explicit LAN participant identity
namespace and consistent native adaptation, separate from actual Steam login/
ownership/authentication. Do NOT impersonate other Steam accounts or bypass
platform checks. User-scoped LAN participant IDs are a new design requirement,
not grounds to relabel arbitrary invented Steam IDs as legitimate accounts.

Sourcecheck confirms more than search must change: provider_identity feeds
create/join/membercapture/addressselection; provider_addresses matches BOTH
identitystrings; original native host localize calls14592d690; lifecycle member
capture uses same native identitypair. Clearingquery4d or changingwireID alone
cannot establish unique localmember selection, nativeowner events ortransport.
Before shipping LAN identity projection, audit all consumers and prevent any
LANnamespace IDs reaching retained Steam/account operations as Steam IDs.
Keep platform/user ownership untouched; no global user+200 write or blind
userobjectclone. Actual game boot/concurrent entitlement behavior not changed.
No same-account solution implemented or runnablebattle claimed in this followup.

LATEST suppliedfix6 runtime2026-10-23: user CORRECTS earlieranswer:
"oh nevermind should be the same steam account". Separateaccountclaim below
is superseded. Linux023c/Maxinator reports rpc54/97/139/196 ALL return1/result0,
inspection_read1/copymask0/numericpass1/SELF_EXCLUSION1/join_attempts0.
Server acceptsPlayercandidate(all exclusions0) eachtime; Linux thenCREATEs
separate room, no shared2memberjoin. Initial rpc1 return0 expected firsthost.
Fix6installed,Steamkind1,thread1156matched,noquarantine/captureerror. Positive
selfprediction proves checkedprimaryowner/localbytes equal withquery4d enabled;
original1458c08b0 removes equalprimary. Sameaccountcorrectionfits identity
collision; stronglysupported explanation, NOT breakpointtrace. DoesNOTprove
laterjoin/channel/combatready. Launchername/serverUUIDdoesNOTchange nativeID.
NoinventedIDs, fieldswap, predicatebypass ordiscardedflags. Meaningfulnexttest
requiresdistinctlegitimateidentitiesactiveINGAME, notanother sameaccountrun.
DoNOTconflate suppliedLinuxreport withWindowswhose nativefileisnotsupplied.
RecheckserverDTOstoresHOSTmember, provider_addresses changesaddressesonly,
materializerownerfromDTO; no source-level requesteridentitysubstitutionfound.
Originalgetteroffsets/predicatepolarity independentlyconfirmed; no inspector
falsepositiveidentified. Report:
analysis/runtime-fix6-self-exclusion-2026-10-23.md. Thisfollowup diagnosticONLY:
no runtime/source/DLL/config/game/distributionchanges, no newtest/battlesuccess.

CURRENT fix6 (2026-10-23): user requests deep research/results and confirms
SEPARATE Steam accounts. Quickmatch/combat STILL NOT achieved; this revision
is a diagnostic handoff, NOT a proven playable fix. Actual fix5 Windows
return1/result0→separateCREATE is still the observed gap. Both clients Steam;
fallback normalization does not explain this run. No identical old-build/F5
test, forced merge, discarded flags, renamed identities or auth bypass.

Deep audit: query+4d identity remove_if1458c08b0 compares descriptor+88 primary
OWNER identity to legitimate local primary; equal bytes/length removes it,
secondary/sessionUUID/memberlist/displayname ignored. Local-empty skips it.
147b48c18 is unused tag, not called vtable; prefix-compare returns equal length,
NOT C memcmp0. Separate accounts does NOT prove actual native strings differ;
no identities were logged. Descriptor145943940/145945540 layout/deepcopy audit
found no mismatch. Original join wrapper1458c299d zero-extends ushort R9D;
Steam1459269b0/145921190 consumes a borrowed view, not proven raw-R8 numericID.
Thus no blind ABI/layout/filter patch is supported by this investigation.

Independent controlled original-instruction oracle now PASS10,000 cases vs
production server predicate: signed comparisons0..4, AND/OR, missing keys,
maxcounts/uint64keys/uint32compatibility/default/+4e. Source-only
analysis/scripts/native_numeric_oracle.{py,c}; exactSHAguard,2copiedcodepages,
PROT_NONE surrounding reservation, RW→RX neverRWX, disposable subprocess.
Only pure145940dc0→1420a2f50→145940b90/b10, synthetic buffers/NULLstats;
no gameentry/import/TLS/platform/account/network. Inputs unchanged. This is
actual pure-machine-code replay, NOT mocked callback or actual game/combat.

New linked read-only native_session_inspect.{h,c} evaluates ACTUAL deep-owned
returned vector element before provider return, never alters admission/output.
Sticky native_inspection_read (1valid), native_copy_mask (0checkedfieldsagree),
native_numeric_pass (1predictedaccept), native_self_exclusion (1predictedremove).
Unknown=-1; read0 means incomplete, NOT game rejection. Maskbits ID1/compat2/
numericcount4/values8/primaryowner16/capacity32/membercountbyte64. This is NOT
complete descriptor validation or event-level outer/title tracing. Heap scratch,
bounded callbacks/overflow/text/querycounts; no nativecalls/rawdata logging.
Sticky native_join_attempts/flags/code includes early nonzero-flags refusal
BEFORE accepted join_calls increments, survives immediatecreate. Guard still
refuses unsupported flags. All thread/hash/owned-vptr/auth checks unchanged.
Reports<=2048B, all snprintf truncation refused; maxwidth/canary testpasses.

Revision native-session-v3-development-fix6; bundledDLLSHA256
3ed8e8ec4c27c7fac65e8336b2f95cc206f5aab569d6383fe90b92091ecef579.
ONLY game-install deltafromfix5:
SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/native_search.dll
(or installer-detected Win64/ue4ss/Mods/SzeroLAN/scripts/native_search.dll).
External installs NOT modified; original Shipping hash reverified unchanged.
Close games, use updatedtools normalsetup; backups/loaders/config/othermods
preserved. No server behavior/wire change thisrevision. Full fileledger/evidence:
analysis/native-postfilter-investigation-fix6.md and
analysis/native-postfilter-deep-fix6.txt. REA exacttarget opened/closed; bounded
directGhidra selected .pdata/chained fragments, no globalanalysis; no false
claim of REA runtime instrumentation. Old /tmp fixtures had vanished and were
rebuilt under /tmp/szero-fix6-verify-eZSnYE with disposable Wine/Xvfb.

Verification:155Python tests pass,no skips,108.919s, actual compiled legacy/v3
IPC workers/realTCPUDPloopback, synthetic nativecallbacks/titledecision.
Compiled quickmatch inspector detects intentionally incomplete mockclone mask114;
sticky results survivecreate/join; nativejoinattempt flags0/code0 exercised.
All6Lua contracts, strictWin64DLL/inspector<=512Bframes, inspectorASan/UBSan
with detect_leaks=0 pass (NO leakcheck). Final maxwidth report/refusal-canary
and publication regression independently rerun after formatguard changes:
1test/4.192s passes. No actualgame launched or Windows recovery/combat proven.
Fix6distribution:99explicitallowlistedentries; ZIP SHA256
68d2f6cc8244d5973ee80066b0118016242897620974b07a5b80aacbecc3a812.
Both manifests/archivepayloadidentity verified via build_bundle.py --check.
Remaining evidence must distinguish read/copy failure, native numeric/self
prediction, earlyjoinrefusal, then later titleblacklist/continuation. Do NOT
present passing synthetic Quickmatch fixture as realgame completion.

Latest Player/Windows fix5 files restored/read2026-10-23: correctserverclient
b2437532e4c54d06bbe55bfe4d244a6b;requests1and37 BOTH native returncount1,
result0, sampledcontextcount0, followedbyseparateCREATE/cached. Steamkind1,
thread3040matching,noquarantine/captureerror. Combinedserverevidence rulesout
emptyreply/RPCdecode/nativeconstructionrefusalforTHOSEsearches. BothPCsare
Steam; fallbacknormalization NOTcauseofthisrun. Remainingpost-provider
processing/acceptance/join boundary; doNOTclaimexactfilterfromsnapshots.
Recheck1458cc840 numericrefilterANDquery+4d identity-removal branch147b48c18/
1458c08b0 before14595ec10 context-vectortransfer; then titleID/joincontinuation.
No proofsameaccountcausedit; no inventedidentities/discardedjoinflags/forced
success. joins0stilldoesnotexcludeearlyflagrefusal. No furtherexistinglogs or
identicaluninstrumentedtest needednow. Report:
analysis/runtime-fix5-windows-native-return-2026-10-23.md. Diagnostic only,
noDLL/runtime/packagechanges,newtestsorplayablesuccessclaims.

Latest fix5runtime(2026-10-23 16:04–16:05CEST): server DOES accept/return
Maxinator's waiting session to Player twice(results1,allexclusions0,flags40).
Player then CREATEs separate sessions eachtime; noshared2membercommit.
Attached UE4SS is Linux/Maxinator FIRSTHOST, notPlayer:fix5,Steamkind1,
expectedemptysearchreturn0,createcached,matchingthread1092,noquarantine.
Do NOT attribute hostreturn0 to guest's result1 search or assumeWindowsstatus.
Serverfilterrelaxation is notjustified; nextgap lies AFTERserverselection.
Need existingPlayer/Windows UE4SS.log +native_search_<instance>.json from
THISrun(andclientlogifavailable), NOT anotheridenticaltest. Nonzerojoinflags
currentlyrefusebeforejoin_calls increments:zerojoins alone != noattempt;
notprovenactualcause, doNOTdiscardflags/bypasschecksblindly. HostSteamkind
alsoestablishesfallbacknormalizationwasNOTthat host's observedproblem.
Report:analysis/runtime-fix5-candidate-accepted-2026-10-23.md. Diagnostic only,
noDLL/runtime/packagechanges,newtestsorplayablesuccessclaims.

CURRENT fix5 (2026-10-23): user requests Quickmatch completion, confirms both
clients selected matching battle settings, and says last action was lobby
creation/error. Later6d15df0 refusal may relate to lobby, NOT proven and NOT
explanation for earlier accepted Quickmatchcreates. Unknown type still refused.
Do not ask to change selections or use F5. Playable Quickmatch NOT achieved.

Native audit confirms3-word owned search vector/aux fields correct; outer
1458cc840 rechecks numeric/OR predicate using original service+40 default.
Steam/standardLOCAL1411072d0 returnsfalse, fallbackLOCAL1410fdcc0 returnstrue.
Fix5 sends exact owned/whitelisted leaf-derived default inSEARCH3/MATCH3,
instead of hardcodedfalse; explicitquery+4e stilloverrides. No arbitrarynative
call or filterrelaxation. Actual suppliedbackend unknown, so NOT provenrootcause.
Blacklist14595b980 hashset andtitlepredicate1459eb450→1458edef0 compareIDs;
NOT SteamnumericIDparsing, no evidence to renameUUIDs/bypassnativepredicates.

Server sharedadmission predicate emits bounded aggregateexclusions+<=4candidate
numeric summaries, resultcounts; transactions logaction/session/membercounts.
Noidentity/address/opaque payloadlogging or wirechanges. Native sticky request/
returncount/result survivescreatebetweenpolls; requestN↔serverrpc-N. Context
vectorcount is a bounded snapshot, NOT preciseacceptanceevent. Servicekind
0unknown/1Steam/2standardLOCAL/3fallbackLOCAL. JSON<=2048B,maxwidthtested;
truncationrefused, all originalhash/thread/owned-vptrguards preserved.

Changed servertools:native_sessions.py andszero_lan.py. Nativeprovider.inc/
native_search.c compile intobundledDLL. ONLY game-install deltafromfix4 is
SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/native_search.dll (or detected
Win64/ue4ss/Mods). Nooriginals/loaders/config/othermods/externalinstalls changed.
Fulltoolsbundle/serverrestart +clientsetupupdate required fornewcorrelation.
Revision native-session-v3-development-fix5; DLLSHA256
35b891eb4fa1a78109326b2f530b01b962980b0a7b93d50020adcc81d3431887.

Verification:154Python tests pass,noskips,104.277seconds,realTCP/UDPloopback,
actualcompiledlegacy/v3workers,disposableWine/Xvfb. NewcompiledQuickmatch
scenario search→createA/search→joinB provesoneserver2membersession; native
factory/clone/titledecision SYNTHETIC, NOT game/combat.6newserverdiagnostic
tests differentialpredicate/privacy/exclusions/actioncorrelation. All6Lua,
strictWin64build andseparatemax-report/publication regression(4.133s)pass.
No new sanitizer/leakcheck. Originalshippinghashreverified unchanged.
Reports:analysis/quickmatch-handoff-fix5.md and
analysis/native-quickmatch-acceptance-fix5-trace.txt. Further runtimeevidence
must distinguish serverresult0/exclusion fromnative return1/nojoin; do not
call thiscompletedmultiplayer orrequestidenticaluninstrumentedtesting.
Fix5distribution:95explicitallowlistedentries includingnewdiagnostictest;
archiveSHA256 b678b0a883d2090b538848cda0e505a172052dea5bbaf627b02dd21fec8e3904.
Bothmanifestandarchivepayloadidentitiesverified via build_bundle.py --check.

Latest supplied fix4 run reviewed2026-10-23: both server connections issue
search and prepared/committed transactions. Supplied743b/Maxinator native
report reaches4creates/cached,4searches,ZEROjoins, matchingthread908,no
quarantine. Repeated leave/search/create cycles, NOT proof of one server
search held alive beyond120seconds. Player transaction action is NOT logged;
do not infer both created merely from prepare/commit. Server logs omit result
counts/filter reasons/action/session/member correlation; cannot yet distinguish
candidate filtering from native returned-descriptor rejection. Later23:58:38
local create refuses another UNKNOWNVTABLE6d15df0 (114384368), unreadsizezeros.
Separate later limitation, not explanation for prior successful cachedcreates.
Next evidence: bounded candidate/exclusion/result counts, transaction action/
membership and native acceptance correlation; no blind filter relaxation,
forced session merging, neighboring-vtable aliasing or identical F5retest.
Report:analysis/runtime-fix4-no-match-2026-10-23.md. Diagnostic only; no runtime
file, DLL or distribution changes, no new tests or battle success claimed.

CURRENT fix4 (2026-10-22, Windows ProcDump23:40:47): actual C0000005
null READ at Shipping+580d698. Dump SHA256
fb65ebd5476d705e6118673d6f3d9044920715cf90208d3825b4374670ef7030.
Bounded initial unwind verified using original PE unwind records:
parser14580d680 <-1459425a0 <-Steam145927dc0 <-native_search+7527
(block_create calling lifecycle_readiness). Internal readiness incorrectly
called original service+c8 with TWO args; Steam implementation requires TWO
additional ID views. LOCAL+c8 has a different contract. Fixture had falsely
modeled both as a two-arg getter. This is OUR ABI defect, not evidence of
remnants/GPU/security failure. Linux selected backend identity remains unknown.

Fix4 internal status follows original LOCAL14592efa0 lookup: service+8->bundle,
bundle+8->platform, platform virtual+60 with PLATFORM receiver. Owned-service,
thread, bounded-read, original-image executable guards remain; native errors
propagate, no manufactured success/authentication bypass. Published Steam+c8
uses explicit four-argument unsupported-operation refusal, LOCAL uses status.
Regression fixture now has a fatal wrong-service+c8 sentinel and separate
platform receiver/callback, including missing-platform refusal.
Revision native-session-v3-development-fix4. Bundled DLL SHA256
5fe23bf44480df288cc8c01a4e3861ab2ec349b9dd8ca79e2fd5b5fc68ce54cb.
Only installed game delta from fix3: scripts/native_search.dll; preserve all
loaders/config/other mods/originals. External installations NOT modified.
Details:analysis/runtime-windows-access-violation-fix4.md. REA recorded-crash
tool only supports Linux cores; Windows MDMP parsed read-only with struct,
original objdump and PE unwind records, NOT fabricated WinDbg/REA results.
Windows runtime recovery and combat remain UNVERIFIED. Do not claim fixing
this one exception establishes all Steam/LOCAL slots have equivalent contracts.
Verification:147 Python tests pass, no skips,94.303seconds; all6Lua contracts
and strictWin64DLLcompilation pass. Actual-include regression checks platform
receiver/missing platform, fatal wrong-service-slot sentinel; publication
fixture checks distinct Steam/LOCALcallbacks. Synthetic natives/real loopback
only, NOT actualgame. No new sanitizer/leakcheck claimed. Original EXE SHA256
reverified unchanged. Fix4distribution:94allowlistedentries, archiveSHA256
c98e9881535c6fe0cc10d401a0dde3ed90199a9263f245bf69c5b7a6a4684826.
Both manifests/archive payload identity verified by build_bundle.py --check.

CURRENT fix3 (2026-10-22,0bcc supplied blackscreen): exact newreport proves
native CREATEcapture refused by UNKNOWNVTABLE, moduleRVA114382912=0x6d15840.
Size/cursorzerosareUNREADdefaults, NOTemptydata. Matchingthread920,noquarantine;
searchreachedserver22:37:42.798local. No create/commit/battle, nocrashexception
stack. Fix2didNOTresolveit; itsvectorlayoutwasnotthisobservedclass.

New exact146d15840 reader:48-byteheader, read/write+10/+18,length+20,capacity+28,
EMBEDDEDbytesobject+30; NOkindfield/externaldatapointer. Constructor145839350,
factories145857f10/1459d6c20 andoriginalgetter1424ae2f0 confirm. Recoveredvia
boundedretainedGhidra+originalbytes;12RIPLEAcandidatesnotallvalidatedxrefs.
Unknownvtable stillrefused; bounds/cursorpolicy,borrowedownership, native-only
default andauthenticationchecksunchanged. Layoutenum4=embedded,3=unknown.

Revisionnative-session-v3-development-fix3; bundledDLLSHA256:
2e947e026f2ff7fe1e7a0f11814293e7983dea64c1daa35ad0988bca158b1172.
Onlygame-sidechange scripts/native_search.dll. Externalinstallationreadonly;
noactualgameexecuted.147Pythontests pass,noskips,93.753seconds, includingnew
compiledcreate-embedded→realRPC/server→codec→syntheticnativefactory/cachecase;
payload/cursorschecked. All6Lua,strictWin64build,ASan/UBSanwirefixturepass
(detect_leaks=0, NOleakcheck). Realblack-screenrecovery/combatUNVERIFIED.
Reports:analysis/runtime-native-observed-stream-fix3.md and
analysis/native-observed-stream-fix3-trace.txt. NooldF5testrequested.
Fix3distribution:94explicitallowlistedentries; ZIP SHA256
efc142af99e04754544882c7d22c001e420d1e0ae96c5b28280444151356edc3.
Manifest/source/archive identity verified by build_bundle.py --check.

PREVIOUS fix2 (superseded by fix3 above): supplied matching5bef native
report + UE4SS log prove CREATE capture refused specificallystream_unsupported
code2 aftersearch22:22:53.495local; thread932matched, noquarantine. Fix1didNOT
resolveblack screen. No crashstack; logs do NOTestablish nativeexception.

New separate exact-layout capture: vector147b43960 is64B, data+20/count+28/
capacity+30/allocator+38, cursors+10/+18. Original145839ac0/1457dac30 and
vtablegetterbytes confirm this; never read the inline72B header overvector.
Knowninline147b43f10/kind1 remains supported. Preservepayload/cursors, no
nativegetter/destructorcalls, no arbitrary-vtableacceptance. Unknownfamilies,
writecursorbeyondlength andbounds stillrefuse. The oldcode2doesNOTprove this
specificruntimeobjectwasvector (couldunknownvtable/kind/cursor); don'tclaimit.

Revision native-session-v3-development-fix2 adds bounded stream layout/refusal,
module-relative vtableRVA,length/cursor diagnostics (noabsolutepointers/identity/
payloadlogging). Onlygame-sidechange scripts/native_search.dll; SHA256:
64afb8ebb2f97ee7456168d57fe18c8e260017c9d0382758d880a16c9937bd2e.
Native-onlylauncher/defaults andfix1borrowedownership preserved. Externaltest
installationread-only, noactualgameexecution.146Python tests pass,noskips,
90.730seconds,compiledworkerwithvectorinput→realRPC/bridge/server→codec→
syntheticnativefactorybytes/cursorsverified. All6Lua contracts,strictWin64build
andchangedASan/UBSanfixturepass (detect_leaks=0, NOleakcheck). Everycapture
frame<=512B regression. Realblack-screenrecovery/combatremainUNVERIFIED.
Report:analysis/runtime-native-stream-refusal-fix2.md; statictrace:
analysis/native-vector-stream-fix2-trace.txt. Do not askforoldF5pairing.
Fix2 distribution:94 explicit allowlisted entries; archive SHA256
7aa05106b140d874294b46e719f8759c95e13bab64da1773b465e83dccd262ee.
Both checksum manifests and source/archive payload identities verified.

PREVIOUS fix1 (superseded by fix2 above): native-only normal
launcher, NO mode checkbox; save/launch migrates absent/oldfalse session/search
flags totrue, preserves unknown fields, sets SESSION3=1/SEARCH=1/MENU=0 and
retains exact EXE/helper/server preflight. Fresh client.example defaults true.
Do not reintroduce unsupported normal overlay/search-only launch options.

Read-only supplied a6 report proves search accepted then CREATE(kind1) capture
refused, not a failed query/thread/network call. create_calls0 increments after
accepted capture only; expected/observed thread2264 matched. Current UE4SS.log
was overwritten by later1609 legacy run; no native crash stack is available.
Actual black-screen cause/resolution and combat remain UNVERIFIED.

Fixed unsafe settings cleanup: outer1458c84a0 ALWAYS destroys settings after
virtual+88 returns. Our provider copies, never moves ownership; it must leave
borrowed settings untouched, especially after capture refusal. Removed native
destructor/free and input mutation from create/match/update wrappers. Actual-
include regression now asserts caller ownership instead of inventing consume.
Settings capture uses bounded72-byte header/private heap: Win64-O2 stack224B
vs8592B, regression<=512B. No validation relaxed/identity invented/auth changed.
Added bounded native_capture/native_capture_code refusal diagnostics; create
failure no longer mislabeled query_invalid. Revision:
native-session-v3-development-fix1; new bundled DLL SHA256:
ce649c372e8b2a8afab8cbf24d34584e6bcaa9bc6d16b3244f1c55623f5c879e.
Only game-side change THIS revision is scripts/native_search.dll. Normal
installer backs up differing own DLL; external shared/SZeroLinux untouched.
Full investigation and evidence limits:analysis/runtime-native-create-refusal-fix1.md.
Fix1 verification:146 Python tests, no skips,89.941seconds; actual compiled
legacy/v3IPC fixtures, isolated Xvfb/disposable Wine/real loopback networking.
All6 Lua contracts pass, strict Win64 DLL build passes. Changed wire fixture
passes ASan/UBSan with detect_leaks=0; no leak-check or real-game success claim.
Fix1 distribution:94 allowlisted entries; ZIP SHA256
af4b8cc78f93576a9f80c97724ab50fbbd5ec527fe7ac4ff4827dddc38453dcf.
Source/manifest/archive identities verified with build_bundle.py --check.

PREVIOUS native session-v3 update (superseded by fix1 above): the real C dispatcher is NOW
linked into the bundled native_search.dll, including native constructor/host/
owned search results/lifecycle/transport components. This supersedes all older
"unchanged DLL/source-only" milestones below. Actual game/native allocator,
callback-thread compatibility, channel negotiation and synchronized combat are
STILL UNVERIFIED. Do not claim tournament readiness or achieved playable goal.

Bundled helper SHA256 changed from
9bcc674310fb68f08df05bb06676fdcf1b01b453902a5e0319b7faa5adf9c087 to
66d4426a683576a9f1bc117bf9879d2ff6c819dcc28d91dafa2475631764861e.
Revision native-session-v3-development; report reason installed_session_v3_development.
Native operation/stage/result, expected/observed thread and quarantine diagnostics
are bounded scalars. Old v2 search did NOT prove native thread==Lua thread;
strict new native guards refuse mismatch rather than silently running there.
Original native +38 service task queue is forwarded EVEN on its original
non-Lua thread; only added LAN work is thread-restricted. Never drop that queue.

New launcher checkbox selects the experimental native sessions without manual
JSON/environment edits. Saves native_session:true + native_search:true, sets
SZERO_LAN_NATIVE_SESSION3=1 only for that explicit mode; legacy v2 remains
separate. Defaults OFF; preserves existing configuration/unknown fields. When
unchecked after a v3 session, both flags disable on save. Launcher rejects
outdated installed native_search.dll vs bundled hash/revision marker, so it
cannot silently run v2 while claiming v3. Close ALL games before setup/update.
Native-mode launch also verifies the exact shipping EXE and probes the selected
server for session-v2/transaction-v1 capability; absent/old servers fail before
game launch. This is a bounded LAN check, not platform authentication.

Only game-side packaged changes: Mods/SzeroLAN/scripts/native_search.dll and
native_search.lua under SparkingZERO/Binaries/Win64 (or detected ue4ss/Mods).
No original EXE, game DLL, PAK/UTOC/UCAS or save patched. Existing loaders/mods
preserved, differing own mod files backed up by installer. Game-root SzeroLAN.json
changes ONLY via normal config editor/checkbox. External shared/SZeroLinux
installation remained read-only; user must install updated bundle themselves.
Server/client MUST update full tools folder, including NEW server dependency
native_session_transactions.py; Python/C sources NEVER go into game scripts.

Implemented coherent limited-profile operations: finite native search vectors
(original allocator/copy/release, bounded stats writes), create/join preparation
BEFORE remote commit, cache consumption AFTER matching COMMITTED, conditional
native abort/quarantine, query/join-or-create, owner-authorized registry flags
(separate from member fields), full supported settings streams/actual member
flags, owned-settings cleanup, leave/cache teardown and periodic in-place diff.
Unknown native ownership retains one bounded quarantine and stops allocations.
Unchanged passive snapshots skip reconstruction/diff through a bounded four-
service frame cache, preserving consumed stream cursors. Explicit settings
updates still apply. Immediate next operations cooperatively drain completed
worker handoff before claiming its mailbox; no-session fences do not fabricate
readiness for an unfinished operation. Native thread guards precede task access.
Idle transport gate checks mode2/all12channel slots/state, suppresses platform
transport override byte661 only, never reinitializes active contexts. Local
bind is game port; remote addresses are own proxy ingress, both loopback ports
retained across sidecar reconnect. Legitimate identity strings are preserved;
no invented account identities or platform/auth/readiness/DRM bypass added.

Server prepare is invisible/no UDP route, stable IDs/reserved slots, <=120s
expiry and per-connection generations. Abort compares BOTH session and member
token, so it cannot delete a newer rejoin to the same room. Concurrent match
preparations retry an invisible host rather than create two rooms. Mailbox
updates happen in server receive order; delayed old commit cannot rewind a
new two-member notification. LOCAL search policy is explicit default-normalize
false, numeric/OR predicate, capacity2 and metadata flags&5 admission. This is
not Steam geographic matchmaking emulation. Profiles reject nonempty properties,
unknown stream implementation/write-growth and unsupported nonzero join flags.

Current deployment/build details: lan/README.md, lan/native/README.md and
analysis/native-session-v3-integration-status.md. New focused native evidence in
analysis/native-provider-transaction-v4-findings.md and ledger below. Bundle
build/check uses python lan/build_bundle.py [--check], explicit allowlist only.

Final verification for this CURRENT update:145 Python tests pass, no skips,
with both actual compiled IPC fixtures enabled, disposable-prefix Wine and
isolated Xvfb/real loopback sockets;90.574 seconds. All6 Lua contracts pass.
Actual-include lifecycle regression covers immediate FLAGS->fence and
LEAVE->no-session-fence with20ms delayed recycling, unchanged consumed cursors,
changed members and unsupported/foreign state. Strict Win64 DLL compilation
passes. Portable adapter/search/codec/wire ASan/UBSan fixtures passed earlier
in this update with detect_leaks=0; do NOT claim leak checks. Native callbacks
are synthetic fixtures, not actual game calls. Original shipping hash remains
e54e79e756f79719f09915078a37b6e87c23d32ecaaaa2f485d1a048ba198e55.
Current distribution:94 explicit allowlisted entries; ZIP SHA256
258d0aa60603dc2f6eb2a54a8cfef4437be84c12651ac5d201ca54f2527d30b0.
Both manifests and archive payload identities verified by build_bundle.py.

### Historical notes below (superseded where stated by CURRENT above)

Earlier in-turn work (2026-10-22, latest user: "then do it and do it right"):
new session-v3 bridge/server integration is under implementation. Do not infer
playability or ask for another identical test. Supplied 20:24:53 search hit the
known120-second timeout at20:26:53; later connection-refused is separate.
Native lifecycle recheck corrects +a0 to query/join-or-create and +b0 to
owner-only registry metadata flags, NOT member flags. LOCAL admission rejects
create_flags&5 and full rooms, defaults numeric compatibility normalization to
false. Sources changed in this pass are not yet a verified game deliverable.

New/changed artifacts during active work (install destinations are explicit):
`lan/native_session_transactions.py`: server tools beside szero_lan.py only;
invisible prepared descriptors, reserved join slots, stable IDs, generation
fences, conditional committed rollback,120-second expiry, no prepare UDP route.
`lan/native_sessions.py`, `lan/szero_lan.py`: server tools; match, metadataflags,
transaction protocol. `lan/native_search.py`, `lan/ingame_client.py`: client
tools, bounded v3 IPC and bridge routing (legacy kept). New tests
`lan/test_native_session_transactions.py`, `lan/test_native_session_rpc.py`:
do not install. `lan/test_native_sessions_v2.py`: test helper updated, do not
install. `lan/native/native_session_search.{h,c}`,
`lan/native/test_native_session_search.c`, `lan/test_native_session_search.py`:
source/fixture only, do not copy into game. `native_session_adapter.{h,c}` and
`native_session_host.c` (all under lan/native): staged native ownership work,
source only until dispatcher verified. No original game or external tested
installation modified. Distribution/manifests not regenerated yet this pass.

Latest session implementation work (2026-10-22): user explicitly requests a
USABLE multiplayer replacement. That goal is NOT achieved. New server v2,
source native adapter/host/settings/codec/transport components are implemented
and tested, but NOT wired into the installed provider. Current game DLL is
UNCHANGED native-search-v2; search stillpending, create/join stillunavailable.
Do NOT present this development update as a playable fix or request another
identical pending/F5 run. Remaining implementation is spelled out in
analysis/native-session-v3-integration-status.md. No user testing is needed to
rediscover this known missing dispatcher. External installation read-only.

Latest supplied runtime DOES prove both native searches reachedserver17:48:04
and17:48:25local, pending/noerror, with8numeric/1compound onMaxinator. It does
notprove manualcancel ornative session/channel/battle. Duplicatecancel cleanup
is idempotent. This supersedes old note saying newpendinggamepath unverified.

Implementedserver native_session requestversion2/profile2 (v1unchanged/isolated):
fullsigned numeric/OR comparisons including permissive missingkeys andexplicit
compatibilitydefault; candidatefilter ONLY (notcomplete distance/roompolicy).
Opaque known-layoutstream canonicalbase64<=4096bytes,read/writecursors bounded
to capturedlength as limitedconstructionpolicy (writegrowthnativepossible but
unsupported), no nonemptyproperties. Searchlimit1keepsresponse<8KiB. Member/
creator-settingsupdate, stableidentities, duplicateidentity rejection, rawlocal
marker8b canonical0 forsharedstate; eachnativecopy localizeslegitimateownmember.
Servernative_transport event and registeredUDP routinguseactual2memberv2
sessions, neverlegacyqueue/match_start. Departure/disconnectrevokeroutes.
ClientLobbyClient acceptsvalidatednative_transport assignments. Originalnative
NativeSearchRPCstillnevercallsdirectoryv2. Session-v2versioncapabilitymeans
serverAPIavailable, NOTnativegamebackendready.

Newsourcecomponents (all NOTinstalled byinstaller): native_session_wire
boundedsettings/identitycapture +known147b43f10kind1stream; materializerexplicit
profile2opaque stream preservingcursors; SESSION3 Pythonencoder/Cdecoderowned
data/rebasedviews; native_session_adapter withcorrectcreateOWNEDIDstring
result,plain40Bjoinsuccess, cacheconsumption andownedinplacediff refresh;
native_session_host guardedWindowsbindingfactory/localize/string/cache/copy/
diff/atomicstrongweakrelease. Newpairlayoutvalidatedbeforenativefollowups.
native_lan_transport verifiesidlecontext+matching/session/task,mode2, all12
channelvtableslots/statectx+2c0==0 and permitsguarded661bytechange, neverreinit;
ownedinlinebindstring helper. These are NOT invoked bycurrentDLL. Futurelive
dispatcher must integrate all servicecallbacks, finiteownedsearchvectors,
create/join/update/leave/fences, transactional cancellation, local/remoteproxy
addresses andnativechannelhandshake. DoNOTforward Steam sessioncallbacks with
LANidentifiers orreturnmaterializerhandle as+88success.

Criticalneworiginalcodecontracts in lifecycle/stream/UDP reports: +88success
isnativeIDstringaftercache1458cbbf0 (consumespair), +98plain40Bzero-code;
14592d690 localizes8bANDoptionalpresence/value.1458caf50 consumesdeepowned0xe8
temporary andupdatesexistingnodes/events INPLACE; neverarena/wholesale replace.
OriginalLOCALcreate field88/e1initial0; createflags live AFTERdescriptor+e8,
notfield_e1. Realgameallocator/cache/diff/transportcallbacks NOTexecuted in
fixtures. CallbackWindowsbindingassumesouterverifiedhash/thread/ownedvptr;
it doesnotinstallprovider orreplaceaccount/platformreadiness.

Verification:99 Python tests pass withcompiledWin64IPC fixtureenabled, noskips;
all6Lua contracts pass. FivenewWin64fixturespass indisposableWineprefix using
owneddata/syntheticcallbacks only, no gamefunctions. StrictMinGW-Werrorbuilds
andstandaloneASan/UBSanpass (LSANdisabled; doNOTclaimleakchecks). RealUDPtests
use5clients/twoindependentsessions andexactrouting/revocation, NOTgamefights.
ServerDTO->PythonSESSION3->compiledCparser preservesactualopaque4096bytepayload.
No game-sidefilechangedthispass; gameoriginalSHA256 andnative_search.dllSHA256
reverifiedunchanged. Installerdoesnotcopynewsourcefiles togame. Distribution
contains75allowlistedentries, SHA256
43f2bcb7cce2c71868d0a2b1bc35616dfd6ef7f244258304464e309ef2486660.
It containsdevelopmentcomponents, notnewplayableDLL; see updatedREADME.

Latest native search-v2 fix (2026-10-22): supplied external game log proves
hook installed15:14:42UTC and searchintercepted15:16:24UTC. Its Maxinator ID
f92fb035a69c425a925d1d9bdd679816 has no serversearch; Player1 IDd10929df329148d0939fb7fa3f876a4c
has a DIFFERENT search17:16:42local rejected unsupported_compound_query and
cleanupcancel. Do not conflate those clients or label cleanup a usercancel.
InstalledDLL/Python matcholdbuild. Full sourcehashes/timelines in
analysis/runtime-native-search-2026-10-22.md. External installation READONLY.

Both handoff causes are now implemented fixes, not guesses. Compiled original
C connect_bridge reproduced Wine failure before network: after initial3valid
fields, final whitespace-only fscanf(" %c") returns0, notEOF; oldparserrejects
correctendpoint. Replaced with bounded160byte ASCII parser, strictport/token,
LF/CRLFallowed, NUL/extra/overlonginvalid. New analysis exact-build confirms
query+28 array stride32 flatPOD: two16byte numericpredicates OR, allpairs AND
ordinaryfilters. Missingkey semantics in native-compound-filter-findings.md;
do NOT invent generic strictmatching later. BEGIN2 IPC now copies both complete
predicates beforeyield; max16numeric/16pairs,8KiBline. Server preserves validated
compound_filters first/second values in pendingsearches, does NOT evaluate or
produce native results. Oldcount-only nonemptycompound stillrejects explicitly.
Do not simplyremove validation. Comparison0..4 signedint semantics verified.

NativeJSON revision=native-search-v2 adds ipc_phase/ipc_error/ipc_error_code/
last_request. Clientlogs identify IPCaccept/forward/reply without rawqueries,
pointers/identities. Productionprocess_job is unexported requestlifecycle factored
for actual compiled integration; NOproductionhashbypass. Onlygame-side artifact
changed thisrevision is scripts/native_search.dll (SHA256
9bcc674310fb68f08df05bb06676fdcf1b01b453902a5e0319b7faa5adf9c087).
main.lua/Luahelpers/installer unchanged thisrevision. Update ingame_client.py,
native_search.py and szero_lan.py with full toolsbundle; server needs new
native_search.py too. Keep existing native_search:true opt-in via preservedJSON;
freshsetup/update/restart required, originalOnline notF5. Nooriginalgamebytes
modified. Hookpublication/intercept is runtimeobserved; newpending/cancelgame
success remains UNVERIFIED. Nativecreate/join/member/UDP/combat stillunfinished.

Verification: all80 Python tests pass, NOskips, with isolatedXvfb, real local
sockets and compiled Win64IPC test enabled via disposableWineprefix. That test
contains12cases covering actual productionprocess_job ->RPC->GameBridge->server,
LF/CRLF, exactnegative/simple/ORpair data, cancellation/disconnectcleanup,
malformedendpoints and errorownership untilhook_done. SyntheticWin64 ABI/query
fixture also passes, all6 Lua contracts pass; DLL/fixtures -Wall-Wextra-Werror.
No realgame/native scheduler/allocator executed by these standalonefixtures.
OriginalshippingSHA256reverified unchanged. Distribution53allowlistedentries,
archiveSHA25627ac6246bfccbc86d72c7ace1b64db08f14dfcde087cee7cb79169b6c36e0353.
Bothmanifests/archivepayload identityverified. No F5 repeatneeded to diagnose.

Latest implementation (2026-10-22): OPT-IN actual native search/cancel hook now
exists in lan/native/native_search.c and bundled native_search.dll/Lua. It is
OFF by default; set game-root SzeroLAN.json native_search:true, setup/update,
fresh launch BEFORE Online. main.lua early branch excludes ALL old F5/panel,
audit and SpNet behavior. This is not the full requested multiplayer solution.
The exact-image guarded helper asynchronously verifies SHA256, checks context
identity/idle task+19d6/session+40 and all28 service slots, then publishes an
immutable pinned selected-service vptr clone. Service-instance-wide, NOT
per-context; shared-context global quiescence remains unproven. No hot reload.
Native +90 copies bounded query values, yields via original native task
scheduler, worker sends loopback IPC -> bridge -> central native_search API.
Real cancellation deep-copies task+58 error; yield function defines AL ONLY
and MUST retain unsigned-char ABI. Borrowed query/settings/string ownership
stays native. +88 create returns tagged48B unavailable error; +98 join returns
PLAIN40B unavailable error. No fake empty success or native descriptors returned.
Compound queries explicitly fail, comparisons0..4 preserved not evaluated.
Search pending/cancel has generation isolation/disconnect cleanup/120sec cap;
one active search per process, multiple processes supported. Native session
directory/materializer are still NOT connected to this hook. Native session
results/create/join/member/channel/UDP bootstrap/combat remain unfinished.
No authentication/readiness/platform ownership checks changed; retained
platform methods may still contact services. Offline startup NOT established.

Server must update szero_lan.py AND native_search.py alongside existing tools.
Bridge ingame_client.py uses loopback NativeSearchRPC only for explicit opt-in.
Launcher retains pleasant address/port/name editor and preserves unknown JSON.
New installed game files: scripts/native_search.lua and native_search.dll;
main.lua changed. Full destination ledger below; installer preserves backups
and records18 changes on a fresh setup. Other mod DLL/scripts unchanged.
External shared/SZeroLinux installation was NOT modified. Shipping EXE hash
reverified unchanged. Do NOT claim real-game success or request old F5 pairing.

Verification:75 Python tests pass under isolated Xvfb, including actual helper
TCP protocol->GameBridge->LobbyClient->GameServer search/cancel; launches mocked.
All6 Lua contracts pass. Win64 DLL builds with -Wall -Wextra -Werror. Synthetic
Win64 C fixture passes in isolated fresh-prefix Wine using owned service memory
and fake native scheduler/error-copy callbacks, not the game. Covers all3
vtables/all28slots, actual CAS, guards, create/join canaries, query bounds,
borrowed inputs, hook cancellation, worker-error and busy paths. Real native
scheduler, compiled worker IPC in game, forced publication races and timeout
branch remain unverified. See analysis/native-search-implementation-findings.md.
New distribution:51 allowlisted entries, SHA256
9b0fcbd745aa01eb94c5433e831f6c19928e0b0fb713dd00ddb358f9823e7767.
Manifest/archive payload identity checked; no originals/configs/logs/online DLLs.

Latest construction implementation (2026-10-22): exact-build native factory
145943940 can copy a valid0xe8 descriptor into0x100 allocation with refcount
control at+e8. The two-word handle is descriptor/control, NOT itself the virtual
title session. Title factory145a93240->145a22b50 consumes that pair into0x698
wrapper;0x118 member wrappers BORROW descriptor nodes. Native member schema,
owner identity/capacity and canonical empty containers now recovered; see
native-descriptor-schema-findings.md/session-object-construction-findings.md.

Implemented SOURCE-ONLY lan/native/session_materializer.{h,c}: bounded data
inputs, exact static layouts, borrowed source strings/containers, original-ABI
factory callback, explicit profile1 empty-properties/empty-stream ONLY. Rejects
unsupported fields, unsorted/duplicate member order, duplicate IDs, wrong owner
count, invalid text/counts and overwriting owned output. Native callback is
NOT bound to game address; no DLL export, installed hook or game execution.
Factory copies synchronously; source uses own arena, never native-destruct
it. Output belongs to caller including native errors, never CRT-free it.

Server native_sessions.py now optionally accepts native_data on create and
native_member on join, materialization_profile1 on search; emits complete
pointer-free native_descriptor fields for that limited profile. Server assigns
IDs/order/owner, preserves supplied native identities/address/raw flags and
positional numeric values, rejects nonempty stream/properties and spoofed
ownership. Old requests remain compatible and searches are profile-isolated.
Member identities are NOT proven account-ID/display-name labels; preserve
legitimate source values, do not invent them or touch authentication. Current
installed game bridge never calls this API; source constructor is NOT a native
Online redirect. Production decode/provider hook, cancellation, member updates
and relay/channel lifecycle remain required. No further F5 test requested.

Verification:60 Python tests (21directory tests,5real TCPtests,3server-JSON-to-C
fixtures included), ASan/UBSan standalone constructor contracts, Win64 object
compilation pass. LeakSanitizer disabled because sandbox tracer prevents it;
do NOT claim leak checks. Fixtures use synthetic native factory, never game.
All existing loader/mod DLLs and original game files unchanged in this step.
Distribution now44 allowlisted entries, archive SHA-256
ff1d3e0dc127f7f49a972c6d7a54cbe9df84955ef0b679aef09ecbad54ef4073.
Server-only updates: szero_lan.py/native_sessions.py. Source-only constructor
and fixtures are included for development, NOT copied by installer into game.

Latest Quickmatch correction and partial implementation (2026-10-22): user
observes character/settings selection BEFORE search. Preserve that native
flow; do not force a second selection after sidecar pairing. Exact stage
negotiation remains unverified. Server now exposes a separate native_session
version1 create/search/join/leave directory via existing TCP protocol2, not
automatic queue/match_start. Copy lan/native_sessions.py beside szero_lan.py
on server machine; not into game. Strict two-member sessions, connection-owned
IDs, equality-only numeric filters, isolated wire partitions, disconnect/leave
updates; this is only a server foundation. Existing installed mod/bridge does
NOT call this API. Native provider hook, owned descriptor/session translation,
cancellation and channel/member lifecycle remain unimplemented; no native
Quickmatch/battle success claimed. Do not request another F5 run for this gap.
New join evidence proves localservice requires an existing process-tree record
and reference-counted active handles, not just the remote server session ID.
Verification: all44 Python tests pass under isolated Xvfb with real loopback
sockets (game launches mocked), plus all5 Lua contracts. New suite includes9
directory unit tests and4 real TCP tests with7 clients/3 independent sessions.
New bounded filter trace establishes comparisons0==,1<,2<=,3>,4>= signedint;
current wire profile intentionally only accepts explicit equality and rejects
unknown/compound filters. Wire partitions are our namespace, NOT proven game
enums. That prior distribution had40 allowlisted entries including3 new Python
files; both manifests/archive payload hashes verified. No game-side file changed
in this step. Original shipping hash reverified unchanged. The server change
does NOT yet make native Online send requests to it.

Latest supplied package now lives under online/DBSPZFix-Online/ (recursive
ignored-file inventory verified). All four Win64 DLL SHA-256 values remain
identical to the previously analyzed package, including protected OnlineFix64.
Reuse retained static evidence; a different folder is not a different build.
analysis/online-package-findings.md records this identity recheck; no game
patches or third-party installation were made.

Direct OnlineFix64.dll REA follow-up (2026-10-22): opened exact hash and
decompiled entry 0x181569390 and three successive targets. File-backed
.ofme2 chain reaches 0x1809e7b51 with computed indirect dispatch; Ghidra
reports bad-instruction truncation and unrecovered jump table. This is NOT
proof the module cannot be analyzed statically and NOT recovered network
hooks. Export OnlineFix RVA0x5faf0 is in unbacked .text; do not interpret
missing bytes as a return-only body (that finding applies to proxy winmm).
No execution/unpacking or runtime changes. See onlinefix64-static-trace.txt
and the follow-up in online-package-findings.md.

User supplied online/ package on2026-10-22 for static research ONLY, explicitly
not integration. Do not execute or install any of its DLLs, visit its shortcut,
or redistribute/stage it. Entire online/ is Git-ignored. Inspect only general
loader/network interoperability structure; exclude DRM, account-ticket,
ownership or DLC circumvention from the LAN implementation. OnlineFix64.dll
has unbacked original .text and high-entropy protected sections; imports alone
do not establish internal hooks or an offline backend. Keep findings bounded.
Completed static REA proxy-loader trace: winmm process-attach loads the system
winmm, resolves192 function targets, then reads dlllist.txt and loads its listed
modules. ExportOnlineFix is return-only, not the hook body. No protected DLL
execution/unpacking, auth/DRM bypass reconstruction, redistribution, or game
patch. See analysis/online-package-findings.md and recorded REA evidence IDs.
Independent new native findings: actualsearch1459c10b0->1458cc840->service+90;
Steam147b95320+90=1459277a0 callsSteam interfaces; local147b95400+90=14592ecc0
queries onlyprocess tree. Native success owns0xe8 descriptors transferred to
context+3b0. Not replaceable by JSONmatch ID. Configdc3 anddc4 have proven OSUDP
branches; dc1 is process-local registrytransport, NOT assumedPlainUdp. Mode
semantics beyondthis remainunknown. Bindaddress is ownedconfig+78 through
localservice+280/virtual+68. Contextlocalbundle switch is scopedcontext+8,
not globalplatformselection, but addresses live in sharedlocalbundle. Native
initializer guards prohibit blind reinit of activecontext (error0x411).
No functional nativeprovider hook or newgame/runtimepatch delivered in this
pass. Current installer/distribution remain unchanged. Remaining nativeABI/
lifecycle/transport work is in the two newfindings reports; moreF5tests are
not currently useful. Original shippinghash reverified unchanged.

Latest user correction (2026-10-22): the captured action at23:54 was native
Quickmatch, no error; the search remained active. Exact session trace
8375b55ce3cfd6f4abd765251eb50be3fa420ba7fd7923c2ac8e6422e49403f5
shows valid context identity, +63c 0->1 at23:54:35, task+19d6/field+665
0->2 at23:55:20, and no session+40 at sampled instants. A no-result search
can legitimately have no session yet; do NOT infer session-construction failure
or a network error solely from these snapshots. User requests implementation
of native search/result handoff, not another overlay test or passive collector.

Latest supplied F5 run (23:41 local, 2026-10-21) repeats server pairing and
zero registered SpNet commands, with native matching/online flags unchanged.
It supplies no new native-session evidence. The previous real Battle->Online
run did change setup/matching/online flags but had no native session internals.
User explicitly asks implementation and what evidence would help; do NOT
request another identical F5 run. An opt-in, bounded, read-only native session
capture is implemented to observe actual context/session presence during
the native menu path. This diagnostic is NOT a functional native LAN adapter.
Use Start-Native-Trace.cmd -> setup/update -> launch -> original Battle->Online,
one PC only, no F5, record local action/error times within five minutes. Needed:
session_trace_<instance>.jsonl beside main.lua plus UE4SS.log. No credentials,
packet dumps, raw pointers or game writes. Hash guard, title vtable/global
identity, 13 bounded reads/full snapshot, one poll/sec, 300poll/300second and
256record caps. Lua inactive on normal launch. Main calls only on game thread,
including inactive/unpaired sidecar state. Report boundary in
analysis/runtime-native-session-evidence-gap.md. Current provider/result ABI
and real-game runtime compatibility remain unresolved; do not claim redirect.
New static factory145a93240 ->145a22b50 allocates0x698 and consumes an owned
two-word service handle; it is not a plain match-ID string constructor.
Verification:31 Python tests, five Lua contracts and five synthetic decoder
tests pass. Native session fixture passes in isolated Wine; not a game test.
Current ZIP contains44 allowlisted entries, SHA-256
ff1d3e0dc127f7f49a972c6d7a54cbe9df84955ef0b679aef09ecbad54ef4073.
The earlier capture update installs main.lua (opt-in capture calls), session_trace.lua and
session_probe.dll only; preserves existing game config and originals. Installer
and tools/tests/docs are updated. External tested installation remains read-only.

Latest user direction (2026-10-21, after successful F5-open-v4 rendering):
stop expanding the overlay/native-widget prototype. Reuse Battle -> Online's
actual menu, lobby conditions, character/stage selection and DP rules with a
config-selected LAN backend. Do not merely redirect the title login/CDN host:
the native platform/session interface and transport require separate adapters.
The newest read-only external runtime snapshot (20:56:35 UTC) found 5,426
occupied console entries, all read, a valid control entry, zero spn entries,
and none of the five attempted command names or relevant suffix variants.
Thus those preset commands are NOT a usable registered entry in that observed
menu state. No native battle/session start was observed. Server pairing at
22:56:33 local time matches this run. See the native-online follow-up reports;
do not ask the user to repeat the same overlay pairing as a networking fix.
Additional latest requirement: a pleasant client-side server-address editor,
not manual JSON editing. Implement in setup_launcher.py, preserving unknown
SzeroLAN.json fields; address, port, name saved for the next launch. This is
separate from native online integration and must not be described as its fix.
Implemented: setup_launcher.py now has address/port/name fields, Save, and
auto-save before launch. Reads do not rewrite configs; saves reread/preserve
unknown options and are atomic. Syntax validation is offline/no DNS. Active
sessions block saves to avoid a displayed-versus-connected address mismatch.
Nine config/window tests cover this, with all game/bridge launches mocked.
New deeper native tracing follows scheduled matching into context session
creation: 145a7f7f0 -> 145a3d770 -> 1459f0af0 -> 1459f9450 -> task ctor
145a24b60/vtable147ba65c0 -> leaf145a69410 ->145a09a50 ->145a7f460
->145a14560 ->145a67260 ->14599c540. One creation branch enters
1459b93a0 ->1459ace60 ->145965f30 ->145964d30. This checks context+63c,
1459b28b0 and context+108 readiness (else0x413), requires no existing+40,
selects service via context+667, and calls1458c84a0. That wrapper requires
service virtual+48 then invokes virtual+88; local vtable147b95400+88 is
14592c830. Successful tagged results traverse145960b20 ->1459891a0,
which obtains/installs context+40 via virtual+28 and continues additional
member/channel setup. Do NOT write+40 directly or fabricate success. Native
ABI/ownership/search/join/leave and safe LAN-only provider installation remain
unimplemented. See analysis/native-online-backend-findings.md for evidence.
Native binary readers/writers also confirm inner tag type<<2 and MSB-first
base128 integers; selected IDs3/9/28 have bounded offline decoding only.
Complete UDP framing and type semantics remain unresolved. Dummy service
creates process-local tree records, not a central network lobby by itself.
Verification for this update: 31 Python tests pass under Xvfb (loopback server
fixtures; game starts mocked), all four Lua mock contracts pass, and five
offline synthetic decoder tests pass. Revised distribution contains32 entries
total:31 allowlisted files plus lan/SHA256SUMS.txt; no runtime
configs/logs/caches/game originals. ZIP SHA-256:
862f2ca0c0fe3b81dd58df2efed75264b94d209aac826d7ddc5ca1690c47135c.
Only client-tools setup_launcher.py changes runtime behavior in this update;
no mod script/DLL, server code, original game or external install changed.

Latest confirmed UI fix: own-object runtime probes on 2026-10-21 reproduce the
unsupported UFunction:ForEachProperty call in pinned UE4SS3. TextBlock, FText and
SetText succeed; function lookup succeeds; UFunction property iteration fails.
Read-only own-process metadata verifies UIOnlyEx NumParms4/ParmsSize18 and
GameAndUIEx NumParms5/ParmsSize19 at discovered offsets +b4/+b6. Removed iteration
from panel.lua AND native_menu.lua; use exact-build four/five argument calls.
Panel revision=f5-open-v4 now emits bounded pre-call steps and composes stage
outside xpcall too: the user's v2 runtime lost the handler's formatted result.
Mocks previously invented a UFunction iteration API; they now reject it.
See analysis/widget-input-runtime-findings.md. This is a reproduced API fix,
NOT verified rendering, full native menu integration, or a networking fix.
Temporary workspace probe bootstrap files were removed. External installation
was not changed. This update changes installed panel.lua and native_menu.lua.

Latest user clarification: there is NO crash or black screen; F5 simply shows
no menu. Do not repeat the prior speculative black-screen explanation as fact.
Supplied external UE4SS.log at 2026-10-21 20:20:09 UTC records UMG creation then
`UMG update failed: function: ...`. The failed API is NOT identified by that
message. This run uses panel.lua (not opted-in native_menu.lua), and no match
assignment/native audit appears. Server connections alone do not imply pairing.
The pinned loader DLL and actual log confirm Key.UP/DOWN/LEFT/RIGHT are not the
correct arrow names: panel.lua now uses *_ARROW. The former mock had invented
the wrong names and was corrected. Panel revision=f5-open-v2 logs F5 requests,
individual open/input stages and traceback even for non-string Lua errors.
Text is populated before showing/focusing; failed opens collapse the own root
and best-effort restore input, stop polling until another explicit F5 press,
and cannot send blind commands while not shown. Regression mocks inject both
property-iteration and focus errors and exercise retry/rollback. This is NOT a
runtime-proven fix for the failing UI API; the next log must identify the stage.
External tested installation was read only, not patched. Installer update for
this correction changes only the installed scripts/panel.lua.

Current build adds an opt-in native-widget prototype: set `native_menu: true`
in game-root SzeroLAN.json, then launch through the setup window. Default is
false. main.lua chooses native_menu.lua instead of panel.lua; native root and
buttons use exact SSMenuManager/SSMenuButton classes. A separate menu_bridge.dll
binds only newly created owned widgets after image, class/vtable, ownership,
thread, request and prologue checks. Unlike console_probe.dll this UI helper
DOES invoke one native UI function. It does not initialize a session, invoke
authentication, alter production menus, or perform travel. Native main-menu
controller/scene-stack integration is still absent. Bare widget lifecycle and
real navigation remain unverified and may crash; keep disabled by default.
Lua errors disable the experiment and best-effort restore input; pcall cannot
recover native crashes. 25 Python tests, four Lua mocks and both native Windows
fixture executables pass; these are NOT game UI or combat tests.

Investigation continuation (2026-10-21): user confirms Linux uses system Wine
and `/home/maxinator/.wine` through our CMD/launcher; the other PC is Windows.
REA target identity matched the supported EXE; focused MCP decompilation timed
out after 300 seconds. Old `/tmp/szero-*` projects are gone in this environment.
Fresh selected-function Ghidra recovery now works without global analysis via
`analysis/scripts/SzeroBounded.java` (PE .pdata, chained unwind fragments).
Do not cite initial one-byte body reports as complete. Current projects are
`/tmp/szero-menu-ghidra/Menu` and `/tmp/szero-spnet-ghidra-e6KgAe/Spnet`.
New findings: native menu states 1c->1d->optional1e->1f actually submit travel;
local and Steam service bundles are constructed separately. Native sends still
require an initialized channel. No runtime channel bootstrap/selection success
is established. Full details: native-menu-integration-findings.md and
plainudp-bootstrap-findings.md. Do not confuse MultiplayerErrCode conversion
functions with a contextMode parser.

One bounded startup using the user's default Wine prefix, separate Xvfb and
network namespace exited3. Its UE4SS log was subsequently updated at
2026-10-21 16:11:25 UTC: loader/mod startup and event-loop start occurred, but
there was no configured runtime assignment or world sample in that test.
Therefore that log does not prove whether a main-menu world was reached.
Wine also reported unimplemented `ntoskrnl.exe.IoOpenDeviceInterfaceRegistryKey`;
its attribution to the game exit is NOT established. No drivers/platform checks were
disabled, original game files changed, or external shared installation modified.

The optional new console audit DLL is read-only, own-process, exact-hash guarded;
it invokes no engine methods or network functions. Hashing is asynchronous;
bounded registry reads run once on the game thread after pairing. It emits
`console_probe_<instance>.json` next to scripts and prints it to UE4SS.log.
Missing helper disables only this diagnostic. Registration is not acceptance;
unregistered objects may be retained and header consistency is not atomicity.
Live game compatibility still needs runtime verification. Native Windows fixture
tests and Lua mocks do not establish it.

Latest correction (2026-10-21): user reported severe lag, F11 conflicting with
fullscreen, and still zero game packets. Supplied UE4SS log confirms native
transition2/matching0/online flags false after server pairing. UI/performance
changes do NOT solve native session initialization. main.lua now caches only
controller/engine paths and resolves fresh handles; global discovery occurs
only on a missing context (one-second retry). Removed recurring SSGameInstance,
roster and battle-state global scans. Native getters use world.OwningGameInstance
or engine.GameInstance. Panel is initially closed, uses full-viewport anchors,
UIOnly focus on open and GameAndUI on close, and skips unchanged SetText calls.
F5 opens/closes; Up/Down selects action, Left/Right selects lobby, Enter acts,
Escape closes. No F11 binding or old global F-key action bindings. No cached
UObject wrappers across frames. The custom UMG menu is NOT registered in the
game's own menu/online state machine and has no controller-native integration.
Performance impact and native focus behavior still require a real game test.
Regression contracts now assert zero hot-path global scans over100 polls,
zero closed-menu UObject work, unchanged-text suppression, full-screen layout,
F11 absence, and both input API signatures with/without bFlushInput.

Build a private, offline-LAN multiplayer replacement for the Windows version of
DRAGON BALL: Sparking! ZERO. Clients must select the LAN server with a normal
configuration value such as `server_address = "192.168.1.20:PORT"`. Do not
require a hosts-file edit, DNS change, or Internet service.

Latest user requirements: one central server must handle multiple clients,
lobbies and matchmaking. No shared secret, passwords, user-selected player
numbers, or manually configured peer addresses. Both combatants are ordinary
clients of that server. Multiple independent matches must be possible. The
user will provide game logs after testing the revised implementation.
The user also requests bundled loader binaries and painless offline setup.
Use the pinned official UE4SS basic release already in `lan/vendor`; setup
must preserve existing loaders and user mods rather than replacing them.

Latest additions (2026-10-20): put server IP/hostname, port and player name in
`SzeroLAN.json` at the game root. Move lobby/queue controls into the game;
external window should offer setup/update and launch only. A paired match
must eventually enter native character/stage selection before combat. This
session/selection integration is NOT implemented or verified yet. User asks
for a deep investigation, including other mods and the normal online client
flow. Server wildcard IPv4 bind `0.0.0.0` is explicitly authorized (clients
still use an actual destination IP). Keep a private-LAN default recommendation
and explain unauthenticated exposure; do not reject wildcard binds.

User requested Git initialization with actual game files ignored. Repository
initialized; no commit made. Do not stage/commit original game binaries,
archives, saves, logs, local config, or generated runtime data. Keep .gitignore
and this handoff up to date. The pinned official loader ZIP is an intentional
redistributable dependency, not an original game artifact.

This is an interoperability/modding project for a user-controlled LAN. Do not
disable or bypass DRM, anti-cheat, platform ownership checks, or account
authentication. Keep any platform-independent LAN transport separate from
those systems.

## Workspace and target identity

- Workspace root:
  `/run/media/maxinator/813d5e8b-46f5-4be2-8485-bbc7c8e57dec/Szero`
- Game root:
  `DRAGON BALL - Sparking! ZERO/`
- Launcher executable:
  `DRAGON BALL - Sparking! ZERO/SparkingZERO.exe`
- Shipping executable:
  `DRAGON BALL - Sparking! ZERO/SparkingZERO/Binaries/Win64/SparkingZERO-Win64-Shipping.exe`
- Shipping executable SHA-256:
  `e54e79e756f79719f09915078a37b6e87c23d32ecaaaa2f485d1a048ba198e55`
- Companion `.rne` PE SHA-256:
  `ed0410d5e1bad641bc2f508811f90f4bbbe23e9a803668cfe03be535f13ec7bf`
- Unreal Engine version: `5.1`
- Main package AES key:
  `0xb2407c45ea7c528738a94c0a25ea8f419de4377628eb30c0ae6a80dd9a9f3ef0`

Do not assume offsets are portable to another executable hash. Any binary patch
must first verify the exact SHA-256 above and fail closed on a mismatch.

## Available tooling

- `FModel.exe` is in the workspace root.
- FModel SHA-256:
  `d9c835d9788565bbe185d99ca09207929df5d8111f87e55afb1f21e21e764ea0`
- FModel version observed from the binary/runtime log: `4.4.4.0`.
- It targets .NET Desktop Runtime `10.0.10`; the user's default Wine prefix has
  .NET `10.0.13` and runs it successfully.
- The default Wine prefix already contains a working FModel profile. A clean
  temporary Wine prefix does not have the required .NET Desktop Runtime.
- FModel confirmed `GAME_UE5_1 (DesktopMobile)`, mounted 47/48 archives, accepted
  one AES key, and indexed 417,945 files. The main two IoStore containers are
  `pakchunk0-Windows.utoc` (297,602 files) and
  `pakchunk1-Windows.utoc` (104,682 files).
- FModel's saved profile points at a second game directory under
  `/run/media/maxinator/shared/SZeroLinux`. The shipping EXE and
  `pakchunk0-Windows.utoc` in that directory have the same SHA-256 values as
  the workspace copies, so observations from that mounted profile apply to the
  exact target build. Do not distribute or install files from the profile.
- A read-only load of `pakchunk0-Windows.utoc` completed and exposed the
  `SparkingZERO/Content` and plugin trees. No asset was exported or modified.
- REA is connected and selected Ghidra 12.1.2 for the native PE. Opening the
  shipping executable produced shipped-artifact identity, but a broad regex
  string search exceeded the MCP call's 300-second timeout. Do not repeat the
  same broad Ghidra query unchanged. Prefer focused searches, package evidence,
  PE/import inspection, or a retained/saved analysis route.

## Confirmed static findings

These are observations from the exact shipping executable, not runtime claims:

- The executable contains Steam interface strings including
  `SteamMatchMaking009`, `SteamMatchMakingServers002`,
  `SteamNetworkingMessages002`, `SteamNetworkingSockets012`, and
  `SteamNetworking006`.
- It imports `WS2_32.dll` and `WINHTTP.dll`.
- Online/debug strings include:
  `EDebugOnlineBtl_ServerApiType::DummyAuth`,
  `EDebugOnlineBtl_ServerApiType::Skip`,
  `EDebugOnlineBtl_ServerApiType::Normal`, `+connect_lobby`,
  `dummy_session_`, `dummy_session_member_`, `SessionP2pDead`,
  `PlatP2pConnNotFound`, `OnlineSession`, and `DumpOnlineSessionState`.
- The executable contains `/Script/CoreOnline` and `ECoreOnlineDummy::Dummy`.
- Observed Bandai Namco account strings include
  `https://account.bandainamcoid.com/bnlink/%s.txt`,
  `bnid/get_consumer.php`, `bnid/post_consumer.php`, and
  `bnid/delete_consumer.php`.
- These strings strongly suggest a Steam/platform session and P2P layer plus a
  separate title/account service, but static strings do not establish the
  complete handshake, packet format, or whether battle traffic is direct P2P.

## Required next evidence

Current milestone: `lan/` contains a central TCP/UDP lobby server, an identical
multi-client desktop launcher, JSON address config templates and automatic
UE4SS Lua adapter. The previous secret-based per-pair relay is replaced by
protocol version 2. There are no user-selected player roles. The server assigns
the game's internal two-player join order per match. Real socket tests exercise
six simulated clients, two simultaneous matches and another waiting lobby.
Additional tests cover lobby waiting-list rotation and disconnect cleanup.
All twenty-four Python tests and both mocked Lua adapter/panel tests passed on
2026-10-20; GUI tests used an isolated virtual display. This includes fresh
offline setup from the real bundled loader archive, preserving existing files,
hash guards, unrelated proxy conflicts, backups and rollback. These supersede
the previous ten-test and five-test relay validation.
No game process was used for these automated tests. User-supplied game logs
are separate runtime evidence. The adapter is NOT yet a complete
multiplayer replacement or integrated replacement for the in-game menus.
Latest user logs: the loader/mod loaded, server matchmaking succeeded, but the
old adapter called UEHelpers.GetPlayerController, which requires a valid
player-controlled Pawn. Main-menu controllers have no Pawn; UE4SS.log reported
"No PlayerController found" and contained no Issued command lines. Read-only
evidence came from `/run/media/maxinator/shared/SZeroLinux/lan/` server/client
logs and that installation's `Win64/UE4SS.log`. UE4SS timestamps are UTC, while
the server logs were local UTC+2. Do not mistake the offset for separate runs.
No changes were made to that external installation.

The supplied second test now verifies the revised controller lookup inside
the game: all five Issued lines appear, with no controller exception. It does
NOT verify command acceptance. Both tested pairings stay in Korat_P with an
already-existing battle-state object and no first-game-packet log entry.
See analysis/runtime-test-2026-10-20.md for source hashes and bounded findings.

The revised main.lua removes the UEHelpers dependency: prefer
LocalPlayer.PlayerController, then an explicitly local live PlayerController,
then GameEngine.GameViewport.World. No Pawn check. UObject lookup and command
issuance occur on the game thread. The mock tests cover the exact no-Pawn
regression; the controller lookup is now runtime-verified by that log. The adapter also writes bounded
JSON diagnostics beside its runtime file; LobbyClient reads matching revision
and match only, logs reports and displays stages in the GUI. First actual game
UDP packets are logged and packet counts are displayed separately. No adapter
status or packet count establishes successful combat synchronization.

The highest-priority next steps are proving acceptance of the SpNet commands,
initializing the game-owned session context, and entering native character/
stage selection before combat. Do not repeat global analysis. A loaded battle
object and a sidecar match_start are not game-transition success markers.

Current UI prototype: Start-Client.cmd now opens setup_launcher.py (two actions
only). It creates SzeroLAN.json at the game root if absent, preserves it on
updates, starts a per-instance hidden ingame_client.py bridge, and launches the
game with SZERO_LAN_INSTANCE. The UMG panel constructs an asset-free UserWidget
tree on the game thread; all cross-frame references are paths/strings, with
fresh StaticFindObject lookups. No cached widget wrappers across travel.
Latest controls: F5 toggle; Up/Down action, Left/Right lobby, Enter select,
Escape close. No F11. The former overlay drew in the user's supplied test;
the revised full-screen/input-focused menu remains mock-tested only.
The old launcher.py remains an optional diagnostic desktop UI. The hidden
bridge performs TCP/UDP work; Lua performs no blocking network I/O. Native
selection entry remains explicitly unimplemented; do not claim otherwise.
Read-only native getter/object-marker diagnostics operate while waiting or
assigned; no online login, normal matchmaking, or travel is started by them.
The six GameInstance getter bodies were verified as pure field reads in the
exact shipping executable, including non-const GetBattleSetupStartMode. See
analysis/game-instance-getter-thunks.txt; native diagnostics do not assign any
of those fields.

New confirmed static evidence (direct Ghidra, partial global analysis):

- `analysis/plainudp-trace.txt`, `0x1421d5570`: compiled PlainUdp presets
  issue `spn.multiplayerContext.contextMode PlainUdp`,
  `myDummyMatchingJoinOrder`, `myDummyP2pAddress`,
  `dummyPeerP2pAddresses`, then `spn.multiplayerContext.apply`.
- `0x140967910`: registers `SS.BattleSyncLocalOnlineBattle` with documentation
  `-1:none 0:host 1:guest`; the adapter does not set this variable because its
  effect on battle entry is still unresolved. Backing variable: `0x1484bff88`.
- `analysis/focused-results.txt`, `0x1424c0600`: parser maps DummyAuth=0,
  Skip=1, Normal=2 into `0x14870adb9`. Debug battle code later issues the
  `setServerAccessMode` commands. This is not proof of a functional LAN mode.
- P2P error-string xrefs lead to error conversion routines, not a transport.
- `ServerURL` belongs to `HttpNetworkReplayStreaming`; do not treat it as a
  matchmaking endpoint override.
- `0x145cae020` initializes title-service defaults including login.php and CDN
  URLs. `0x1427acca0` converts a host FString and calls `0x145add0a0`, a wrapper
  writing the service object field at +0x68. No user config entry established.
- The newer battle-entry reports trace console delegate tables
  `0x146d2a130` and `0x146d2a300`: callbacks `0x1424bce80` and `0x1424bcfd0`
  call argument parsers `0x1424c0600` and `0x1424c04b0`. These set debug
  settings/global auto-start flag `0x14870adb6`. The observed consumer is
  debug setup tick `0x1424cd1d0`, which calls `0x1424c5370`. That flow assumes
  an existing initialized debug setup manager; it is not a demonstrated
  main-menu entry trigger. State callbacks `0x1424c8200` through
  `0x1424c8570` configure helper/session state and eventually travel after
  writing battle settings. Do not blindly issue the auto-battle command or
  travel to a guessed map. Some surrounding debug commands change validation
  behavior and are deliberately not included in this adapter.

Follow-up: inspect references to `0x1484bff88`, and inspect actual game logs
after the automatic adapter applies a server match assignment. Establish socket binding and input synchronization
before adding menu redirection. UE4SS v3.0.1 basic loader binaries are now
bundled, but compatibility with this exact game build still needs runtime testing.

Focused follow-up reports are indexed in `analysis/selection-entry-findings.md`.
Exact-build `SSMainMenuLevelScriptActor:StartOfflineBattle` and `StartQuickMatch`
wrappers resolve an object then end at a compiled `ret 0` stub; do not use them
as match-entry triggers. `TestLevelTransition(enum,int32)` has real scene-data
and state-machine behavior, but requires loaded scene/subscene indices and is
not yet a validated LAN selection trigger. `SetTransitionMode` writes context;
the normal selection callback separately submits travel after setting flags.
SpNet's generic dynamic console-registration bridge and native UDP bind/send
wrappers are present. Literal PlainUdp preset strings do not prove those exact
console objects were registered/accepted. `.value`/`.exec` suffixes apply only
to combined value-and-callable metadata nodes, not all SpNet commands.

1. Export/search package-side configuration and Blueprint assets related to
   `CoreOnline`, `OnlineSession`, `DebugOnlineBtl`, `ServerApiType`,
   `DummyAuth`, `OnlineRoom`, and `OnlineEnable`.
2. Focus native xrefs on `+connect_lobby`, `dummy_session_`,
   `SessionP2pDead`, `PlatP2pConnNotFound`, and the debug server-API enum.
3. Determine whether a built-in dummy/skip backend path can be enabled through
   configuration or a cooked asset. Prefer that over binary patching.
4. If static evidence is insufficient, capture only user-authorized local test
   traffic/process behavior. Do not contact or impersonate production services.
5. Establish the minimum viable architecture:
   - discovery/rendezvous server only if battles are already peer-to-peer;
   - LAN relay if the platform transport cannot address local peers directly;
   - title-backend emulator only for endpoints actually required to enter and
     complete a private match.
6. Add a config-driven client adapter/launcher. It must parse a hostname or IP
   plus port and resolve/connect directly; never edit the hosts file.

## Implementation and safety requirements

- Prefer new sidecar files, a loader-supported mod/plugin, or reversible cooked
  overrides. Patch the shipping EXE only when there is no less invasive route.
- Never overwrite the original executable or package in place. Put generated
  client artifacts under a dedicated distribution directory and include a
  verifier/installer that backs up and hashes any replaced file.
- Bind the LAN server to an explicit interface from configuration. Default to
  a private/LAN address, not all public interfaces.
- Add protocol versioning, bounded packet sizes, timeouts, and no trust in
  client-supplied lengths or player identity.
- Do not embed the package AES key in the runtime server/client unless package
  mounting is genuinely required at runtime. It is currently an analysis input.
- Keep observed behavior, inferred behavior, and implementation choices clearly
  separated in reports and code comments.

## Patch ledger

Update this table immediately whenever a file is created, generated, copied,
or patched. The `Install destination` must be relative to the game root or say
`server machine only`. This is the authoritative handoff/install list.

| Workspace file | Status | Install destination | Purpose |
| --- | --- | --- | --- |
| `analysis/runtime-native-observed-stream-fix3.md` | New supplied-run/exact observed stream report | Do not install | Reported RVA0x6d15840, recovered embedded layout, targeted capture and runtime limits |
| `analysis/native-observed-stream-fix3-trace.txt` | New bounded static recovery | Do not install | Constructor/factories and original getter/table bytes for exact observed class |
| `analysis/scripts/find_rip_lea.py` | New read-only exact-hash static candidate scanner | Do not install/distribute | Bounded .text RIP-LEA matches for one selected target; candidates require disassembly confirmation |
| `analysis/runtime-native-stream-refusal-fix2.md` | New matching-run and stream-layout report | Do not install | Specific stream refusal, missing vector capture, observed-versus-inferred boundary and verification |
| `analysis/native-vector-stream-fix2-trace.txt` | New bounded exact-build static evidence | Do not install | Vector constructor, copy boundary, original vtable/getter bytes; not game execution |
| `analysis/runtime-native-create-refusal-fix1.md` | New runtime/ownership correction report | Do not install | Distinguishes reported crash from observed refusal, original caller cleanup and native-only defaults |
| `analysis/native-create-ownership-fix1-trace.txt` | New focused exact-build Ghidra recheck | Do not install | Create wrapper always cleans inputs; Steam+a0 unsupported does not consume; static only |
| `lan/native_session_transactions.py` | New server runtime | Server tools only, beside szero_lan.py | Invisible prepare, stable-ID commit, reserved slots, generation/member-token abort fencing and match retry |
| `lan/build_bundle.py` | New reproducible explicit-allowlist builder | Tools folder only; never game scripts | Builds/checks manifests and payload-identical distribution without scanning originals/runtime files |
| `lan/native/native_session_provider.inc` | New linked C dispatcher | Source only; compiled into scripts/native_search.dll | Actual worker-to-native create/search/join handoff, staged commit, native allocator vector and bounded quarantine |
| `lan/native/native_session_frames.inc` | New bounded native-thread frame cache | Source only; compiled into scripts/native_search.dll | Service-keyed unchanged-snapshot suppression preserves consumed cursors; explicit settings still apply |
| `lan/native/native_session_lifecycle.inc` | Updated linked C lifecycle | Source only; compiled into scripts/native_search.dll | Borrowed create/match/settings inputs stay caller-owned; flags, leave, original queue, periodic member diff and teardown |
| `lan/native/native_session_transport.inc` | New linked transport gate | Source only; compiled into scripts/native_search.dll | Selected owned service, idle OSUDP/12-slot validation, bounded receipt and guarded byte CAS; no active reinit |
| `lan/native/native_session_search.h` and `.c` | New native-owned search vector | Source only; compiled into scripts/native_search.dll | Finite zero/one snapshots using original allocator/deep-copy/release, no fake pending success |
| `lan/native/test_native_session_search.c`, `lan/test_native_session_search.py` | New synthetic native search tests | Do not install | Owned vector layout, bounds, ownership and errors |
| `lan/native/test_native_session_ipc.c`, `lan/test_native_session_bridge.py` | New actual C-worker integration fixtures | Do not install | Real RPC/bridge/TCP path, synthetic native callbacks, join/match/cancellation/quarantine and reconnect ports |
| `lan/native/test_native_session_lifecycle.c`, `lan/test_native_session_lifecycle.py` | Updated actual-include lifecycle fixtures | Do not install | Caller-owned settings including refused create remain unchanged; original queue, flags, diff, readiness and teardown; synthetic callbacks |
| `lan/test_native_session_install.py` | New synthetic publication/rollback runner | Do not install | All three original vtables/new slots, cache-empty guard and idle transport rollback |
| `lan/test_native_session_rpc.py` | New bounded loopback protocol tests | Do not install | SESSION3 values, busy-match retry, late commit cancellation, mailbox ordering and settings preservation |
| `lan/test_native_session_transactions.py` | New transaction unit tests | Do not install | Reservations, capacity, stable IDs, conditional abort, flags and atomic match policy |
| `lan/test_native_session_transactions_wire.py` | New real TCP/UDP transaction tests | Do not install | Invisible prepare, disconnect cleanup, same-room member-token fencing and two independent routes |
| `lan/test_native_server_ports.py` | New port-allocation tests | Do not install | Retry ephemeral UDP/TCP collision only, preserve explicit bind ports and validate native ports |
| `analysis/native-provider-transaction-v4-findings.md` | New exact-build implementation/limitations report | Do not install | Flags correction, staged ABI, adjacent callbacks, mandatory native task queue and verification boundary |
| `analysis/native-provider-flags-v4-trace.txt`, `native-provider-extra-v4-trace.txt`, `native-provider-invite-v4-trace.txt`, `native-provider-queue-v4-trace.txt` | New focused static evidence | Do not install | Exact original metadata, generic invite and service task queue bodies; not runtime proof |
| `analysis/native-settings-leave-v4-trace.txt`, `native-settings-leave-inner-v4-trace.txt` | New retained bounded Ghidra traces | Do not install | Settings move/consumption, native cache removal and original readiness; decompiler output, not source |
| `analysis/native-session-v3-integration-status.md` | Updated implementation handoff | Do not install | Linked experimental adapter, verification boundary and unresolved real-game progression |
| `analysis/native-session-lifecycle-v3-findings.md` | New exact-build lifecycle contract | Do not install | Create ID-string result, base handle cache and native in-place member refresh |
| `analysis/native-session-lifecycle-v3-trace.txt` | New bounded static trace | Do not install | Create/join/cache callbacks and output ownership |
| `analysis/native-session-lifecycle-v3-refresh-trace.txt` | New bounded static trace | Do not install | Original descriptor diff/update, events and member node preservation |
| `analysis/native-session-lifecycle-v3-flags-trace.txt` | New exact-build flag evidence | Do not install | Original local-create member flags and descriptor initialization |
| `analysis/native-udp-bootstrap-v3-findings.md` | New exact-build transport contract | Do not install | Post-platform channel configuration and idle-channel guard |
| `analysis/native-udp-bootstrap-v3-trace.txt` | New bounded static trace | Do not install | OSUDP factory, bind callback and original bytes |
| `analysis/native-session-wire-v3-findings.md` | New exact-build settings contract | Do not install | Bounded opaque stream capture/copy, cursor limits and unsupported property variants |
| `analysis/native-session-wire-v3-trace.txt` | New bounded static trace | Do not install | Concrete stream, native settings and identity-pair layouts |
| `lan/native/native_session_wire.h` | Updated linked capture types | Source only; compiled into native_search.dll | Three exact stream layouts including observed embedded class and scalar refusal metadata |
| `lan/native/native_session_wire.c` | Updated linked bounded settings capture | Source only; compiled into native_search.dll | Separate inline/vector/embedded readers, small stack/private heap, scalar diagnostics and unchanged output on refusal |
| `lan/native/test_native_session_wire.c` | New synthetic settings fixture | Do not install | Own-memory capture bounds and profile2 stream construction |
| `lan/test_native_session_settings.py` | Updated fixture runner | Do not install | Compile/run settings fixture plus Win64 capture-stack ceiling; no game |
| `lan/native/native_session_adapter.h` | New source-only provider callbacks | Do not install into game | Correct create ID and join error ABI, explicit trusted callbacks |
| `lan/native/native_session_adapter.c` | Updated linked lifecycle core | Source only; compiled into native_search.dll | Staged native ownership, cache commit/abort, quarantine and in-place refresh |
| `lan/native/test_native_session_adapter.c` | New synthetic lifecycle fixture | Do not install | Output variants, ordering, native error ownership and refreshed descriptor consumption |
| `lan/test_native_session_adapter.py` | New fixture runner | Do not install | Compile/run lifecycle fixture with synthetic callbacks |
| `lan/native/native_lan_transport.h` | New source-only transport contract | Do not install into game | Explicit verified-image/native-thread callback gates |
| `lan/native/native_lan_transport.c` | Linked guarded transport core | Source only; compiled into native_search.dll | Exact idle context/channel checks and loopback bind value; no active reinitialization |
| `lan/native/test_native_lan_transport.c` | New synthetic transport fixture | Do not install | Guard failures, expected-byte mutation and inline result canaries |
| `lan/test_native_lan_transport.py` | New fixture runner | Do not install | Compile/run native transport gate fixture |
| `lan/test_native_sessions_v2.py` | New server profile tests | Do not install | Exact numeric/OR predicates, streams, membership updates and profile isolation |
| `lan/test_native_session_transport.py` | New real TCP/UDP session test | Do not install | Five clients/two independent native directory sessions, relay isolation and revocation; not game combat |
| `lan/native_session_codec.py` | Bounded live RPC value encoder | Client/server tools only | Strict SESSION3 descriptor frame from profile2 DTO, used by native session RPC |
| `lan/native/native_session_codec.h` | New source-only descriptor codec | Do not install into game | Owned bounded parser output and rebased value views |
| `lan/native/native_session_codec.c` | New source-only descriptor parser | Do not install into game | Strict ASCII/data/count validation, no native pointer transfer |
| `lan/native/test_native_session_codec.c` | New parser fixture | Do not install | Actual C parser and owned-data canary/bounds contracts |
| `lan/test_native_session_codec.py` | New server-to-C fixture runner | Do not install | Real directory DTO through Python encoder and compiled C parser |
| `lan/native/native_session_host.h` | New guarded Windows callback binding API | Do not install into game | Hash/thread/image/service/owned-vptr contract |
| `lan/native/native_session_host.c` | Updated linked Windows host binding | Source only; compiled into native_search.dll | Verified native function destinations, factory/cache/diff/release and owned string cleanup |
| `lan/native/test_native_session_host.c` | New synthetic Win64 host fixture | Do not install | Negative host guards and owned synthetic pair layout checks; no game callbacks |
| `analysis/native-search-cancellation-join-trace.txt` | Generated bounded ABI trace | Do not install | Different create/search tagged versus join plain-error layouts and caller-owned inputs |
| `lan/native/native_search.c` | Updated experimental native session dispatcher | Source only; compiled DLL installed below | Exact-hash service vptr, native result ownership, cooperative waits and worker-only IPC; runtime battle unverified |
| `lan/ue4ss/SzeroLAN/scripts/native_search.dll` | Rebuilt experimental v3-fix1 helper | `SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/native_search.dll` (or existing loader's Mods tree) | Borrowed-settings ownership correction, categorical capture refusal; native-only normal launcher, no original executable patch |
| `lan/ue4ss/SzeroLAN/scripts/native_search.lua` | New opt-in loader | Same scripts folder as main.lua | Game-thread helper initialization/status; excludes legacy F5/console path when enabled |
| `lan/native_search.py` | Updated bounded IPC and legacy registry | client tools and server tools, beside szero_lan.py | Session transactions, finite snapshots, complete supported settings, generation fencing and ordered mailbox; legacy compatibility |
| `lan/test_native_search.py` | New loopback/native-query tests | Do not install | Native request bounds, cancellation, stale generations and IPC cleanup |
| `lan/test_native_search_wire.py` | New end-to-end bridge/server tests | Do not install | Actual loopback helper IPC through bridge to server search/cancel; no game calls |
| `lan/native/test_native_search_ipc.c` | New compiled IPC fixture | Do not install | Real production C socket/query helpers to Python loopback under isolated Wine, no game |
| `lan/test_native_search_compiled.py` | New opt-in compiled client integration tests | Do not install | Wine-built C IPC to real bridge/server, not hand-written protocol text |
| `analysis/native-compound-filter-findings.md` | New exact-build query findings | Do not install | Flat OR-pair predicates, layout/ownership/evaluation semantics and limits |
| `analysis/native-compound-filter-trace.txt` | New retained static trace | Do not install | Selected Ghidra/PE assembly supporting compound-filter layout |
| `analysis/runtime-native-search-2026-10-22.md` | New runtime evidence and fix report | Do not install | Separate client timelines, reproduced Wine parser bug, compound handoff fixes and limits |
| `analysis/native-search-implementation-findings.md` | New implementation handoff | Do not install | Native hook path, verified contracts and explicit remaining runtime/session gaps |
| `lan/test_native_search.lua` | New loader contract tests | Do not install | Game-thread helper calls, opt-in and bounded changed-status reporting |
| `analysis/native-search-cancellation-findings.md` | New exact-build cancellation contract | Do not install | Borrowed query ownership and cooperative native wait/error propagation |
| `analysis/native-search-cancellation-trace.txt` | Generated bounded native trace | Do not install | Current task, cancellation and stack-switch implementation proof |
| `analysis/native-provider-installation-findings.md` | New exact-build static installation report | Do not install | Service selector, full vtable extent, title initializer callsite and scope constraints |
| `lan/test_session_materializer.py` | New server-to-C data fixture | Do not install | Real server response values through reconstructed C layout and synthetic native factory, not game execution |
| `analysis/native-descriptor-schema-findings.md` | New exact-build field schema | Do not install | Settings, capacity, members, owner identity and transferable-data boundaries |
| `analysis/native-descriptor-construction-trace.txt` | Generated bounded native trace | Do not install | Descriptor/member constructors, refresh, string copy and stream evidence |
| `lan/native/session_materializer.h` | New source-only native construction API | Do not install into game | Bounded data inputs and exact native descriptor/result layouts; host binding still required |
| `lan/native/session_materializer.c` | New source-only client construction component | Do not install into game | Builds valid borrowed descriptors and invokes injected native owned-handle factory; empty-stream/property profile only |
| `lan/native/test_session_materializer.c` | New standalone native contract fixture | Do not install | Layout, bounds, ownership handoff and rejection tests; no game calls |
| `analysis/session-object-construction-trace.txt` | Generated bounded exact-build trace | Do not install | Owned descriptor handle factory and member wrapper construction |
| `analysis/session-object-construction-findings.md` | New constructor contract findings | Do not install | Separate transferable session data from process-local handles and reference ownership |
| `lan/test_native_session_wire.py` | New protocol integration tests | Do not install | TCP ownership, session notifications, isolation and no premature match_start |
| `analysis/native-quickmatch-join-findings.md` | New exact-build static findings | Do not install | Native join, shared-handle ownership and safe integration constraints |
| `analysis/native-quickmatch-join-native.txt` | Generated bounded native trace | Do not install | Steam/local join and title wrapper implementations |
| `analysis/native-quickmatch-join-handles.txt` | Generated bounded native trace | Do not install | Local registry lookup, handle installation and post-join continuation |
| `analysis/native-quickmatch-filter-trace.txt` | Generated bounded native trace | Do not install | Exact numeric comparison semantics and matching search/create branches |
| `lan/native_sessions.py` | Updated server-side session directory | server machine only, beside szero_lan.py | Create/search/join/match/update/flags/leave for linked experimental native adapter; no native pointers on wire |
| `lan/test_native_sessions.py` | New server component tests | Do not install | Session isolation, bounded validation and lifecycle contracts |
| `analysis/onlinefix64-static-trace.txt` | New direct REA static evidence | Do not install | Main protected DLL entry/callee decompilation, assembly, byte identity and explicit coverage limits |
| `analysis/online-package-loader-trace.txt` | New REA static evidence | Do not install | Proxy loader structure and bounded decompilation provenance; no DRM or auth bypass reconstruction |
| `analysis/online-package-findings.md` | New user-supplied artifact report | Do not install | Safe static loader/network findings and protected-code limitations; no third-party integration |
| `analysis/local-transport-dispatch.txt` | Generated focused static trace | Do not install | Compiled network mode factory selection |
| `analysis/local-transport-factories.txt` | Generated focused static trace | Do not install | Concrete local/channel factory construction |
| `analysis/local-transport-udp-factory.txt` | Generated focused static trace | Do not install | Network configuration callback tables |
| `analysis/local-transport-bind-selection.txt` | Generated focused static trace | Do not install | Context-scoped binding selection and service-owned address |
| `analysis/local-transport-os-factories.txt` | Generated focused static trace | Do not install | OS-network factory implementations |
| `analysis/local-transport-udp-construction.txt` | Generated focused static trace | Do not install | Concrete network interface vtables and WinSock-bind forwarding |
| `analysis/local-transport-lifecycle.txt` | Generated focused static trace | Do not install | Exact initialization guards, per-context bundle switch and address setters |
| `analysis/native-lobby-descriptor-layout.txt` | Generated selected-function trace | Do not install | Exact descriptor constructors, nested ownership and cleanup; not a network response template |
| `analysis/native-search-service-boundary.txt` | Generated selected-function trace | Do not install | Search +90 service dispatch, cancellation, local lock wrapper and vector destructors |
| `analysis/native-search-local-query.txt` | Generated selected-function trace | Do not install | Process-local query and native search request/result ownership |
| `analysis/native-search-steam-constructor.txt` | Generated selected-function trace | Do not install | Steam service constructor and concrete vtable identity |
| `analysis/native-search-steam-provider.txt` | Generated selected-function trace | Do not install | Steam search provider implementation and request filter conversion |
| `analysis/native-search-steam-completion.txt` | Generated selected-function trace | Do not install | Steam asynchronous completion and descriptor copy/move constructors |
| `analysis/local-transport-config-trace.txt` | Generated selected-function trace | Do not install | Config getter field locations; no guessed endpoint assignments |
| `analysis/local-transport-mode-consumers.txt` | Generated selected-function trace | Do not install | Actual channel configuration and bind-address/service consumers |
| `analysis/native-search-provider-abi.txt` | Generated focused native trace | Do not install | Native search/filter/join provider boundaries and result ownership |
| `analysis/native-search-provider-findings.md` | New search integration findings | Do not install | Concrete search result ABI and unresolved safe replacement boundaries |
| `analysis/local-transport-config-findings.md` | New transport configuration investigation | Do not install | Evidence for local mode selection versus unverified address/channel setup |
| `analysis/runtime-native-session-evidence-gap.md` | New supplied-log and native ABI report | Do not install | Latest F5 run adds no native evidence; precise capture needed for provider integration |
| `analysis/native-session-wrapper-construction.txt` | Generated focused static trace | Do not install | Native session descriptor constructor below exact title factory |
| `lan/Start-Native-Trace.cmd` | New opt-in capture entry | client tools folder (outside game root) | Launches normal setup window with bounded native-state tracing enabled; not a LAN redirect |
| `analysis/native-session-wrapper-factory.txt` | Generated focused native trace | Do not install | Concrete title session-wrapper factory selected by context virtual +28 |
| `lan/native/session_probe.c` | New opt-in read-only helper source | client tools folder only | Exact-image, bounded own-process context/session-presence trace; no function calls or state writes |
| `lan/ue4ss/SzeroLAN/scripts/session_probe.dll` | Generated native helper | Same mod scripts folder as main.lua | Optional native session-state capture, not networking/initialization |
| `lan/ue4ss/SzeroLAN/scripts/session_trace.lua` | New opt-in capture adapter | Same mod scripts folder as main.lua | Environment-gated game-thread diagnostic independent of sidecar pairing |
| `lan/test_session_trace.lua` | New diagnostic contract tests | Do not install into game | Default-disabled and bounded helper invocation; mocked only |
| `analysis/native-online-backend-findings.md` | New runtime/native integration report | Do not install | Latest unregistered-command evidence, matching task chain, concrete service +88 boundary and remaining ABI work |
| `analysis/native-session-create-completion.txt` | Generated focused static trace | Do not install | Native service result completion required before a context owns a session |
| `analysis/native-session-service-virtual-boundary.txt` | Generated focused static trace | Do not install | Selected service virtual call and context-result completion; no runtime injection |
| `analysis/native-session-provider-operation.txt` | Generated focused static trace | Do not install | Guarded context session-provider operation below native result wrappers |
| `analysis/native-session-create-service-call.txt` | Generated focused static trace | Do not install | Concrete service callback boundary for native session creation |
| `analysis/native-platform-session-create.txt` | Generated focused static trace | Do not install | Context-to-service session creation boundary reached from normal native matching |
| `analysis/native-session-service-dispatch.txt` | Generated focused static trace | Do not install | Session service and result-object dispatch reached from context matching |
| `analysis/native-room-context-session.txt` | Generated focused static trace | Do not install | Context-owned session operation and actual callback handlers below title matchmaking |
| `analysis/native-room-operation-forwarding.txt` | Generated focused static trace | Do not install | Native room operation result/parameter forwarding below scheduled matching |
| `analysis/native-room-provider-entry.txt` | Generated focused static trace | Do not install | Session preparation and native room-operation provider entry; no authentication modifications |
| `analysis/native-matching-start-operation.txt` | Generated focused static trace | Do not install | Concrete title matching operation reached by the scheduled native task |
| `analysis/native-matching-task-execution.txt` | Generated focused static trace | Do not install | Matching task call target recovered from original leaf thunk, not guessed packet handling |
| `analysis/scripts/decode_native_message.py` | New offline analysis tool | Do not install/distribute | Partial evidence-based inner-message decoder; not a UDP listener or server |
| `analysis/scripts/test_decode_native_message.py` | New analysis test | Do not install/distribute | Five synthetic decoder boundary/rejection tests; not captured game traffic |
| `analysis/native-matching-task-callback.txt` | Generated focused static trace | Do not install | Concrete task callbacks selected from the original matching-operation vtable |
| `analysis/native-matching-operation-construction.txt` | Generated focused static trace | Do not install | Native scheduled operation capture and executable task construction |
| `analysis/native-matching-service-call.txt` | Generated focused static trace | Do not install | Matching service calls below asynchronous wrappers, preserving exact-build types as unknown |
| `analysis/native-matching-provider-dispatch.txt` | Generated focused static trace | Do not install | Actual matching-operation dispatch and condition construction below native menu wrappers |
| `analysis/native-session-lookup-trace.txt` | Generated focused static trace | Do not install | Existing native session lookup, channel readiness predicates and result conversion |
| `analysis/native-message-protocol-trace.txt` | Generated focused static trace | Do not install | Native message encoding primitives and local session storage paths |
| `analysis/native-message-protocol-findings.md` | New bounded protocol report | Do not install | Observed serializer fields versus unresolved channel framing and lifecycle |
| `analysis/native-online-operation-step-trace.txt` | Generated focused static trace | Do not install | Concrete session operation vtable handlers and continuation setup |
| `analysis/native-online-operation-trace.txt` | Generated focused static trace | Do not install | Native menu online-operation builders and asynchronous session creation; no runtime calls |
| `analysis/widget-input-runtime-findings.md` | New runtime evidence report | Do not install | Own-object API tests and measured input function parameter counts; limits and cleanup |
| `analysis/scripts/WidgetParamProbe.c` | New analysis-only metadata reader | Do not install/distribute | Read-only own-process UFunction NumParms/ParmsSize at runtime-verified offsets; no engine calls |
| Generated `analysis/scripts/WidgetParamProbe.dll`, `widget-function-addresses.txt`, `widget-function-signatures.txt` | Temporary analysis artifacts | Do not install/distribute | Runtime function signature probe, not LAN runtime dependencies |
| `analysis/scripts/WidgetInteropProbe.lua` | New analysis-only own-widget probe | Do not install/distribute | Isolated transient TextBlock/FText/parameter-iteration compatibility test; no viewport or network calls |
| Temporary `Win64/Mods/SzeroWidgetProbe/scripts/main.lua` and `enabled.txt` in workspace game | Removed after bounded tests | Do not install/distribute | Ran only the analysis probe in the workspace test copy |
| `analysis/native-menu-widget-lifecycle.txt` | Generated focused native trace | Do not install | Selected lifecycle functions only; bare widget full lifecycle remains unverified |
| `lan/ue4ss/SzeroLAN/scripts/native_menu.lua` | New opt-in native-widget menu prototype | Same scripts folder as main.lua | Own SSMenuManager/SSMenuButton controls; NOT the native main-menu controller stack or battle bootstrap |
| `lan/test_native_menu.lua` | New mocked native-widget test | Do not install | Own-instance callback isolation, native focus requests, guards and closed-menu idle work |
| `lan/native/menu_bridge.c` | New experimental native UI binding source | Do not install source | Separate state-mutating UI-only helper; exact-build, fresh-widget ownership and thread guards |
| `lan/ue4ss/SzeroLAN/scripts/menu_bridge.dll` | Generated experimental native UI bridge | Same scripts folder as main.lua | Only opted-in native menu mode; binds newly created native buttons, not existing menus or network contexts |
| `analysis/native-menu-base-input.txt` | Generated focused native trace | Do not install | Native menu input/callback implementation candidates |
| `analysis/native-menu-focus-activation.txt` | Generated focused native trace | Do not install | Native focus request and owned-widget activation recursion |
| `analysis/native-menu-child-registration.txt` | Generated focused native trace | Do not install | Native child activation and manager behavior |
| `analysis/native-menu-button-delegates.txt` | Generated focused native trace | Do not install | Native button delegate setup candidates |
| `analysis/native-menu-dynamic-delegates.txt` | Generated focused native trace | Do not install | Dynamic weak-object/FName delegate binding and explicit button registration |
| `lan/test_audit.lua` | New mocked audit test | Do not install | Missing helper, wrong image, pending/timeout, base-name counting and one-shot behavior |
| `lan/native/README.md` | New native audit build/limitations guide | Do not install | Reproducible DLL and native Windows fixture test; no acceptance claims |
| `lan/ue4ss/SzeroLAN/scripts/audit.lua` | New optional audit adapter | Same scripts folder as main.lua | Loads bounded read-only native helper on game thread; reports registration, never assumes command acceptance |
| `lan/native/console_probe.c` | New read-only exact-build native audit source | Do not install source | Own-process console registry read; asynchronous executable SHA-256 guard; no engine calls or memory writes |
| `lan/ue4ss/SzeroLAN/scripts/console_probe.dll` | Generated native audit DLL | Same scripts folder as main.lua | Optional bounded console registration snapshot; not a session bootstrap |
| `analysis/local-backend-selection-trace.txt` | Generated focused native trace | Do not install | Separate compiled local and Steam service factories and actual selector implementations |
| `analysis/native-menu-base-construction.txt` | Generated focused native trace | Do not install | Menu base reflected registration |
| `analysis/native-menu-base-schema.txt` | Generated focused native trace | Do not install | Menu base constructor and class factory |
| `analysis/scripts/SzeroBounded.java` | New focused recovery script | Do not install | Decompiles selected PE exception-table bodies, merges chained unwind fragments; no global analysis |
| `analysis/native-menu-dispatcher.txt` | Generated initial trace; superseded | Do not install | Initial menu dispatcher recovery; use corrected state/tick reports for body coverage |
| `analysis/native-menu-state-tick.txt` | Generated focused native trace | Do not install | Exact native menu tick, virtual state dispatch and captured-data resolver |
| `analysis/native-menu-transition-handler.txt` | Generated focused native trace | Do not install | Native state 1c processing |
| `analysis/native-menu-transition-stages.txt` | Generated focused native trace | Do not install | Native states 1d through 1f and actual scene-transition submission |
| `analysis/console-exec-implementations.txt` | Generated focused native trace | Do not install | Kismet console-command implementation, controller and engine dispatch paths |
| `analysis/native-menu-integration-findings.md` | New bounded findings | Do not install | Proven native menu route and unresolved safe local integration |
| `analysis/plainudp-bootstrap-trace.txt` | Generated focused native trace | Do not install | Context initialization, outgoing channel guards and error-code conversion |
| `analysis/plainudp-bootstrap-findings.md` | New bounded findings | Do not install | Missing native channel boundary; avoids confusing error-code metadata with mode selection |
| `analysis/matching-settings-owner-resume.txt` | Generated bounded native trace | Do not install | Native matching-settings owner resume paths after delegate trampolines |
| `analysis/matching-settings-owner-continuations.txt` | Generated bounded native trace | Do not install | Native matching-settings callbacks after Enter; static only |
| `analysis/matching-settings-delegate-callers.txt` | Generated bounded native trace | Do not install | Matching settings owner delegate registration and its incoming callers |
| `analysis/matching-settings-delegate-setup.txt` | Generated bounded native trace | Do not install | Candidate owner-delegate writers for native matching settings; static only |
| `AGENTS.md` | New project documentation; not a game patch | Do not install | Investigation handoff and patch ledger |
| `.gitignore` | New Git exclusions | Do not install | Excludes original game/tools binaries, runtime state, local config and generated distributions |
| `analysis/runtime-test-2026-10-20.md` | Second supplied game-log findings | Do not install | Controller fix verified; unchanged Korat world and no game-packet evidence; source hashes |
| `analysis/scripts/RuntimeSchemaProbe.lua` | New bounded runtime metadata probe | Do not distribute into game | Reads thirteen native struct/class schemas before world startup; no object values or network calls |
| `analysis/runtime-native-schema.tsv` | Generated runtime schema report | Do not install | Exact-build native property names/types/order and enum metadata, not guessed public-header layout |
| `analysis/scripts/SzeroFocused.java` | New analysis script | Do not install | Read-only Ghidra string/xref/decompiler query |
| `analysis/focused-results.txt` | Generated analysis report when focused script completes | Do not install | Static references and recovered pseudocode; partial global analysis |
| `analysis/scripts/SzeroTrace.java` | New analysis script | Do not install | Bounded reference traversal and decompilation of selected anchors |
| `analysis/trace-results.txt` | Generated trace report when script completes | Do not install | References to debug mode and session markers |
| `analysis/session-trace.txt` | Generated static analysis report | Do not install | Session construction and validation functions |
| `analysis/backend-trace.txt` | Generated static analysis report | Do not install | Service configuration constructors and endpoint fields |
| `analysis/endpoint-setter-trace.txt` | Generated static analysis report | Do not install | Candidate service-host setter and callers |
| `analysis/plainudp-trace.txt` | Generated static analysis report | Do not install | Built-in PlainUdp preset handlers and local battle mode |
| `analysis/battle-entry-trace.txt` | Generated static trace | Do not install | Debug setup state machine and local battle flag |
| `analysis/local-battle-callers.txt` | Generated static trace | Do not install | Callers of local battle flag and debug command registration |
| `analysis/auto-battle-delegates.txt` | Generated static trace | Do not install | Candidate console delegate callbacks for battle entry |
| `analysis/battle-transition-stages.txt` | Generated static trace | Do not install | Debug setup states, session setup and final travel; not a verified main-menu entry path |
| `analysis/selection-entry-trace.txt` | Generated focused static trace | Do not install | Main-menu and battle-setup synchronization and selection transition anchors |
| `analysis/selection-api-trace.txt` | Generated focused static trace | Do not install | Reflected transition-mode and matching entry points; static applicability only |
| `analysis/selection-native-bindings.txt` | Generated static binding trace | Do not install | Native implementations adjacent to reflected selection API names |
| `analysis/transition-mode-callers.txt` | Generated focused static trace | Do not install | Transition mode setter, native callers and matching implementation |
| `analysis/mainmenu-selection-api.txt` | Generated reflected API trace | Do not install | StartOfflineBattle, StartQuickMatch and LevelTransition native binding names |
| `analysis/mainmenu-selection-bindings.txt` | Generated native binding trace | Do not install | Native main-menu battle/quick-match function wrappers |
| `analysis/mainmenu-battle-start.txt` | Generated focused native trace | Do not install | Main-menu no-argument StartOfflineBattle and StartQuickMatch implementations |
| `analysis/selection-entry-findings.md` | New static evidence summary | Do not install | Exact selection APIs, shipping no-op traps and remaining runtime evidence gap |
| `analysis/public-mods-findings.md` | New read-only public-source research report | Do not install | Reflected selection APIs, in-game UMG construction candidates and pinned-loader safety caveats |
| `analysis/cooked-menu-findings.md` | New exact-build package investigation report | Do not install | Real cooked menu graph, no-op Blueprint wrappers, native schema validation and safe remaining evidence boundaries |
| `analysis/scripts/package-inspector/PackageInspector.csproj` | New offline analysis project | Do not install | References FModel's pinned CUE4Parse parser; not runtime code |
| `analysis/scripts/package-inspector/Program.cs` | New read-only archive inspector | Do not install | Narrow asset listing and explicitly selected JSON/Blueprint pseudo exports; AES environment input only |
| `analysis/scripts/package-inspector/HeaderSchema.cs` | New optional exploratory analysis helper | Do not install | Explicitly labelled reconstructed-header mapping probe for one menu data asset; not an exact-build usmap |
| `analysis/scripts/package-inspector/README.md` | New analysis recovery guide | Do not install | Pinned parser/header identities, configurable dependency build and bounded export commands |
| `analysis/matching-session-entry.txt` | Generated focused native trace | Do not install | Matching/session setup implementation, selected functions without global caller expansion |
| `analysis/socket-bind-trace.txt` | Generated focused import-reference trace | Do not install | WinSock bind, sendto, WSASendTo and socket creation callers; transport attribution incomplete |
| `analysis/spnet-console-trace.txt` | Generated focused native trace | Do not install | SpNet UE Console registration and native UDP bind/send wrappers |
| `analysis/spnet-dispatch-registration.txt` | Generated focused native trace | Do not install | Dynamic SpNet console enumeration and transport bind callers |
| `analysis/spnet-property-registration.txt` | Generated focused native trace | Do not install | UE console `.value` and `.exec` registration wrappers and UDP bind setup |
| `analysis/spnet-console-metadata.txt` | Generated focused native trace | Do not install | Dynamic command metadata/path-name builders and console listeners |
| `analysis/spnet-context-construction.txt` | Generated focused native trace | Do not install | MultiplayerContext initialization and command listener wiring |
| `analysis/plainudp-binding-candidates.txt` | Generated focused native trace | Do not install | Address-based socket binder, matching call and metadata export candidates |
| `analysis/transition-mode-consumers.txt` | Generated focused getter-consumer trace | Do not install | Actual readers of game-instance transition mode and selected transition dispatch |
| `analysis/mainmenu-normal-transition.txt` | Generated focused native trace | Do not install | Non-debug-menu level transition wrapper and offline selection state callback |
| `analysis/mainmenu-test-transition-flow.txt` | Generated focused native trace | Do not install | Reflected TestLevelTransition implementation and SpNet matching singleton initialization |
| `analysis/spnet-context-metadata-init.txt` | Generated focused native trace | Do not install | Multiplayer context initialization and console metadata exposure |
| `analysis/spnet-context-properties.txt` | Generated focused native trace | Do not install | Context property/type descriptors and base constructor |
| `analysis/spnet-console-node-table.txt` | Generated focused vtable trace | Do not install | Exposed multiplayer context console node and initialization callback |
| `analysis/spnet-udp-binding-tables.txt` | Generated focused binding-reference trace | Do not install | Shared UDP binding adapters and table references |
| `analysis/matching-query-bindings.txt` | Generated focused reflection trace | Do not install | Exact-build read-only matching status names and singleton accessor |
| `analysis/matching-query-implementations.txt` | Generated focused native trace | Do not install | Game-side matching queries and default application session interface |
| `analysis/app-network-interface.txt` | Generated focused native trace | Do not install | AppNetworkWorker interface default, reflected status forwarding and class identity |
| `analysis/app-network-vtables.txt` | Generated focused vtable trace | Do not install | Default application online interface methods and worker constructor metadata |
| `analysis/game-instance-diagnostic-getters.txt` | Generated exact-build getter registration trace | Do not install | Read-only game-instance diagnostics ownership and implementation anchors |
| `analysis/game-instance-getter-thunks.txt` | Generated native thunk/constructor trace | Do not install | Verify diagnostic getters and AppNetworkWorker concrete interface construction |
| `analysis/app-network-concrete-interface.txt` | Generated concrete vtable trace | Do not install | Actual online-enable, fence creation and fence state callbacks |
| `analysis/matching-session-bootstrap.txt` | Generated focused native trace | Do not install | Core multiplayer operation setup and context initialization callers |
| `analysis/local-backend-bootstrap-candidates.txt` | Generated focused native trace | Do not install | Session-operation construction and application bootstrap configuration callers |
| `analysis/title-context-factory.txt` | Generated focused native trace | Do not install | Title multiplayer factory configuration and existing session discovery routine |
| `analysis/title-context-implementation.txt` | Generated static title-factory trace | Do not install | Read-only title context factory implementations |
| `analysis/title-context-construction.txt` | Generated static context-construction trace | Do not install | Concrete title multiplayer context construction/configuration |
| `analysis/korat-multiplayer-constructor.txt` | Generated exact-build native trace | Do not install | Title-specific context constructor and post-bootstrap initialization |
| `analysis/menu-button-reflection-schema.txt` | Generated exact-build reflection trace | Do not install | Main-menu button struct property schema for precise cooked-asset mapping |
| `analysis/scripts/menu-properties.txt` | Generated bounded property-descriptor trace | Do not install | Main-menu exact-build reflected property descriptor names and raw flags |
| `analysis/menu-properties-complete.txt` | Generated exact-build property schema | Do not install | Main-menu button full descriptor order, type flags and referenced type factories |
| `analysis/menu-appended-property-types.txt` | Generated precise property type trace | Do not install | Appended main-menu enum/struct property types and derived fields |
| `analysis/menu-settings-property-schema.txt` | Generated exact-build reflection trace | Do not install | Current settings property schema and newly appended alternative-property data |
| `analysis/menu-settings-property-types.txt` | Generated property-descriptor trace | Do not install | Exact added settings field type compared with existing property data |
| `analysis/autoquickmatch-settings-entry.txt` | Generated focused native reflection trace | Do not install | Actual AutoQuickMatch settings UI callback entry points |
| `analysis/autoquickmatch-settings-callbacks.txt` | Generated native callback trace | Do not install | Settings widget reflected callback signatures and entry implementation |
| `analysis/local-online-helper-bootstrap.txt` | Generated focused native trace | Do not install | Local-online role flag readers and BattleSync helper bootstrap |
| `analysis/settings-enter-flow.txt` | Generated focused native trace | Do not install | Matching settings Enter callback and local-sync helper fallback |
| `analysis/autoquickmatch-enter-implementation.txt` | Generated concrete UI callback trace | Do not install | Real matching-condition Enter implementation used by current Quick match widget |
| `analysis/local-online-helper-consumers.txt` | Generated focused flag-consumer trace | Do not install | Internal downstream consumers of local-online synchronization helper flags |
| `analysis/local-online-frame-consumers.txt` | Generated focused native trace | Do not install | Consumers of skeletal/physics partition flags enabled by local-online helper |
| `analysis/matching-settings-owner-callbacks.txt` | Generated focused native trace | Do not install | Settings callback storage and owner delegate setup |
| `analysis/dummy-session-service-vtable.txt` | Generated focused vtable trace | Do not install | Compiled dummy-session service constructor and method table candidates |
| `analysis/console-manager-layout.txt` | Generated exact-build native trace | Do not install | Console manager singleton construction for bounded read-only command registration inspection |
| `analysis/console-manager-lookup.txt` | Generated focused native trace | Do not install | Console manager map lookup and element layout verification |
| `analysis/scripts/read_console_registry.py` | New bounded read-only runtime probe | Do not install | Enumerates exact-build console registrations only in a stopped game child owned by an explicitly selected isolated test controller |
| `lan/szero_lan.py` | Replaced with central lobby/matchmaking server and identical client protocol | server machine and client tools folder (outside game root) | Server-owned membership, queues, matches and isolated UDP forwarding; no secrets |
| `lan/launcher.py` | New desktop client and adapter installer | client tools folder (outside game root) | Server address, lobby list, matchmaking, automatic game-instance assignment |
| `lan/ingame_client.py` | New background client | client tools folder | Connects using game-root SzeroLAN.json; bounded per-instance command/status exchange with game panel |
| `lan/setup_launcher.py` | Updated native-only setup/launch window | client tools folder (outside game root) | Address/port/name, no mode checkbox; migrate absent/false flags, atomic JSON preservation, exact EXE/helper/server preflight |
| `lan/ue4ss/SzeroLAN/scripts/panel.lua` | In-game panel implementation in progress | Same scripts folder as main.lua | Experimental in-game lobby controls; rendering requires verification |
| Generated `SzeroLAN.json` | New config when absent; preserved thereafter | `SzeroLAN.json` at game root | Server hostname/IP, port and player display name |
| `lan/installer.py` | New offline installer | client tools folder (outside game root) | Verifies hashes, installs missing loader and adapter, writes backups and exact file receipt |
| `lan/vendor/UE4SS_v3.0.1.zip` | Downloaded unchanged official basic release | Installer selects members; do not extract whole ZIP into game | Bundled UE4SS.dll and dwmapi.dll plus helper/settings |
| `lan/vendor/UE4SS-LICENSE.txt` | Official MIT license from v3.0.1 tag | `SparkingZERO/Binaries/Win64/UE4SS-LICENSE.txt` for fresh setup | Loader redistribution notice |
| `lan/vendor/UE4SS.json` | New provenance and member hashes | Do not install into game | Pinned source URL, release date and measured hashes |
| `lan/Start-Server.cmd` | New Windows entry point | server machine only | Double-click server startup |
| `lan/Start-Client.cmd` | New Windows entry point | client tools folder (outside game root) | Double-click lobby window startup |
| `lan/server.example.json` | Simplified config template | server machine only | LAN bind IP and port |
| `lan/client.example.json` | Updated native-default config template | client tools folder (installer creates game-root SzeroLAN.json only if absent) | Server hostname/IP, port, display name and true native-search/session flags |
| `lan/ue4ss/SzeroLAN/scripts/main.lua` | Revised experimental adapter; not installed | `SparkingZERO/Binaries/Win64/ue4ss/Mods/SzeroLAN/scripts/main.lua` for that UE4SS layout | Polls runtime assignment and applies recovered PlainUdp commands automatically |
| `lan/ue4ss/SzeroLAN/enabled.txt` | New mod enable marker; not installed | `SparkingZERO/Binaries/Win64/ue4ss/Mods/SzeroLAN/enabled.txt` for that UE4SS layout | UE4SS mod discovery |
| `lan/README.md` | New deployment and validation guide | Do not install into game | Exact copy paths, prerequisites and limitations |
| `lan/test_szero_lan.py` | New socket integration tests | Do not install into game | Real relay/bridge transport validation |
| `lan/test_adapter.lua` | New mocked adapter test | Do not install into game | Lua command sequence validation |
| `lan/test_panel.lua` | New mocked UMG panel test | Do not install | Construction, per-frame fresh lookup, controls and travel lifetime contract |
| `lan/test_ingame_client.py` | New background bridge tests | Do not install | Game-root config, bounded commands and Lua data encoding |
| `lan/test_setup_launcher.py` | Updated config/editor window tests | Do not install | Nine tests: validated config preservation, save and auto-save, active-session guard and mocked per-instance launch |
| `lan/test_launcher.py` | New installer/window tests | Do not install into game | Hash guard, install destinations, backups and GUI state rendering |
| `lan/SHA256SUMS.txt` | New distribution checksums | Do not install into game | Integrity checks for the experimental source package |
| `dist/SzeroLAN-experimental.zip` | Generated revised distribution package | Extract into a tools folder on server/client PCs | Contains the `lan/` source/config/launcher layout; no original game files |
| `dist/SHA256SUMS.txt` | Generated archive checksum | Do not install into game | Integrity check for the ZIP |

The launcher generates `lan_runtime.lua` for a manually launched single game,
or `lan_runtime_<instance-id>.lua` when using its Start game button. These go
beside the installed mod's `main.lua`, are updated automatically, and are not
user configuration files. A separate launcher window can start each game
process with its own `SZERO_LAN_INSTANCE` environment variable. Actual game
launch/platform multi-instance support is still unverified. For older UE4SS
layouts, use `SparkingZERO/Binaries/Win64/Mods/SzeroLAN/...`; the install button
detects both layouts. Fresh setup installs bundled UE4SS v3.0.1 directly into
Win64. Existing UE4SS binaries, settings and shared helpers are preserved.
The exact fresh setup paths relative to the game root are:

- `SparkingZERO/Binaries/Win64/dwmapi.dll`
- `SparkingZERO/Binaries/Win64/UE4SS.dll`
- `SparkingZERO/Binaries/Win64/UE4SS-settings.ini` (only if absent)
- `SparkingZERO/Binaries/Win64/UE4SS-LICENSE.txt`
- `SparkingZERO/Binaries/Win64/Mods/shared/UEHelpers/UEHelpers.lua` (only if absent)
- `SparkingZERO/Binaries/Win64/Mods/mods.txt` (only SzeroLAN on fresh setup;
  preserve other entries on existing setups)
- `SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/main.lua`
- `SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/panel.lua`
- `SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/audit.lua`
- `SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/console_probe.dll`
- `SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/native_menu.lua` (opt-in)
- `SparkingZERO/Binaries/Win64/Mods/SzeroLAN/scripts/menu_bridge.dll` (opt-in)
- `SparkingZERO/Binaries/Win64/Mods/SzeroLAN/enabled.txt`
- `SzeroLAN.json` (only if absent)
- `SparkingZERO/Binaries/Win64/SzeroLAN-install.json` (generated file receipt)

The upstream ZIP contains unrelated example mods; installer allowlists exclude
them. An unrelated existing dwmapi.dll without recognized UE4SS is a conflict
and is left unchanged. Each setup receipt records a transaction with changed
paths, before/after hashes and backups. Failures roll back file changes.
Pinned archive SHA256:
`4b47d4bceddd2f561a4e395bfa00924ccfc945af576a2d0c613e6537846c57ec`.
GitHub supplied no upstream digest for this older asset; this is a measured
hash of the official download, not a signature claim.
The launcher backs up differing adapter files before replacing them and refuses
to install against an executable hash other than the analyzed one.

Generated testing logs: `lan/server.log` (and rotation `.1`) and
`lan/client-<instance-id>.log` (and rotation `.1`). These are runtime outputs,
not patches to game files. No source checksums cover machine-specific configs,
runtime assignments or logs.
The revised adapter generates `lan_runtime_<instance-id>.status.json` beside
its `main.lua`, or `lan_runtime.status.json` for the generic path. These are
local diagnostics, not installed source files. The latest in-game UI revision
updates main.lua, adds panel.lua, and creates game-root SzeroLAN.json only if
absent. Clients must rerun Set up / update game and restart. Tools-side runtime
changes include szero_lan.py, installer.py, setup_launcher.py, ingame_client.py
and Start-Client.cmd. The old launcher.py stays available for diagnostics.

## Retained analysis recovery (2026-10-20)

The direct headless run retains its project at `/tmp/szero-ghidra-project`,
project `SzeroProject`. Global analysis reached its 1800-second limit; coverage
is partial. The first post-script failed compilation because this Ghidra
version has no `DefinedDataIterator.definedStrings` method. The corrected
workspace script uses the Listing API and checks `StringDataInstance.isString`.
Use a dedicated script directory (`analysis/scripts`), never all of `/tmp`:
Ghidra recursively follows Wine drive links while compiling Java scripts.
The unused temporary Wine prefix's c:, e:, and z: directory symlinks were
removed to release that recursive scan; no target files were deleted.
Java runtime settings use `JAVA_TOOL_OPTIONS=-Duser.home=/tmp/szero-ghidra-home`.
Process the retained program with `-process` and `-noanalysis` for focused
queries after saving. Do not re-import the executable unnecessarily.

No original game executable, DLL, PAK, UTOC, UCAS or save has been patched.
For an isolated local startup test on 2026-10-20, the installer was run against
the workspace game copy: it added the ten fresh-setup files listed above plus
SzeroLAN-install.json. Receipt transaction 1792533431963565326 records all
before hashes as null (nothing overwritten) and exact after hashes. It also
generated scripts/lan_runtime_deadbeef.lua for the offline probe. The shipping
EXE hash was rechecked unchanged. The user's separate shared/SZeroLinux
installation was NOT changed. Test profile: /tmp/szero-runtime-ImCOa6, network
namespace isolated from external access, separate Xvfb. The first sandboxed
Wine attempt failed to bind its local socket before game execution. Scoped
escalated startup worked far enough for UE4SS and native-schema collection,
then the game exited code3 before any world became available. The unmodded
baseline (only our new dwmapi proxy temporarily renamed, then restored with
hash verified) also exited3. The cause is not established; do not label it a
mod crash or bypass normal platform startup. A null-RHI attempt produced no
new loader log and is not evidence about mod compatibility.
A subsequent normal DX11/windowed attempt also exited3 before a world appeared.
Do not repeat those identical isolated-profile startup attempts unchanged.
To verify the panel and native session progression, obtain the user's known-
working Wine/Proton launch command/prefix information, preserve it, and inspect
only the selected game instance. Do not copy account/session secrets, alter
platform checks, or assume a network namespace isolates host IPC proxies.

The bounded schema probe produced 245 lines without ERROR/MISSING. It
corroborates current property order and enum labels. Stable UE4SS 3.0.1
ForEachProperty/ForEachName callbacks must fall through with nil to continue:
explicit false caused iteration to fail after the first item in this runtime.
Also GetStruct():GetStructAddress() is the optional VALUE STORAGE address,
not UScriptStruct metadata; zeros there must not be used as metadata identity.
The workspace installed main.lua temporarily contained an explicit analysis
probe hook controlled by SZERO_LAN_SCHEMA_PROBE=1, never present in packaged
source. That hook was removed after probing; the installed main.lua is restored
to the source/receipt version. No game original was modified for the probe.
FModel was run read-only for indexing; its existing user
profile is outside the workspace and is not a redistribution artifact.

The experimental adapter copy list above is available and sidecar/loader files
are installed only in the workspace test copy. Two-game multiplayer is not
verified. Do not copy
`AGENTS.md` into the game directory; it belongs only at the workspace root.

## Verification checklist for every deliverable

- Record SHA-256 before and after any transformed artifact.
- State the exact source file and install destination folder.
- Test server and two clients on an isolated LAN without a hosts-file change.
- Test both numeric IPv4 and hostname configuration values.
- Confirm clean failure when the server is absent or the config is invalid.
- Confirm production online mode is not contacted while LAN mode is selected.
- Confirm originals can be restored without reinstalling the game.
