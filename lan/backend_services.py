"""Socket-owned LAN backend records, separate from the game's official service.

Only explicitly recovered login/transaction/notice/report/banner/card and
room-owned battle-start/end contracts are supported.
No platform credentials, official progression, purchases, or arbitrary backend
URLs are accepted. Native transport forwards approved value-only fields, never
whole native request bodies.
"""
from __future__ import annotations

import copy
import re
import time
import uuid

from native_rank import validate_rank_snapshot
from native_profile import PROFILE_ROUTES, RANK_ROUTE, validate_profile_update


VIRTUAL_BASE = "https://szero.invalid/"
MAX_PEERS = 256
MAX_BATTLE_RECEIPTS = 1024
BATTLE_RECEIPT_TTL = 600
_PEER = re.compile(r"[0-9a-f]{32}\Z")
_BATTLE_ROUTES = ("/pvp/start_battle_player1.php", "/pvp/start_battle_player2.php")
_BATTLE_END_ROUTES = ("/pvp/end_battle_player1.php", "/pvp/end_battle_player2.php")
_ROUTES = frozenset(("/user/login.php", "/user/check_transaction.php", "/system/get_notice.php",
                     "/pvp/get_report_taken_counts.php", "/shop_banner/get_list.php",
                     "/user/get_player_card.php", *PROFILE_ROUTES, *_BATTLE_ROUTES, *_BATTLE_END_ROUTES))


class LanBackendServices:
    """Ephemeral service state owned by already-admitted TCP connections.

    The caller supplies its actual live connection's peer ID and validated name,
    never an ID selected from a native JSON body. Disconnect removes its login;
    bounded finish receipts retain immutable ownership for late peer cleanup.
    Returned dictionaries are independent snapshots, not mutable server records.
    """

    def __init__(self, card_resolver=None, battle_resolver=None, native_store=None):
        self.native_store = native_store
        self._native_states = {}
        self._sessions = {}
        self._accounts = {}
        self._battles = {}
        # Receipts outlive native room leaves: either peer may finish first.
        # Their immutable TCP/account ownership is separate from a new round.
        self._battle_history = {}
        self.card_resolver = card_resolver
        self.battle_resolver = battle_resolver

    def bind_account(self, peer_id, account):
        """Called only after server-side token verification on the TCP hello."""
        if account is not None:
            self._accounts[peer_id] = copy.deepcopy(account)

    def disconnect(self, peer_id):
        self._native_states.pop(peer_id, None)
        self._sessions.pop(peer_id, None)
        self._accounts.pop(peer_id, None)
        for sid, battle in list(self._battles.items()):
            if peer_id in battle["members"]:
                self._battles.pop(sid, None)
                self._retire_battle(battle)
        self._prune_battle_history()

    @staticmethod
    def _retire_battle(battle):
        if battle["expires_at"] is None:
            battle["expires_at"] = time.monotonic() + BATTLE_RECEIPT_TTL

    def _prune_battle_history(self):
        now = time.monotonic()
        for code, battle in list(self._battle_history.items()):
            if battle["expires_at"] is not None and now >= battle["expires_at"]:
                self._battle_history.pop(code, None)
                if self._battles.get(battle["session_id"]) is battle:
                    self._battles.pop(battle["session_id"], None)

    def _battle_context(self, peer_id):
        """Only a live server-owned two-member roster can authorize a start."""
        if not callable(self.battle_resolver):
            raise ValueError("LAN battle directory unavailable")
        context = self.battle_resolver(peer_id)
        if type(context) is not dict or set(context) != {"session_id", "members", "membership"}:
            raise ValueError("invalid LAN battle context")
        sid, members, membership = (context[key] for key in ("session_id", "members", "membership"))
        if (not isinstance(sid, str) or _PEER.fullmatch(sid) is None
                or type(members) not in (tuple, list) or len(members) != 2
                or type(membership) not in (tuple, list) or len(membership) != 2
                or any(not isinstance(value, str) or _PEER.fullmatch(value) is None
                       for value in (*members, *membership))
                or len(set(members)) != 2 or len(set(membership)) != 2
                or peer_id not in members):
            raise ValueError("invalid LAN battle roster")
        if any(owner not in self._sessions or not self._accounts.get(owner) for owner in members):
            raise ValueError("both LAN battle participants must log in")
        return sid, tuple(members), tuple(membership)

    def prune_battles(self):
        """Membership notifications invalidate starts; reads also revalidate."""
        for sid, battle in list(self._battles.items()):
            try:
                current = self._battle_context(battle["members"][0])
            except ValueError:
                current = None
            if current != (sid, battle["members"], battle["membership"]):
                self._battles.pop(sid, None)
                self._retire_battle(battle)
        self._prune_battle_history()

    def _start_battle(self, peer_id, path, body):
        self.prune_battles()
        sid, members, membership = self._battle_context(peer_id)
        role = _BATTLE_ROUTES.index(path)
        if members[role] != peer_id:
            raise ValueError("LAN battle start role does not match room order")
        battle = self._battles.get(sid)
        if battle is not None and battle["reports"]:
            if role != 0:
                raise ValueError("first LAN battle participant must start the next round")
            if len(self._battle_history) >= MAX_BATTLE_RECEIPTS:
                raise ValueError("LAN battle receipt capacity reached")
            self._retire_battle(battle)
            self._battles.pop(sid, None)
            battle = None
        if battle is None:
            if role != 0:
                raise ValueError("first LAN battle participant has not started")
            if len(self._battles) >= MAX_PEERS:
                raise ValueError("LAN battle capacity reached")
            if len(self._battle_history) >= MAX_BATTLE_RECEIPTS:
                raise ValueError("LAN battle receipt capacity reached")
            battle = {"session_id": sid, "members": members, "membership": membership,
                      "match_code": uuid.uuid4().hex, "started": set(),
                      "accounts": tuple(copy.deepcopy(self._accounts[owner]) for owner in members),
                      "names": tuple(self._sessions[owner]["name"] for owner in members),
                      "reports": {}, "typed_reports": {}, "rating_state": "unreported",
                      "responses": {}, "expires_at": None}
            self._battles[sid] = battle
            self._battle_history[battle["match_code"]] = battle
        if role == 1 and body["match_code"] != battle["match_code"]:
            raise ValueError("LAN battle start code does not match the current round")
        battle["started"].add(peer_id)
        return {"match_code": battle["match_code"], "match_phase": 0}

    @staticmethod
    def _end_payload(battle, peer_id, outcome, rank_snapshot):
        # Echo ONLY this caller's existing native category record. This is
        # result-UI preservation, never account/other-player rating authority.
        rank = validate_rank_snapshot(rank_snapshot)
        role = battle["members"].index(peer_id)
        return {"battle_result": {"match_code": battle["match_code"],
                "rank_match_info": rank, "match_result_list": [],
                "battle_rank_point": 0, "battle_disconnect_count": 0,
                "matching_penalty_seconds": 0, "outcome": outcome,
                "is_host": role + 1, "is_disconnect": False,
                "is_rollback": False}, "match_phase": 0}

    def _end_battle(self, peer_id, path, body):
        self.prune_battles()
        battle = self._battle_history.get(body["match_code"])
        if battle is None:
            raise ValueError("unknown or expired LAN battle code")
        role = _BATTLE_END_ROUTES.index(path)
        if battle["members"][role] != peer_id:
            raise ValueError("LAN battle end role does not match the issued round")
        account = self._accounts.get(peer_id)
        session = self._sessions.get(peer_id)
        if (not account or session is None or account.get("id") != battle["accounts"][role].get("id")
                or session["name"] != battle["names"][role]):
            raise ValueError("LAN battle end ownership changed")
        if battle["started"] != set(battle["members"]):
            raise ValueError("both LAN battle participants must start before normal completion")
        outcome = body["outcome"]
        if peer_id in battle["reports"] and battle["reports"][peer_id] != outcome:
            raise ValueError("conflicting duplicate LAN battle end")
        typed = ((body["native_category"], body["native_result"])
                 if "native_category" in body else None)
        previous_typed = battle["typed_reports"].get(peer_id)
        if previous_typed is not None and typed != previous_typed:
            # An initial unavailable result can be upgraded after the native
            # result setter runs; a known result is immutable for this round.
            if typed is None or typed[0] != previous_typed[0] or previous_typed[1] != 0:
                raise ValueError("conflicting duplicate typed LAN battle result")
        if typed is not None:
            store = self.native_store
            if typed[1] == 0:
                battle["rating_state"] = "result_unavailable"
            elif store is not None:
                # One local transaction durably accepts this own report and,
                # only when peer consensus exists, applies the idempotent Elo
                # event. Never wait for the other report before this ACK.
                status = store.record_ranked_report(battle["match_code"],
                    battle["accounts"][0]["id"], battle["accounts"][1]["id"], role, *typed)
                battle["rating_state"] = status
            else:
                battle["rating_state"] = "storage_unavailable"
            battle["typed_reports"][peer_id] = typed
        if peer_id in battle["reports"]:
            return copy.deepcopy(battle["responses"][peer_id])
        payload = self._end_payload(battle, peer_id, outcome, body["rank_snapshot"])
        payload['battle_result']['match_result_list']=self.native_statistics(self.ranked_summary(peer_id))
        if type(payload) is not dict:
            raise ValueError("invalid LAN battle end response contract")
        # Native P1 reports BEFORE its peer-connect stage; P2 connects BEFORE
        # reporting. A valid own report must ACK immediately, never await P2.
        battle["reports"][peer_id] = outcome
        battle["responses"][peer_id] = copy.deepcopy(payload)
        self._retire_battle(battle)
        return copy.deepcopy(payload)

    @staticmethod
    def _validate(peer_id, name, path, body):
        if not isinstance(peer_id, str) or _PEER.fullmatch(peer_id) is None:
            raise ValueError("invalid LAN service connection")
        if (not isinstance(name, str) or not 1 <= len(name) <= 48
                or name != name.strip() or any(ord(c) < 32 or ord(c) == 127 for c in name)):
            raise ValueError("invalid LAN service player name")
        if not isinstance(path, str) or path not in _ROUTES:
            raise ValueError("unsupported LAN backend route")
        # Only recovered value DTOs are accepted: no auth_info, account IDs,
        # tickets, URLs or arbitrary native JSON. Extra fields remain refused
        # until their exact contract and ownership exist.
        if path in PROFILE_ROUTES:
            validate_profile_update(path,body)
        elif path in _BATTLE_END_ROUTES:
            if (type(body) is not dict or set(body) not in (
                    {"match_code", "outcome", "rank_snapshot"},
                    {"match_code", "outcome", "rank_snapshot", "native_category", "native_result"})
                    or not isinstance(body["match_code"], str) or _PEER.fullmatch(body["match_code"]) is None
                    or type(body["outcome"]) is not int or body["outcome"] not in (1, 2)):
                raise ValueError("invalid LAN battle end report")
            validate_rank_snapshot(body["rank_snapshot"])
            if "native_category" in body and (
                    type(body["native_category"]) is not int or body["native_category"] not in (1, 2, 3)
                    or type(body["native_result"]) is not int or body["native_result"] not in (0, 1, 2, 3)):
                raise ValueError("invalid typed native battle result")
        elif path == _BATTLE_ROUTES[1]:
            if (type(body) is not dict or set(body) != {"match_code"}
                    or not isinstance(body["match_code"], str) or _PEER.fullmatch(body["match_code"]) is None):
                raise ValueError("invalid LAN battle start code")
        elif path == "/user/get_player_card.php":
            if (type(body) is not dict or set(body) != {"target"}
                    or not isinstance(body["target"], str)
                    or (body["target"] != "self" and re.fullmatch(r"szlan:[0-9a-f]{32}", body["target"]) is None)):
                raise ValueError("invalid LAN player card target")
        elif type(body) is not dict or body:
            raise ValueError("LAN backend expects an empty route-only body")

    def request(self, peer_id, name, path, body):
        self._validate(peer_id, name, path, body)
        if path in PROFILE_ROUTES:
            session=self._sessions.get(peer_id)
            if session is None or session['name']!=name:
                raise ValueError('LAN backend login required on this connection')
            state=self.native_state(peer_id)
            if path==RANK_ROUTE:
                state['player_rank']=body['player_rank']
            else:
                records=state.setdefault('proficiency',{})
                if body['character_id'] not in records and len(records)>=512:
                    raise ValueError('native proficiency capacity reached')
                records[body['character_id']]=body['character_proficiency_rank']
                state['character_id']=body['character_id']
            self._save_native_state(peer_id,state)
            payload={}
        elif path in _BATTLE_ROUTES:
            session = self._sessions.get(peer_id)
            if session is None or session["name"] != name:
                raise ValueError("LAN backend login required on this connection")
            payload = self._start_battle(peer_id, path, body)
        elif path in _BATTLE_END_ROUTES:
            session = self._sessions.get(peer_id)
            if session is None or session["name"] != name:
                raise ValueError("LAN backend login required on this connection")
            payload = self._end_battle(peer_id, path, body)
        elif path == "/user/get_player_card.php":
            session = self._sessions.get(peer_id)
            if session is None or session["name"] != name:
                raise ValueError("LAN backend login required on this connection")
            if self.card_resolver is None:
                raise ValueError("LAN card directory unavailable")
            profile = self.card_resolver(peer_id, body["target"])
            if callable(getattr(self.native_store, "get_profile", None)) and type(profile.get("id")) is int:
                fresh = self.native_store.get_profile(profile["id"])
                if type(fresh) is dict:
                    profile = dict(profile, ranks=fresh["ranks"])
            payload = {"player_card": self.player_card(profile)}
        else:
            payload = self._request(peer_id, name, path)
        # Original145ad0500 checks top-level "res" BEFORE the route-specific
        # parser. A missing res on HTTP2xx becomes55E5E2BF. Only successful,
        # known LAN operations reach here; refusals still raise, never res=0.
        return {"res": 0, **payload}

    def native_state(self, peer_id):
        account=self._accounts.get(peer_id)
        if account and self.native_store is not None:
            return self.native_store.get_native_state(account['id'])
        return copy.deepcopy(self._native_states.get(peer_id,{}))

    def _save_native_state(self,peer_id,state):
        account=self._accounts.get(peer_id)
        if account and self.native_store is not None:
            self.native_store.put_native_state(account['id'],state)
        else:
            self._native_states[peer_id]=copy.deepcopy(state)

    def ranked_summary(self, peer_id):
        account = self._accounts.get(peer_id)
        if not account or not callable(getattr(self.native_store, "get_profile", None)):
            return []
        profile = self.native_store.get_profile(account["id"])
        return copy.deepcopy(profile["ranks"]) if type(profile) is dict else []

    @staticmethod
    def native_statistics(rankings):
        # Original cache getters filter type1/2 separately and session_kind2/3
        # as Ranked Single/DP. LAN has no seasons: both UI periods represent
        # this server's lifetime. TeamUnlimited is NOT projected into kind0.
        records=[]
        for row in rankings:
            if type(row) is not dict or row.get('mode') not in ('single','dp'):continue
            kind,battle=(2,1) if row['mode']=='single' else (3,2)
            games=min(2**32-1,max(0,int(row.get('games',0))))
            wins=min(games,max(0,int(row.get('wins',0))))
            for period in (1,2):
                records.append({'session_kind':kind,'battle_type':battle,'pvp_extra_type':0,'type':period,
                    'match':games,'win':wins,'max_win_streak':min(2**32-1,max(0,int(row.get('max_win_streak',0)))),
                    'max_rank':0,'max_use_character_id':'','max_use_character_count':0})
        return records

    @staticmethod
    def player_card(profile):
        # Original1454f9ec0 tests the optional presence at+98. Parser145ab82e0
        # keys off scalar player_rank on the CARD object, not a nested object.
        # Native asset identifiers are distinct from website artwork IDs.
        result = {"title_icon_id_for_app": "", "title_text_id_for_app": "",
                  "match_result_list": [], "player_rank": 0,
                  "rank_match_stats_list": [], "time_attack_defeat_count": 0,
                  "tournament_stats": {"max_used_character_id": "", "total_count": 0,
                      "championship_count": 0, "max_wins_count": 0,
                      "max_used_character_count": 0, "max_rank": 0},
                  "world_library_stats": {"post_battle_count": 0, "post_replay_count": 0,
                      "others_good_count": 0, "others_favorite_count": 0,
                      "others_play_count": 0}}
        for key in ("character_id", "map_id_for_app", "bgm_id_for_app", "background_id_for_app"):
            result[key] = ""
        for key in ("often_playing_mode", "playable_time_type", "character_proficiency_rank", "sp", "total_sp"):
            result[key] = 0
        for key in ("rank_match_hide_flag", "rank_match_mc_hide_flag", "rank_match_total_hide_flag",
                    "rank_match_mc_total_hide_flag", "tournament_hide_flag", "time_attack_hide_flag"):
            result[key] = False
        native=profile.get('native_state',{})
        if type(native) is dict and type(native.get('player_rank')) is int and -128<=native['player_rank']<=127:
            result['player_rank']=native['player_rank']
        if type(native) is dict:
            character=native.get('character_id')
            records=native.get('proficiency',{})
            if type(character) is str and type(records) is dict and type(records.get(character)) is int:
                result['character_id']=character
                result['character_proficiency_rank']=records[character]
        # This explicitly named LAN metadata is separate from native rank
        # records: unknown title/threshold or stats discriminator fields are
        # never populated from Elo. Original JSON consumers ignore extensions.
        if type(profile.get("ranks")) is list:
            result["lan_rankings"] = copy.deepcopy(profile["ranks"])
            result['match_result_list']=LanBackendServices.native_statistics(profile['ranks'])
        return result

    def _request(self, peer_id, name, path):
        session = self._sessions.get(peer_id)
        if path == "/user/login.php":
            if session is None:
                if len(self._sessions) >= MAX_PEERS:
                    raise ValueError("LAN backend connection capacity reached")
                session = {"session_code": "szlan-" + uuid.uuid4().hex, "name": name}
                self._sessions[peer_id] = session
            elif session["name"] != name:
                raise ValueError("LAN service connection identity changed")
            return self._login(session,self.native_state(peer_id),self.ranked_summary(peer_id))
        if session is None or session["name"] != name:
            raise ValueError("LAN backend login required on this connection")
        if path == "/user/check_transaction.php":
            # 145ad1d90 parses these exact fields; empty rewards are explicitly
            # handled by 145a9f9f0. LAN has no official purchase transactions.
            return {"reward_ids": [], "match_phase": 0, "is_present_receive": False}
        if path == "/system/get_notice.php":
            # Every field of 145aafd10 is optional. Missing means "not updated";
            # this server has no maintenance/banner/ranking updates to publish.
            return {}
        if path == "/pvp/get_report_taken_counts.php":
            # 145ab03a0 reads four uint32 counters. These are this isolated
            # LAN service's counters, never values copied from an official user.
            return {"rank_match_remove_fight_report_taken_count": 0,
                    "rank_match_report_inciting_report_taken_count": 0,
                    "rank_match_other_report_taken_count": 0,
                    "rank_match_invalid_settings_report_taken_count": 0}
        if path == "/shop_banner/get_list.php":
            # 145a9f710 ->145ab72d0, then145aceb00 accepts an empty vector.
            # This LAN service publishes no shop adverts or purchase URLs.
            return {"shop_banner_info_list": []}
        raise ValueError("unsupported LAN backend route")

    @staticmethod
    def _login(session,native_state=None,rankings=None):
        # Native 145ad0d20 requires nonempty session_code AND redirect_url.
        # The latter is an in-process virtual route marker, never a remote URL.
        # Fresh LAN records contain no official ranking, follows, notices or
        # penalties. Arrays and explicit booleans match the recovered parsers;
        # absent is_relogin would parse the literal "null" as TRUE.
        return copy.deepcopy({
            "session_code": session["session_code"],
            "redirect_url": VIRTUAL_BASE,
            "cdn_base_url": VIRTUAL_BASE,
            "rank_match_info_list": [],
            "player_card": LanBackendServices.player_card({"native_state":native_state or {}, "ranks":rankings or []}),
            "lan_rankings": rankings or [],
            "follow_player_list": [],
            "failed_matching_count": 0,
            "match_disconnection_count": 0,
            "matching_penalty_seconds": 0,
            # This LAN profile has no recorded incomplete matches. Native
            # 145a5d990 uses this byte as the searcher's completion rate, not
            # as a ranking value: advertising0 makes an80%-minimum room
            # reject every clean new player (numeric key7 <= own completion).
            "match_completion_rate": 100,
            "post_and_report_penalty_status": {
                "post_penalty_status": {"penalty_level": 0, "is_penalty_period": False},
                "report_penalty_status": {"penalty_level": 0, "is_penalty_period": False}},
            "rest_report_count": 0,
            "is_new": False,
            "is_relogin": False,
            "maintenance_end_notice_list": [],
        })
