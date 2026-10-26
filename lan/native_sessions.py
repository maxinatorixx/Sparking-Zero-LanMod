"""Bounded central session directory, separate from legacy sidecar matchmaking.

This is a server data model, NOT a native game ABI or a working game adapter.
Call only with the owner ID of the current, server-established connection.
Search is an immediate snapshot; it creates no pending task to cancel.
Version1 retains explicit equality only. Version2 supports the recovered
numeric/OR predicate and explicitly selected compatibility normalization; this
is not the full distance/room policy. Partitions are our protocol namespace,
not recovered game enum labels. Numeric attribute meanings remain opaque.

Optional materialization profile 1 preserves explicit constructor input values
for a future client-side materializer. It supports only absent stream/empty
properties and does not decode identity/address bytes or invent their meaning.
The server assigns IDs, join order and creator ownership; all other native
fields must be supplied explicitly. Version2/profile2 additionally preserves a
bounded known-layout stream payload/cursors and supports member/settings updates.
Its shared local-member marker is zero: native clients localize their OWN copy.
Opaque settings payloads are not interpreted or logged. No native constructor
is called here, and the installed search-only bridge does not use this API.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import copy
import base64
import binascii
import json
import logging
import re
import uuid

from native_search import validate_request as validate_native_query

VERSION = 1
MAX_SESSIONS = 128
MAX_ATTRIBUTES = 16
MAX_RESULTS = 4
MAX_MULTI_MEMBERS = 8
MULTI_PROTOCOL = 5
_HEX = re.compile(r"[0-9a-f]{32}\Z")
_BUILD = re.compile(r"[0-9a-f]{64}\Z")
_REQUEST = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_KEY = re.compile(r"0|[1-9][0-9]{0,19}\Z")
_NATIVE_HEX = re.compile(r"(?:[0-9a-f]{2}){1,64}\Z")
LOG = logging.getLogger("szero_lan")


def _fields(value, required):
    if type(value) is not dict or set(value) != set(required):
        raise ValueError("unexpected or missing session request fields")


def _integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError("session numeric value out of bounds")
    return value


def _key(value):
    if not isinstance(value, str) or not _KEY.fullmatch(value) or int(value) > 2**64 - 1:
        raise ValueError("attribute key must be a canonical uint64 string")
    return value


def _partition(value):
    _fields(value, ("build", "protocol", "mode"))
    if not isinstance(value["build"], str) or not _BUILD.fullmatch(value["build"]):
        raise ValueError("build must be a lowercase SHA-256")
    return (value["build"], _integer(value["protocol"], 1, 2**32 - 1),
            _integer(value["mode"], 0, 2**32 - 1))


def _attributes(value):
    if type(value) is not dict or len(value) > MAX_ATTRIBUTES:
        raise ValueError("too many session attributes")
    return {_key(k): _integer(v, -(2**31), 2**31 - 1) for k, v in value.items()}


def _filters(value):
    if type(value) is not list or len(value) > MAX_ATTRIBUTES:
        raise ValueError("too many session filters")
    result = {}
    for item in value:
        _fields(item, ("key", "comparison", "value"))
        if item["comparison"] != "eq":
            raise ValueError("only explicit equality session filters are supported")
        key = _key(item["key"])
        if key in result:
            raise ValueError("duplicate session filter")
        result[key] = _integer(item["value"], -(2**31), 2**31 - 1)
    return result


def _native_text(value):
    if (not isinstance(value, str) or not _NATIVE_HEX.fullmatch(value)
            or b"\0" in bytes.fromhex(value)):
        raise ValueError("native text must be canonical nonempty hex without NUL, at most 64 bytes")
    return value


def _native_member(value):
    _fields(value, ("identity_hex", "address_hex", "field_88", "optional_present",
                    "optional_value", "field_8b"))
    identities = value["identity_hex"]
    if type(identities) is not list or len(identities) != 2:
        raise ValueError("native member requires exactly two identity values")
    if type(value["optional_present"]) is not bool:
        raise ValueError("native optional_present must be boolean")
    return {"identity_hex": [_native_text(item) for item in identities],
            "address_hex": _native_text(value["address_hex"]),
            "field_88": _integer(value["field_88"], 0, 255),
            "optional_present": value["optional_present"],
            "optional_value": _integer(value["optional_value"], 0, 255),
            "field_8b": _integer(value["field_8b"], 0, 255)}


def _native_stream(value):
    if value is None:
        return None
    _fields(value, ("kind", "data_base64", "read_cursor", "write_cursor"))
    encoded = value["data_base64"]
    if value["kind"] != "spnet-memory-v1" or not isinstance(encoded, str) or len(encoded) > 5464:
        raise ValueError("unsupported or oversized native stream")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError("invalid native stream encoding") from None
    if len(data) > 4096 or base64.b64encode(data).decode("ascii") != encoded:
        raise ValueError("invalid native stream encoding or size")
    return {"kind": "spnet-memory-v1", "data_base64": encoded,
            "read_cursor": _integer(value["read_cursor"], 0, len(data)),
            "write_cursor": _integer(value["write_cursor"], 0, len(data))}


def _native_data(value, attributes, version=1):
    _fields(value, ("profile", "compatibility", "numeric", "capacity", "field_e1",
                    "stream", "properties", "member"))
    if type(value["profile"]) is not int or value["profile"] != version:
        raise ValueError("unsupported native materialization profile")
    numeric = value["numeric"]
    if type(numeric) is not list or len(numeric) > MAX_ATTRIBUTES:
        raise ValueError("native numeric values must be a bounded list")
    numeric = [_integer(item, -(2**31), 2**31 - 1) for item in numeric]
    # Keep search filters consistent with the descriptor returned on discovery.
    # These are opaque numeric slots, not character/selection field names.
    if attributes != {str(index): item for index, item in enumerate(numeric)}:
        raise ValueError("attributes must exactly index native numeric values")
    capacity = _integer(value["capacity"], 1, MAX_MULTI_MEMBERS if version == 2 else 2)
    if version == 1 and capacity != 2:
        raise ValueError("native profile1 requires capacity two")
    if type(value["properties"]) is not list or value["properties"]:
        raise ValueError("nonempty native properties are not supported")
    if version == 1 and value["stream"] is not None:
        raise ValueError("native stream is not supported in profile1")
    member = _native_member(value["member"])
    if version == 2:
        member["field_8b"] = 0  # Recovered process-local marker; native adapter localizes it.
    return {"profile": version,
            "compatibility": _integer(value["compatibility"], 0, 2**32 - 1),
            "numeric": numeric, "capacity": capacity,
            "field_e1": _integer(value["field_e1"], 0, 255),
            "stream": _native_stream(value["stream"]) if version == 2 else None,
            "properties": [], "member": member}


def native_numeric_decision(query, candidate, default_normalize):
    """Recovered numeric/compatibility predicate ONLY, not distance/room policy.

    Native missing positional keys are permissive, including in OR-pairs.
    Default normalization must be supplied explicitly, never guessed here.
    """
    if type(default_normalize) is not bool:
        raise ValueError("native compatibility default must be explicit boolean")
    validate_native_query({"op": "begin", "id": 1, "query": query})
    if query["compound_count"] and "compound_filters" not in query:
        raise ValueError("compound predicate values required")
    left, right = query["compatibility"], candidate["compatibility"]
    mode = query["field_4e"]
    normalize = default_normalize if mode == 255 else mode != 0
    if left and right:
        if normalize:
            left, right = ((left - 1) & 0xffffffff) % 1000, ((right - 1) & 0xffffffff) % 1000
        if left != right:
            return "compatibility", {"query": left, "candidate": right, "normalized": normalize}
    numeric = candidate["numeric"]

    def predicate(item):
        key = int(item["key"])
        if key >= len(numeric):
            return None
        a, b, op = numeric[key], item["value"], item["comparison"]
        return (a == b, a < b, a <= b, a > b, a >= b)[op]

    def detail(item):
        key = int(item["key"])
        return {"key": key, "comparison": item["comparison"], "query": item["value"],
                "candidate": numeric[key] if key < len(numeric) else None}

    for index, item in enumerate(query["filters"]):
        if predicate(item) is False:
            return "numeric", {"index": index, **detail(item)}
    for index, pair in enumerate(query.get("compound_filters", [])):
        if predicate(pair["first"]) is False and predicate(pair["second"]) is False:
            return "compound", {"index": index, "first": detail(pair["first"]),
                                "second": detail(pair["second"])}
    return None, {}


def native_numeric_matches(query, candidate, default_normalize):
    return native_numeric_decision(query, candidate, default_normalize)[0] is None


def _candidate_decision(session, owner, partition, version, profile, filters,
                        query, normalize, excluded, match_identity=None):
    """The actual admission predicate, shared with bounded diagnostics."""
    for rejected, reason in ((session.id in excluded, "reserved"),
            (session.version != version, "version"), (session.partition != partition, "partition"),
            (len(session.members) >= session.capacity, "full"),
            (version == 2 and bool(session.create_flags & 5), "flags")):
        if rejected:
            return reason, {}
    if match_identity is None:
        if (session.native_data is not None) != (profile in (1, 2)):
            return "profile", {}
        if owner in session.members:
            return "own", {}
        if not all(session.attributes.get(k) == v for k, v in filters.items()):
            return "numeric", {}
    if version == 2:
        reason, detail = native_numeric_decision(query, session.native_data, normalize)
        if reason:
            return reason, detail
    if match_identity is not None and any(value["identity_hex"] == match_identity
                                           for value in session.native_members.values()):
        return "own", {}
    return None, {}


class _SearchDiagnostics:
    def __init__(self, owner, request, total):
        self.owner, self.request, self.total = owner, request, total
        self.counts = {key: 0 for key in ("reserved", "version", "partition", "full", "flags",
                       "profile", "own", "compatibility", "numeric", "compound", "accepted")}
        self.details = []

    def observe(self, session, reason, detail):
        self.counts[reason or "accepted"] += 1
        if len(self.details) < 4:
            self.details.append({"session": session.id, "reason": reason or "accepted",
                                 "members": len(session.members), "flags": session.create_flags, **detail})

    def emit(self):
        request = self.request
        query = request.get("query", {})
        LOG.info("Native candidates client=%s request=%s op=%s profile=%s total=%s scanned=%s "
                 "results=%s numeric=%s compound=%s normalization=%s default_normalize=%s counts=%s details=%s",
                 self.owner, request["request_id"], request["op"], request.get("materialization_profile", 2 if request["op"] == "match" else 0),
                 self.total, sum(self.counts.values()), self.counts["accepted"],
                 len(query.get("filters", [])), query.get("compound_count", 0),
                 query.get("field_4e"), request.get("default_normalize"), json.dumps(self.counts, separators=(",", ":")),
                 json.dumps(self.details, separators=(",", ":")))


@dataclass
class _Session:
    id: str
    partition: tuple
    attributes: dict
    creator: str
    members: dict[str, str] = field(default_factory=dict)
    native_data: dict | None = None
    native_members: dict[str, dict] = field(default_factory=dict)
    version: int = 1
    create_flags: int = 0

    @property
    def capacity(self):
        return self.native_data["capacity"] if self.native_data is not None else 2


class NativeSessionDirectory:
    """Use on the server event-loop thread; no awaits or external I/O inside.

    Owner IDs and membership are never supplied in request payloads. An owner
    belongs to at most one session. Creator departure revokes the whole session
    rather than silently promoting a guest into an unverified native host role.
    Full sessions are not discoverable; joining one cannot displace a member.
    """

    def __init__(self, max_sessions=MAX_SESSIONS, candidate_policy=None):
        self.candidate_policy=candidate_policy
        self.max_sessions = _integer(max_sessions, 1, MAX_SESSIONS)
        self.sessions = {}
        self.memberships = {}

    def has_membership(self, owner_id):
        return owner_id in self.memberships

    def member_owners(self, owner_id):
        """Server-only connection IDs for membership-change notifications."""
        session = self.sessions.get(self.memberships.get(owner_id))
        return tuple(session.members) if session else ()

    def relay_peer(self, owner_id, session_id):
        """Server-only connection routing; never a native battle-ready signal."""
        session = self.sessions.get(self.memberships.get(owner_id))
        if session is None or session.version != 2 or session.id != session_id or len(session.members) != 2:
            return None
        return next((other for other in session.members if other != owner_id), None)

    def describe_membership(self, owner_id):
        session = self.sessions.get(self.memberships.get(owner_id))
        return self._describe(session) if session else None

    @staticmethod
    def _describe(session):
        build, protocol, mode = session.partition
        result = {"session_id": session.id,
                "partition": {"build": build, "protocol": protocol, "mode": mode},
                "attributes": dict(session.attributes), "capacity": session.capacity,
                "members": [{"member_id": member, "join_order": index}
                            for index, member in enumerate(session.members.values())]}
        if session.version == 2:
            result["create_flags"] = session.create_flags
        if session.native_data is not None:
            descriptor = copy.deepcopy(session.native_data)
            descriptor.pop("member")
            descriptor["id"] = session.id
            descriptor["members"] = [dict(copy.deepcopy(session.native_members[owner]),
                                            id=member, join_order=index,
                                            owner=owner == session.creator)
                                     for index, (owner, member) in enumerate(session.members.items())]
            result["native_descriptor"] = descriptor
        return result

    def handle(self, owner_id, request, *, excluded_sessions=()):
        if not isinstance(owner_id, str) or not _HEX.fullmatch(owner_id):
            raise ValueError("invalid server connection identity")
        if type(request) is not dict:
            raise ValueError("session request must be an object")
        op = request.get("op")
        version = request.get("version")
        if type(version) is not int or version not in (1, 2):
            raise ValueError("unsupported session directory version")
        extras = {"create": ("partition", "attributes"),
                  "search": ("partition", "filters", "limit"),
                  "join": ("partition", "session_id"), "leave": ()}
        if version == 2:
            extras["search"] = ("partition", "query", "default_normalize", "limit")
            extras["update"] = ("native_member",)
            extras["set_flags"] = ("flags",)
            extras["match"] = ("partition", "attributes", "native_data", "query", "default_normalize", "create_flags")
        if not isinstance(op, str) or op not in extras:
            raise ValueError("unsupported session operation")
        optional = {"create": "native_data", "search": "materialization_profile",
                    "join": "native_member"}.get(op)
        if version == 2 and op == "update":
            optional = "native_data"
        required = ("version", "request_id", "op", *extras[op])
        permitted = (*required, optional) if optional is not None and optional in request else required
        if version == 2 and op == "create" and "create_flags" in request:
            permitted = (*permitted, "create_flags")
        _fields(request, permitted)
        request_id = request["request_id"]
        if not isinstance(request_id, str) or not _REQUEST.fullmatch(request_id):
            raise ValueError("invalid session request ID")
        partition = _partition(request["partition"]) if op not in ("leave", "update", "set_flags") else None
        result = {"event": "native_session_result", "version": version,
                  "request_id": request_id, "op": op}
        if op == "match":
            # Exact recovered LOCAL +a0 policy: validate all creation inputs,
            # search admitted candidates, join first available or create. This
            # method runs without awaits on the central event-loop thread.
            if owner_id in self.memberships:
                raise ValueError("already a session member")
            attributes = _attributes(request["attributes"])
            native = _native_data(request["native_data"], attributes, 2)
            if native["capacity"] != 2 and partition[1] != MULTI_PROTOCOL:
                raise ValueError("multiple participants require the multi-peer transport partition")
            flags = _integer(request["create_flags"], 0, 65535)
            if type(request["default_normalize"]) is not bool:
                raise ValueError("native compatibility default must be explicit boolean")
            validate_native_query({"op": "begin", "id": 1, "query": request["query"]})
            if request["query"]["compound_count"] and "compound_filters" not in request["query"]:
                raise ValueError("compound predicate values required")
            diagnostics = _SearchDiagnostics(owner_id, request, len(self.sessions))
            eligible=[]
            for session in self.sessions.values():
                reason, detail = _candidate_decision(session, owner_id, partition, 2, 2, {},
                    request["query"], request["default_normalize"], excluded_sessions, native["member"]["identity_hex"])
                diagnostics.observe(session, reason, detail)
                if reason is None:eligible.append(session)
            if self.candidate_policy is not None:eligible=self.candidate_policy.candidates(owner_id,request,eligible)
            for session in eligible:
                diagnostics.emit()
                joined = self.handle(owner_id, {"version": 2, "request_id": request_id, "op": "join",
                    "partition": request["partition"], "session_id": session.id, "native_member": native["member"]})
                return dict(result, action="join", session=joined["session"])
            diagnostics.emit()
            created = self.handle(owner_id, {"version": 2, "request_id": request_id, "op": "create",
                "partition": request["partition"], "attributes": attributes, "native_data": native, "create_flags": flags})
            return dict(result, action="create", session=created["session"])
        elif op == "create":
            attributes = _attributes(request["attributes"])
            native = _native_data(request["native_data"], attributes, version) if "native_data" in request else None
            if native is not None and native["capacity"] != 2 and partition[1] != MULTI_PROTOCOL:
                raise ValueError("multiple participants require the multi-peer transport partition")
            if version == 2 and native is None:
                raise ValueError("version2 requires complete native_data")
            flags = _integer(request.get("create_flags", 0), 0, 65535)
            if owner_id in self.memberships:
                raise ValueError("already a session member")
            if len(self.sessions) >= self.max_sessions:
                raise ValueError("session directory full")
            session = _Session(uuid.uuid4().hex, partition, attributes, owner_id,
                               {owner_id: uuid.uuid4().hex}, native,
                               {owner_id: copy.deepcopy(native["member"])} if native else {}, version, flags)
            self.sessions[session.id] = session
            self.memberships[owner_id] = session.id
            if self.candidate_policy is not None:self.candidate_policy.created(owner_id,native)
            result["session"] = self._describe(session)
        elif op == "search":
            filters = _filters(request["filters"]) if version == 1 else {}
            limit = _integer(request["limit"], 1, MAX_RESULTS if version == 1 else 1)
            profile = request.get("materialization_profile")
            if "materialization_profile" in request and (type(profile) is not int or profile != version):
                raise ValueError("unsupported native materialization profile")
            if version == 2:
                if profile != 2 or type(request["default_normalize"]) is not bool:
                    raise ValueError("version2 requires explicit profile/default normalization")
                validate_native_query({"op": "begin", "id": 1, "query": request["query"]})
                if request["query"]["compound_count"] and "compound_filters" not in request["query"]:
                    raise ValueError("compound predicate values required")
                result["numeric_filter_only"] = True
            result["sessions"] = []
            eligible=[]
            diagnostics = _SearchDiagnostics(owner_id, request, len(self.sessions))
            for session in self.sessions.values():
                reason, detail = _candidate_decision(session, owner_id, partition, version, profile, filters,
                    request.get("query"), request.get("default_normalize"), excluded_sessions)
                diagnostics.observe(session, reason, detail)
                if reason is None:eligible.append(session)
            if self.candidate_policy is not None:eligible=self.candidate_policy.candidates(owner_id,request,eligible)
            result["sessions"]=[self._describe(session) for session in eligible[:limit]]
            diagnostics.emit()
        elif op == "join":
            session_id = request["session_id"]
            if not isinstance(session_id, str) or not _HEX.fullmatch(session_id):
                raise ValueError("invalid session ID")
            session = self.sessions.get(session_id)
            if session is None or session.version != version or session.partition != partition:
                raise ValueError("session unavailable")
            native_member = None
            if session.native_data is not None:
                if "native_member" not in request:
                    raise ValueError("native session requires native_member")
                native_member = _native_member(request["native_member"])
                if version == 2:
                    native_member["field_8b"] = 0
                    if any(existing["identity_hex"] == native_member["identity_hex"]
                           for existing in session.native_members.values()):
                        raise ValueError("duplicate native member identity")
            elif "native_member" in request:
                raise ValueError("legacy session does not accept native_member")
            if owner_id in self.memberships:
                raise ValueError("already a session member")
            if len(session.members) >= session.capacity:
                raise ValueError("session full")
            session.members[owner_id] = uuid.uuid4().hex
            if native_member is not None:
                session.native_members[owner_id] = native_member
            self.memberships[owner_id] = session.id
            result["session"] = self._describe(session)
        elif op == "set_flags":
            flags = _integer(request["flags"], 0, 65535)
            session = self.sessions.get(self.memberships.get(owner_id))
            if session is None or session.version != 2:
                raise ValueError("no version2 session membership")
            if owner_id != session.creator:
                raise ValueError("only creator may update native session flags")
            session.create_flags = session.create_flags & 0xfffc | flags & 3
            result["session"] = self._describe(session)
        elif op == "update":
            session = self.sessions.get(self.memberships.get(owner_id))
            if session is None or session.version != 2:
                raise ValueError("no version2 session membership")
            member = _native_member(request["native_member"])
            member["field_8b"] = 0
            if member["identity_hex"] != session.native_members[owner_id]["identity_hex"]:
                raise ValueError("native identity cannot change in an active session")
            native = None
            if "native_data" in request:
                if owner_id != session.creator:
                    raise ValueError("only creator may update native settings")
                supplied = request["native_data"]
                if type(supplied) is not dict or type(supplied.get("numeric")) is not list:
                    raise ValueError("complete native settings required")
                attributes = _attributes({str(i): value for i, value in enumerate(supplied["numeric"])})
                native = _native_data(supplied, attributes, 2)
                if native["capacity"] < len(session.members):
                    raise ValueError("native capacity cannot exclude current participants")
                if native["capacity"] != 2 and session.partition[1] != MULTI_PROTOCOL:
                    raise ValueError("multiple participants require the multi-peer transport partition")
                if native["member"] != member:
                    raise ValueError("settings member must agree with updated member")
            session.native_members[owner_id] = member
            if native is not None:
                session.native_data = native
                session.attributes = attributes
            result["session"] = self._describe(session)
        else:
            result["left"] = self.has_membership(owner_id)
            self.disconnect(owner_id)
        return result

    def disconnect(self, owner_id):
        """Remove member; return other connection IDs needing a state refresh.

        The caller must not expose these internal connection IDs on the wire.
        Calling twice is safe. All descriptors/partitions returned by handle
        are independent copies, never mutable aliases into directory storage.
        """
        if self.candidate_policy is not None:self.candidate_policy.cancel(owner_id)
        session_id = self.memberships.pop(owner_id, None)
        session = self.sessions.get(session_id)
        if session is None:
            return ()
        session.members.pop(owner_id, None)
        session.native_members.pop(owner_id, None)
        affected = tuple(session.members)
        if owner_id == session.creator:
            self.sessions.pop(session.id)
            for other in affected:
                self.memberships.pop(other, None)
        return affected
