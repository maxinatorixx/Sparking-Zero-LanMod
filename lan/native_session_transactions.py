"""Connection-owned, bounded prepare/commit/abort for native session handoff.

Prepared descriptors have stable IDs but are not discoverable memberships or
UDP routes. Call only on the directory's event-loop thread. This is a server
transaction protocol, not proof that a game has accepted a native descriptor.
"""
from __future__ import annotations

from dataclasses import dataclass
import copy
import re
import time


@dataclass
class _Transaction:
    generation: int
    request: dict
    session: object
    original: object
    expires: float
    state: str = "prepared"
    action: str = ""


class NativeSessionTransactions:
    def __init__(self, directory, clock=time.monotonic, timeout=120):
        if not 0 < timeout <= 120:
            raise ValueError("invalid native transaction timeout")
        self.directory, self.clock, self.timeout = directory, clock, timeout
        # At most one record per established connection. Completed records are
        # tombstones too: old generations cannot mutate a later membership.
        self.records = {}

    def expire(self):
        now = self.clock()
        for record in self.records.values():
            if record.state == "prepared" and now >= record.expires:
                record.state = "aborted"
                record.session = record.original = None

    def disconnect(self, owner):
        self.records.pop(owner, None)

    def has_pending(self, owner):
        self.expire()
        record = self.records.get(owner)
        return record is not None and record.state == "prepared"

    def _reserved(self, session_id, except_owner=None):
        return any(owner != except_owner and record.state == "prepared"
                   and record.action == "join"
                   and record.session.id == session_id
                   for owner, record in self.records.items())

    def reserved_sessions(self):
        self.expire()
        return {record.session.id for record in self.records.values()
                if record.state == "prepared" and record.action == "join"}

    def guard(self, owner, request):
        """Also gate ordinary directory requests so they cannot steal a slot."""
        self.expire()
        if type(request) is not dict:
            return  # The directory supplies its normal validation error.
        record = self.records.get(owner)
        if record and record.state == "prepared":
            if request.get("op") not in ("leave", "search"):
                raise ValueError("native session transaction pending")
        op = request.get("op")
        session_id = request.get("session_id") if op == "join" else self.directory.memberships.get(owner)
        if op in ("join", "update", "set_flags") and self._reserved(session_id, owner):
            raise ValueError("native session join reserved")
        if op == "create":
            pending = sum(item.state == "prepared" and item.action == "create"
                          for item in self.records.values())
            if len(self.directory.sessions) + pending >= self.directory.max_sessions:
                raise ValueError("session directory full")

    def direct(self, owner, request):
        self.guard(owner, request)
        excluded = self.reserved_sessions()
        if type(request) is dict and request.get("op") == "match":
            preview = copy.deepcopy(self.directory)
            result = preview.handle(owner, request, excluded_sessions=excluded)
            if result["action"] == "create":
                self.guard(owner, {"op": "create"})
        result = self.directory.handle(owner, request, excluded_sessions=excluded)
        if request.get("op") == "leave":
            record = self.records.get(owner)
            if record and record.state == "prepared":
                record.state = "aborted"
                record.session = record.original = None
        return result

    def handle(self, owner, request):
        self.expire()
        if not isinstance(owner, str) or re.fullmatch(r"[0-9a-f]{32}", owner) is None:
            raise ValueError("invalid server connection identity")
        if type(request) is not dict:
            raise ValueError("native transaction must be an object")
        op, token = request.get("op"), request.get("transaction_id")
        fields = {"version", "op", "transaction_id"} | ({"request"} if op == "prepare" else set())
        if set(request) != fields or type(request.get("version")) is not int or request["version"] != 1:
            raise ValueError("invalid native transaction fields")
        if op not in ("prepare", "commit", "abort"):
            raise ValueError("unknown native transaction operation")
        match = re.fullmatch(r"rpc-([1-9][0-9]{0,9})", token) if isinstance(token, str) else None
        if not match or int(match[1]) > 2**31-1:
            raise ValueError("invalid native transaction generation")
        generation = int(match[1])
        previous = self.records.get(owner)
        result = {"event": "native_session_transaction", "version": 1,
                  "transaction_id": token, "op": op}
        if previous and generation < previous.generation:
            raise ValueError("stale native transaction generation")
        same = previous is not None and generation == previous.generation
        if op == "prepare":
            payload = request["request"]
            if same:
                if payload != previous.request or previous.state != "prepared":
                    raise ValueError("replayed native transaction generation")
                return dict(result, state="prepared", action=previous.action,
                            session=self.directory._describe(previous.session))
            if previous and previous.state == "prepared":
                raise ValueError("native session transaction pending")
            if (type(payload) is not dict or type(payload.get("version")) is not int
                    or payload["version"] != 2 or payload.get("op") not in ("create", "join", "match")):
                raise ValueError("only version2 create/join/match may be prepared")
            self.guard(owner, payload)
            if payload["op"] == "match":
                for other, record in self.records.items():
                    if (other != owner and record.state == "prepared" and record.action == "create"
                            and record.request.get("partition") == payload.get("partition")):
                        # Stable prepared IDs cannot change into a join during
                        # commit. Serialize discovery behind an invisible host
                        # preparation instead of manufacturing two empty rooms.
                        raise ValueError("native_match_busy")
            # Use precisely the real directory validator and mutation, but on
            # an isolated preview; no rollback of live peer updates is needed.
            preview = copy.deepcopy(self.directory)
            response = preview.handle(owner, payload, excluded_sessions=self.reserved_sessions())
            action = response.get("action", payload["op"])
            if action == "create":
                self.guard(owner, {"op": "create"})
            session_id = response["session"]["session_id"]
            original = copy.deepcopy(self.directory.sessions.get(session_id))
            staged = preview.sessions[session_id]
            self.records[owner] = _Transaction(generation, copy.deepcopy(payload), staged,
                                               original, self.clock()+self.timeout, action=action)
            return dict(result, state="prepared", action=action, session=copy.deepcopy(response["session"]))
        if not same:
            # Cancellation can overtake a queued prepare. Retain its generation
            # so the late prepare cannot create an abandoned membership.
            if op != "abort":
                raise ValueError("unknown native transaction")
            if previous and previous.state == "prepared":
                raise ValueError("native session transaction pending")
            self.records[owner] = _Transaction(generation, {}, None, None, 0, "aborted")
            return dict(result, state="aborted")
        record = previous
        if op == "abort":
            if record.state == "committed":
                # Abort of a completed operation is conditional on its exact
                # membership, never a generic leave that could delete a newer
                # session established by another request.
                live = self.directory.sessions.get(record.session.id)
                if (self.directory.memberships.get(owner) == record.session.id and live is not None
                        and live.members.get(owner) == record.session.members.get(owner)):
                    self.directory.disconnect(owner)
            record.state = "aborted"
            record.session = record.original = None
            return dict(result, state="aborted")
        if record.state == "aborted":
            raise ValueError("native transaction aborted or expired")
        if record.state == "committed":
            current = self.directory.describe_membership(owner)
            live = self.directory.sessions.get(record.session.id)
            if (current is None or current["session_id"] != record.session.id or live is None
                    or live.members.get(owner) != record.session.members.get(owner)):
                raise ValueError("native transaction membership no longer exists")
            return dict(result, state="committed", session=current)
        staged = record.session
        if owner in self.directory.memberships:
            raise ValueError("already a session member")
        current = self.directory.sessions.get(staged.id)
        if current != record.original:
            raise ValueError("native session changed during preparation")
        if record.action == "create" and len(self.directory.sessions) >= self.directory.max_sessions:
            raise ValueError("session directory full")
        self.directory.sessions[staged.id] = copy.deepcopy(staged)
        self.directory.memberships[owner] = staged.id
        record.state = "committed"
        record.original = None
        return dict(result, state="committed", session=self.directory.describe_membership(owner))
