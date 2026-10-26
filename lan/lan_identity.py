"""Explicit LAN-only principals; never platform account identities or login."""
import copy
import re

LAN_PROTOCOL = 4  # Classic installed session IPC already uses protocol 3.
MULTI_PROTOCOL = 5  # Targeted multi-peer transport; isolated from two-player IPC.
_CLIENT = re.compile(r"[0-9a-f]{32}\Z")
_PRINCIPAL = re.compile(rb"szlan:[0-9a-f]{32}\Z")


def principal(client_id):
    if not isinstance(client_id, str) or not _CLIENT.fullmatch(client_id):
        raise ValueError("invalid LAN connection identity")
    return ("szlan:" + client_id).encode("ascii")


def is_principal(value):
    return type(value) is bytes and _PRINCIPAL.fullmatch(value) is not None


def translate_request(request, client_id, protocol=LAN_PROTOCOL):
    """Own independent command copy; preserve the native secondary persona."""
    if type(protocol) is not int or protocol not in (LAN_PROTOCOL, MULTI_PROTOCOL):
        raise ValueError("unsupported LAN partition protocol")
    result = copy.deepcopy(request)
    own = principal(client_id).hex()
    if "partition" in result:
        result["partition"]["protocol"] = protocol
    members = []
    if "native_member" in result:
        members.append(result["native_member"])
    if "native_data" in result:
        members.append(result["native_data"]["member"])
    for member in members:
        member["identity_hex"][0] = own
    return result


def validate_peer_request(directory, client_id, request):
    """Bind reserved LAN identities to the REAL server TCP peer, before writes.

    Existing classic requests remain unchanged. The normal directory validator
    still validates every operation; this guard adds only LAN namespace rules.
    """
    if type(request) is not dict or request.get("version") != 2:
        return
    from native_sessions import _native_member, _native_data
    op = request.get("op")
    members = []
    if "native_member" in request:
        members.append(_native_member(request["native_member"]))
    if "native_data" in request:
        if op in ("create", "match"):
            members.append(_native_data(request["native_data"], request.get("attributes"), 2)["member"])
        elif op == "update":
            supplied = request["native_data"]
            if type(supplied) is not dict or "member" not in supplied:
                raise ValueError("invalid native settings identity")
            members.append(_native_member(supplied["member"]))
    if op == "join":
        sid = request.get("session_id")
        if not isinstance(sid, str) or not _CLIENT.fullmatch(sid):
            raise ValueError("invalid session ID")
        session = directory.sessions.get(sid)
    else:
        session = directory.sessions.get(directory.memberships.get(client_id))
    partition = request.get("partition")
    protocol = partition.get("protocol") if type(partition) is dict else (session.partition[1] if session else None)
    for member in members:
        primary = bytes.fromhex(member["identity_hex"][0])
        lan = primary.startswith(b"szlan:")
        if lan and primary != principal(client_id):
            raise ValueError("LAN identity does not belong to this connection")
        if lan != (protocol in (LAN_PROTOCOL, MULTI_PROTOCOL)):
            raise ValueError("LAN identity namespace and partition mismatch")
        if session and session.native_members:
            owner_member = session.native_members.get(session.creator)
            owner_lan = owner_member is not None and bytes.fromhex(owner_member["identity_hex"][0]).startswith(b"szlan:")
            if owner_lan != lan:
                raise ValueError("LAN and classic session identities cannot mix")


def validate_descriptor(descriptor, max_members=2):
    """Logical HELLO4 snapshots must contain LAN principals, never Steam IDs."""
    members = descriptor.get("members") if type(descriptor) is dict else None
    if type(max_members) is not int or max_members not in (2, 8):
        raise ValueError("unsupported LAN descriptor bound")
    capacity = descriptor.get("capacity") if type(descriptor) is dict else None
    if (type(capacity) is not int or not 1 <= capacity <= max_members
            or (max_members == 2 and capacity != 2)
            or type(members) is not list or not 1 <= len(members) <= capacity):
        raise ValueError("invalid LAN descriptor")
    for member in members:
        try:
            value = bytes.fromhex(member["identity_hex"][0])
        except (KeyError, IndexError, TypeError, ValueError):
            raise ValueError("invalid LAN descriptor identity") from None
        if not is_principal(value):
            raise ValueError("non-LAN descriptor in LAN mode")
