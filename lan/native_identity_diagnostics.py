"""Bounded equality-only diagnostics; never changes native matchmaking state."""
import re

from native_sessions import _native_data, _native_member, _native_text

_UUID = re.compile(r"[0-9a-f]{32}\Z")
_REQUEST = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_ACTIONS = {"create", "join", "match", "update", "search"}


def _safe(value, pattern):
    return value if isinstance(value, str) and pattern.fullmatch(value) else None


def _pair(member):
    if type(member) is not dict:
        raise ValueError("invalid native member")
    values = member.get("identity_hex")
    if type(values) is not list or len(values) != 2:
        raise ValueError("invalid identity pair")
    return tuple(bytes.fromhex(_native_text(value)) for value in values)


class NativeIdentityDiagnostics:
    """Last validated submission per LIVE TCP connection, not payload owner ID.

    Call remember only AFTER the real directory/transaction validator succeeds.
    Independently validate captured fields as defense in depth. Neither raw
    identities, identity hashes, addresses nor opaque settings enter logs.
    """
    def __init__(self, max_clients, logger):
        if type(max_clients) is not int or not 1 <= max_clients <= 256:
            raise ValueError("invalid diagnostics client bound")
        self.max_clients, self.log = max_clients, logger
        self.identities = {}

    def disconnect(self, client_id):
        self.identities.pop(client_id, None)

    def remember(self, client_id, request, *, live_clients, validated=False,
                 wire_op="native_session", request_id=None, result="accepted"):
        if (not validated or _safe(client_id, _UUID) is None or client_id not in live_clients
                or type(request) is not dict or request.get("op") not in _ACTIONS - {"search"}):
            return False
        action = request["op"]
        try:
            if action in ("create", "match"):
                native = _native_data(request["native_data"], request["attributes"], 2)
                member = native["member"]
            else:
                member = _native_member(request["native_member"])
            pair = _pair(member)
        except (ValueError, KeyError, TypeError):
            return False
        # Drop disconnected entries even if a caller missed explicit teardown.
        for old in tuple(self.identities):
            if old not in live_clients:
                self.identities.pop(old, None)
        if client_id not in self.identities and len(self.identities) >= self.max_clients:
            return False
        self.identities[client_id] = pair
        self.log.info("Native identity ingress wire=%s action=%s result=%s client=%s request=%s primary_len=%s secondary_len=%s",
                      "transaction" if wire_op == "native_session_transaction" else "session",
                      action, "prepared" if result == "prepared" else "accepted", client_id,
                      _safe(request_id, _REQUEST), len(pair[0]), len(pair[1]))
        compared = primary_equal = secondary_equal = pair_equal = 0
        for other, previous in self.identities.items():
            if other == client_id:
                continue
            first, second = int(pair[0] == previous[0]), int(pair[1] == previous[1])
            primary_equal += first
            secondary_equal += second
            pair_equal += first and second
            if compared < 4:
                self.log.info("Native identity ingress_compare wire=%s action=%s result=%s client=%s request=%s other_client=%s primary_equal=%s secondary_equal=%s submitted_primary_len=%s other_primary_len=%s submitted_secondary_len=%s other_secondary_len=%s",
                              "transaction" if wire_op == "native_session_transaction" else "session",
                              action, "prepared" if result == "prepared" else "accepted", client_id,
                              _safe(request_id, _REQUEST), other, first, second,
                              len(pair[0]), len(previous[0]), len(pair[1]), len(previous[1]))
            compared += 1
        self.log.info("Native identity ingress_summary client=%s request=%s compared=%s primary_equal_count=%s secondary_equal_count=%s pair_equal_count=%s",
                      client_id, _safe(request_id, _REQUEST), compared, primary_equal,
                      secondary_equal, pair_equal)
        return True

    def returned(self, client_id, request_id, sessions):
        """Compare at most four server-returned owners with requester ingress.

        A missing requester is unknown (-1), not unequal. Owner identity comes
        ONLY from the server-returned descriptor, never a requester payload.
        """
        if _safe(client_id, _UUID) is None or type(sessions) is not list:
            return
        requester = self.identities.get(client_id)
        for session in sessions[:4]:
            if type(session) is not dict:
                continue
            descriptor = session.get("native_descriptor")
            members = descriptor.get("members") if type(descriptor) is dict else None
            if type(members) is not list or not 1 <= len(members) <= 8:
                continue
            owners = [member for member in members if type(member) is dict and member.get("owner") is True]
            if len(owners) != 1:
                continue
            owner = owners[0]
            try:
                pair = _pair(owner)
            except (ValueError, KeyError, TypeError):
                continue
            equal = tuple(int(a == b) for a, b in zip(requester, pair)) if requester else (-1, -1)
            lengths = tuple(map(len, requester)) if requester else (-1, -1)
            self.log.info("Native identity candidate wire=session action=search result=returned client=%s request=%s session=%s member=%s primary_equal=%s secondary_equal=%s requester_primary_len=%s owner_primary_len=%s requester_secondary_len=%s owner_secondary_len=%s",
                          client_id, _safe(request_id, _REQUEST), _safe(session.get("session_id"), _UUID),
                          _safe(owner.get("id"), _UUID), equal[0], equal[1], lengths[0], len(pair[0]),
                          lengths[1], len(pair[1]))
