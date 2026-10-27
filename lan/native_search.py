"""Bounded native IPC: legacy pending search and explicit session-v3 values.

Session mutations use leased server prepare/commit/abort transactions. No native
pointers cross IPC, and server DTOs are never treated as native object handles.
"""
from __future__ import annotations

import copy
import base64
import logging
from pathlib import Path
import queue
import re
import select
import socket
import threading
import time

from installer import atomic_write

MAX_LINE = 8192
MAX_SESSION_LINE = 16384
# Historical layout/protocol partition, NOT a digest read from the game EXE.
# Keep its value stable for existing compatible servers and native clients.
SESSION_PARTITION = {"build": "e54e79e756f79719f09915078a37b6e87c23d32ecaaaa2f485d1a048ba198e55",
                     "protocol": 3, "mode": 0}
LOG = logging.getLogger("szero_lan")
_INSTANCE = re.compile(r"[0-9a-f]{32}\Z")
_DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)\Z")
_SIGNED = re.compile(r"(?:0|-?[1-9][0-9]*)\Z")


class _SessionFinished(Exception):
    pass


def parse_session_command(line):
    """Value-only v3 IPC. Every number/text is validated before forwarding."""
    from native_sessions import _native_member, _native_data
    if type(line) is not bytes or not line.endswith(b"\n") or len(line) > MAX_SESSION_LINE:
        raise ValueError("invalid session IPC frame")
    try:
        parts = line[:-1].decode("ascii").split(" ")
    except UnicodeError:
        raise ValueError("non-ASCII session IPC") from None
    if any(not part for part in parts):
        raise ValueError("noncanonical session spacing")
    pos = 1
    def num(low=0, high=2**64-1, signed=False):
        nonlocal pos
        if pos >= len(parts) or not (_SIGNED if signed else _DECIMAL).fullmatch(parts[pos]) or len(parts[pos]) > 20:
            raise ValueError("invalid session number")
        value = integer(int(parts[pos]), low, high)
        pos += 1
        return value
    def token():
        nonlocal pos
        if pos >= len(parts):
            raise ValueError("missing session field")
        value = parts[pos]
        pos += 1
        return value
    def member():
        value = {"identity_hex": [token(), token()], "address_hex": token(),
                 "field_88": num(0, 255), "optional_present": bool(num(0, 1)),
                 "optional_value": num(0, 255), "field_8b": 0}
        return _native_member(value)
    generation = num(1, 2**31-1)
    verb = parts[0]
    op = {"CREATE3": "create", "MATCH3": "match", "SEARCH3": "search", "JOIN3": "join", "UPDATE3": "update",
          "UPDATESETTINGS3": "update",
          "POLL3": "poll", "FLAGS3": "set_flags",
          "LEAVE3": "leave", "ACK3": "commit", "CANCEL3": "abort"}.get(verb)
    if op is None:
        raise ValueError("unknown session IPC command")
    request = {"version": 2, "request_id": f"rpc-{generation}", "op": op}
    if op in ("create", "match", "join", "search"):
        request["partition"] = dict(SESSION_PARTITION)
    if op in ("create", "match") or verb == "UPDATESETTINGS3":
        compatibility = num(0, 2**32-1)
        count = num(0, 16)
        numbers = [num(-(2**31), 2**31-1, True) for _ in range(count)]
        capacity, field_e1 = num(1, 8), num(0, 255)
        present, size, read, write = num(0, 1), num(0, 4096), num(), num()
        encoded = token()
        if encoded == "-":
            payload = b""
        elif not re.fullmatch(r"(?:[0-9a-f]{2})+", encoded):
            raise ValueError("invalid session stream hex")
        else:
            payload = bytes.fromhex(encoded)
        if size != len(payload) or (not present and (size or read or write)):
            raise ValueError("invalid absent session stream")
        stream = ({"kind": "spnet-memory-v1", "data_base64": base64.b64encode(payload).decode("ascii"),
                   "read_cursor": read, "write_cursor": write} if present else None)
        attributes = {str(i): n for i, n in enumerate(numbers)}
        request["native_data"] = _native_data({"profile": 2, "compatibility": compatibility,
            "numeric": numbers, "capacity": capacity, "field_e1": field_e1,
            "stream": stream, "properties": [], "member": member()}, attributes, 2)
        if verb == "UPDATESETTINGS3":
            request["native_member"] = copy.deepcopy(request["native_data"]["member"])
        else:
            request["attributes"] = attributes
            request["create_flags"] = num(0, 65535)
    if op in ("search", "match"):
        normalize = bool(num(0, 1))
        # Reuse the exact BEGIN2 validator rather than maintaining two query parsers.
        request.update(query=parse_command(("BEGIN2 1 " + " ".join(parts[pos:]) + "\n").encode("ascii"))["query"],
                       default_normalize=normalize, materialization_profile=2, limit=1)
        pos = len(parts)
        if op == "match":
            request.pop("materialization_profile")
            request.pop("limit")
    elif op == "join":
        sid = token()
        if not _INSTANCE.fullmatch(sid):
            raise ValueError("invalid session ID")
        request.update(session_id=sid, native_member=member())
    elif op == "update" and verb != "UPDATESETTINGS3":
        request["native_member"] = member()
    elif op == "set_flags":
        request["flags"] = num(0, 65535)
    if pos != len(parts):
        raise ValueError("extra session IPC fields")
    return {"id": generation, "op": op, "channel": "native_session", "request": request}


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError("native search number out of bounds")
    return value


def fields(value, expected):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError("unexpected native search fields")


def predicate(item):
    fields(item, ("key", "comparison", "value"))
    key = item["key"]
    if not isinstance(key, str) or len(key) > 20 or not _DECIMAL.fullmatch(key) or int(key) >= 2**64:
        raise ValueError("invalid native search key")
    integer(item["comparison"], 0, 4)
    integer(item["value"], -(2**31), 2**31 - 1)


def validate_request(request):
    if type(request) is not dict:
        raise ValueError("native search must be an object")
    op = request.get("op")
    if op not in ("begin", "cancel"):
        raise ValueError("unknown native search operation")
    fields(request, ("op", "id", "query") if op == "begin" else ("op", "id"))
    integer(request["id"], 1, 2**31 - 1)
    if op == "cancel":
        return copy.deepcopy(request)
    query = request["query"]
    expected = ("compatibility", "filters", "compound_count", "distance",
                "field_4c", "field_4d", "field_4e")
    fields(query, (*expected, "compound_filters") if type(query) is dict and "compound_filters" in query else expected)
    integer(query["compatibility"], 0, 2**32 - 1)
    integer(query["compound_count"], 0, 16)
    integer(query["distance"], 0, 2**32 - 1)
    for key in ("field_4c", "field_4d", "field_4e"):
        integer(query[key], 0, 255)
    if type(query["filters"]) is not list or len(query["filters"]) > 16:
        raise ValueError("too many native search filters")
    for item in query["filters"]:
        predicate(item)
    if "compound_filters" in query:
        pairs = query["compound_filters"]
        if type(pairs) is not list or len(pairs) != query["compound_count"]:
            raise ValueError("native compound count mismatch")
        for pair in pairs:
            fields(pair, ("first", "second"))
            predicate(pair["first"])
            predicate(pair["second"])
    return copy.deepcopy(request)


class NativeSearchRegistry:
    """Connection-owned outstanding searches; call on the server event loop."""

    def __init__(self):
        self.pending = {}

    def handle(self, owner, request):
        request = validate_request(request)
        result = {"event": "native_search", "id": request["id"]}
        current = self.pending.get(owner)
        if request["op"] == "cancel":
            if current is not None and current["id"] == request["id"]:
                self.pending.pop(owner)
            return dict(result, state="cancelled")
        if request["query"]["compound_count"] and "compound_filters" not in request["query"]:
            return dict(result, state="error", error="unsupported_compound_query")
        if current is not None and current != request:
            return dict(result, state="error", error="already_searching")
        self.pending[owner] = request
        return dict(result, state="pending")

    def disconnect(self, owner):
        self.pending.pop(owner, None)


def parse_command(line):
    """Parse one bounded ASCII command, including its terminal newline."""
    if type(line) is not bytes or not line.endswith(b"\n") or len(line) > MAX_LINE:
        raise ValueError("invalid native IPC frame")
    try:
        text = line[:-1].decode("ascii")
    except UnicodeError as exc:
        raise ValueError("non-ASCII native IPC frame") from exc
    parts = text.split(" ")
    if any(not part for part in parts):
        raise ValueError("noncanonical native IPC spacing")

    def number(index, signed=False):
        value = parts[index]
        if len(value) > 20 or not (_SIGNED if signed else _DECIMAL).fullmatch(value):
            raise ValueError("noncanonical native IPC number")
        return int(value)

    try:
        if parts[0] == "CANCEL" and len(parts) == 2:
            return validate_request({"op": "cancel", "id": number(1)})
        if parts[0] not in ("BEGIN", "BEGIN2") or len(parts) < 9:
            raise ValueError("invalid native IPC command")
        count = integer(number(3), 0, 16)
        filters = [{"key": parts[4 + 3*i], "comparison": number(5 + 3*i),
                    "value": number(6 + 3*i, True)} for i in range(count)]
        offset = 4 + 3 * count
        compound_count = integer(number(offset), 0, 16)
        compound = {}
        if parts[0] == "BEGIN2":
            if len(parts) != 9 + 3 * count + 6 * compound_count:
                raise ValueError("invalid native IPC field count")
            pairs = []
            for i in range(compound_count):
                start = offset + 1 + 6*i
                pairs.append({"first": {"key": parts[start], "comparison": number(start+1),
                                         "value": number(start+2, True)},
                              "second": {"key": parts[start+3], "comparison": number(start+4),
                                          "value": number(start+5, True)}})
            compound["compound_filters"] = pairs
            offset += 6 * compound_count
        elif len(parts) != 9 + 3 * count:
            raise ValueError("invalid native IPC field count")
        return validate_request({"op": "begin", "id": number(1), "query": {
            "compatibility": number(2), "filters": filters,
            "compound_count": compound_count, **compound, "distance": number(offset+1),
            "field_4c": number(offset+2), "field_4d": number(offset+3),
            "field_4e": number(offset+4)}})
    except IndexError as exc:
        raise ValueError("incomplete native IPC command") from exc


class NativeSearchRPC:
    """One loopback helper connection, bounded queues, instance-scoped endpoint.

    The worker is the sole writer to the socket. GameBridge drains commands
    and publishes server events; it never blocks on native helper socket I/O.
    An idle pending connection remains open for at most 120 seconds.
    """

    def __init__(self, runtime, instance):
        if not isinstance(instance, str) or not _INSTANCE.fullmatch(instance):
            raise ValueError("invalid native IPC instance")
        self.instance = instance
        self.endpoint = Path(runtime).with_suffix(".native.endpoint")
        self.commands = queue.Queue(maxsize=16)
        self.cleanup = queue.Queue(maxsize=16)
        self.outbound = queue.Queue(maxsize=16)
        self.session_outbound = queue.Queue(maxsize=16)
        self.session_latest = 0
        self.session_committed = None
        self.session_snapshot = None
        self.transport_ports = None
        self.session_identity = None
        self.lan_binding = None
        self.lan_invalid = False
        self.lan_lock = threading.Lock()
        self.lan_session_mode = False
        self.multi_session_mode = False
        self.multi_proxy_ports = None
        self.remote_proxy = None
        self.multi_capability = False
        self.stop = threading.Event()
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.listener.settimeout(0.1)
        self.port = self.listener.getsockname()[1]
        self.endpoint_text = f"SZERO_NATIVE_ENDPOINT_V1 {self.port} {instance}\n"
        self.client = None
        try:
            atomic_write(self.endpoint, self.endpoint_text.encode("ascii"))
        except BaseException:
            self.listener.close()
            raise
        self.thread = threading.Thread(target=self._run, daemon=True, name="native-search-ipc")
        self.thread.start()
        LOG.info("NativeIPC ready")

    def bind_lan_identity(self, client_id, capabilities):
        """Pin one server connection for this process; reconnect needs restart."""
        from lan_identity import principal
        with self.lan_lock:
            try:
                own = principal(client_id)
                valid = (type(capabilities) is dict and type(capabilities.get("native_lan_identity")) is int
                         and capabilities["native_lan_identity"] == 1)
            except ValueError:
                valid = False
                own = None
            if not valid or self.lan_invalid or (self.lan_binding is not None and self.lan_binding != own):
                if self.lan_binding is not None:
                    self.lan_invalid = True
                return False
            self.lan_binding = own
            return True

    def invalidate_lan_identity(self):
        with self.lan_lock:
            if self.lan_binding is not None:
                self.lan_invalid = True

    def _lan_identity(self):
        with self.lan_lock:
            return None if self.lan_invalid else self.lan_binding

    def drain(self):
        result = []
        while True:
            try:
                result.append(self.commands.get_nowait())
            except queue.Empty:
                break
        while True:
            try:
                result.append(self.cleanup.get_nowait())
            except queue.Empty:
                return result

    def publish(self, event):
        if type(event) is dict and event.get("event") == "native_session_state":
            session = event.get("session")
            try:
                self.session_snapshot = self._encode_local_descriptor(session["native_descriptor"]) if session is not None else None
            except (ValueError, KeyError, TypeError):
                self.session_snapshot = None
            return
        if type(event) is dict and event.get("event") in ("native_session_result", "native_session_transaction"):
            event = copy.deepcopy(event)
            # GameBridge calls publish in server receive order. Update the
            # immutable mailbox HERE, never when the helper worker eventually
            # drains old replies: a later member-state event must not be
            # overwritten by an earlier delayed one-member commit response.
            token = event.get("request_id", event.get("transaction_id"))
            if token == f"rpc-{self.session_latest}" and event.get("state") != "error" and event.get("error") is None:
                transaction = event.get("event") == "native_session_transaction"
                committed = transaction and event.get("state") == "committed"
                aborted = transaction and event.get("state") == "aborted"
                updated = not transaction and event.get("op") in ("update", "set_flags")
                left = not transaction and event.get("op") == "leave"
                if aborted or left:
                    self.session_snapshot = None
                elif (committed or updated) and "session" in event:
                    try:
                        self.session_snapshot = self._encode_local_descriptor(event["session"]["native_descriptor"])
                    except (ValueError, KeyError, TypeError):
                        event.update(state="error", error="invalid_native_descriptor")
            try:
                self.session_outbound.put_nowait(event)
            except queue.Full:
                self.stop.set()
            return
        if type(event) is not dict or event.get("event") != "native_search":
            return
        try:
            integer(event.get("id"), 1, 2**31-1)
        except ValueError:
            return
        if event.get("state") not in ("pending", "cancelled", "error"):
            return
        try:
            self.outbound.put_nowait(dict(event))
        except queue.Full:
            self.stop.set()

    def _encode_local_descriptor(self, descriptor):
        """Rewrite addresses on an independent local copy, never shared state.

        Identity bytes remain the exact native source values. Only matching a
        captured native identity pair selects the local game bind address; all
        other members use this process's UDP proxy ingress, never a remote PC's
        process-local bind address.
        """
        from native_session_codec import encode_descriptor
        local = copy.deepcopy(descriptor)
        if getattr(self, "lan_session_mode", False):
            from lan_identity import validate_descriptor
            validate_descriptor(local, max_members=8 if self.multi_session_mode else 2)
        ports = self.transport_ports
        if ports is not None:
            for member in local.get("members", ()):
                if getattr(self, "lan_session_mode", False):
                    own = self._lan_identity()
                    if own is None:
                        raise ValueError("LAN binding unavailable; restart required")
                    identities = member.get("identity_hex", ())
                    own_member = bool(identities) and identities[0] == own.hex()
                else:
                    own_member = member.get("identity_hex") == self.session_identity
                if self.multi_session_mode and not own_member:
                    if not callable(self.remote_proxy):
                        raise ValueError("targeted LAN transport unavailable")
                    remote = bytes.fromhex(member["identity_hex"][0]).decode("ascii")
                    port = self.remote_proxy(remote[6:])
                    if port not in self.multi_proxy_ports:
                        raise ValueError("unadvertised native endpoint")
                else:
                    port = ports[0] if own_member else ports[1]
                member["address_hex"] = f"127.0.0.1:{port}".encode("ascii").hex()
        return encode_descriptor(local, version=4 if self.multi_session_mode else 3)

    def close(self):
        self.stop.set()
        self.listener.close()
        if self.client is not None:
            try:
                self.client.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self.thread.join(2)
        try:
            if self.endpoint.read_text(encoding="utf-8") == self.endpoint_text:
                self.endpoint.unlink()
        except FileNotFoundError:
            pass

    def _run(self):
        # Generation numbers remain monotonic across IPC reconnects too: an
        # old server reply must never complete a new helper request with the
        # same numeric ID.
        latest = 0
        latest_request = None
        while not self.stop.is_set():
            try:
                connection, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            self.client = connection
            active = None
            greeted = False
            lan_mode = False
            multi_mode = False
            buffer = b""
            started = time.monotonic()
            active_since = None
            connection.settimeout(0.5)
            try:
                while not self.stop.is_set():
                    now = time.monotonic()
                    if (not greeted and now - started > 5) or (active_since is not None and now-active_since > 120):
                        LOG.warning("NativeIPC reject reason=timeout")
                        break
                    while True:
                        try:
                            event = self.outbound.get_nowait()
                        except queue.Empty:
                            break
                        if greeted and event["id"] == active:
                            word = {"pending": "PENDING", "cancelled": "CANCELLED", "error": "ERROR"}[event["state"]]
                            connection.sendall(f"{word} {event['id']}\n".encode("ascii"))
                            LOG.info("NativeIPC reply id=%s state=%s", event["id"], event["state"])
                            if event["state"] != "pending":
                                active = None
                                active_since = None
                    if not select.select([connection], [], [], 0.05)[0]:
                        continue
                    chunk = connection.recv(MAX_SESSION_LINE + 1)
                    if not chunk:
                        break
                    buffer += chunk
                    session_prefix = buffer.split(b" ", 1)[0] in (b"CREATE3", b"MATCH3", b"SEARCH3", b"JOIN3", b"UPDATE3", b"UPDATESETTINGS3", b"LEAVE3", b"POLL3", b"FLAGS3")
                    if len(buffer) > (MAX_SESSION_LINE if session_prefix else MAX_LINE):
                        LOG.warning("NativeIPC reject reason=oversized_frame")
                        break
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        if not greeted:
                            if line == f"HELLO5 {self.instance}".encode("ascii"):
                                ports, proxies, own = self.transport_ports, self.multi_proxy_ports, self._lan_identity()
                                valid = (self.multi_capability and callable(self.remote_proxy)
                                    and type(ports) in (tuple,list) and len(ports)==2
                                    and type(proxies) in (tuple,list) and 1<=len(proxies)<=64
                                    and type(ports[0]) is int and 1<=ports[0]<=65535
                                    and all(type(p) is int and 1<=p<=65535 and p!=ports[0] for p in proxies)
                                    and len(set(proxies))==len(proxies) and own is not None
                                    and (not self.session_latest or self.multi_session_mode))
                                if not valid:
                                    connection.sendall(b"UNAVAILABLE5\n")
                                    raise ValueError("targeted LAN binding unavailable")
                                frame = f"READY5 {ports[0]} {len(proxies)} "+" ".join(map(str,proxies))+" "
                                connection.sendall(frame.encode("ascii")+own+b"\n")
                                self.lan_session_mode = lan_mode = True
                                self.multi_session_mode = multi_mode = True
                                greeted = True
                                continue
                            if line == f"HELLO4 {self.instance}".encode("ascii"):
                                ports, own = self.transport_ports, self._lan_identity()
                                valid_ports = (type(ports) in (tuple, list) and len(ports) == 2
                                    and all(type(port) is int and 1 <= port <= 65535 for port in ports)
                                    and ports[0] != ports[1])
                                if not valid_ports or own is None or self.multi_session_mode or (self.session_latest and not self.lan_session_mode):
                                    connection.sendall(b"UNAVAILABLE4\n")
                                    raise ValueError("LAN binding unavailable")
                                connection.sendall(f"READY4 {ports[0]} {ports[1]} ".encode("ascii") + own + b"\n")
                                self.lan_session_mode = lan_mode = True
                                greeted = True
                                continue
                            if line == f"HELLO3 {self.instance}".encode("ascii"):
                                ports = self.transport_ports
                                if ports is None or self.lan_session_mode:
                                    connection.sendall(b"UNAVAILABLE3\n")
                                    raise ValueError("native transport ports unavailable")
                                connection.sendall(f"READY3 {ports[0]} {ports[1]}\n".encode("ascii"))
                                greeted = True
                                continue
                            if line != f"HELLO {self.instance}".encode("ascii"):
                                raise ValueError("wrong native IPC instance")
                            connection.sendall(b"READY\n")
                            greeted = True
                            LOG.info("NativeIPC hello accepted")
                            continue
                        if line.split(b" ", 1)[0] in (b"CREATE3", b"MATCH3", b"SEARCH3", b"JOIN3", b"UPDATE3", b"UPDATESETTINGS3", b"LEAVE3", b"POLL3", b"FLAGS3", b"CANCEL3"):
                            self._session_run(connection, line + b"\n", buffer, lan_mode=lan_mode, multi_mode=multi_mode)
                            raise _SessionFinished()
                        if lan_mode:
                            raise ValueError("LAN binding requires session IPC")
                        request = parse_command(line + b"\n")
                        if request["op"] == "begin":
                            if request["id"] < latest or (request["id"] == latest and
                                    (active is None or request != latest_request)):
                                raise ValueError("replayed native IPC generation")
                            if active is not None and active != request["id"]:
                                raise ValueError("native IPC search already pending")
                            latest, latest_request = request["id"], request
                            active = request["id"]
                            active_since = time.monotonic()
                            LOG.info("NativeIPC begin id=%s numeric=%s compound=%s",
                                     active, len(request["query"]["filters"]), request["query"]["compound_count"])
                        else:
                            LOG.info("NativeIPC cancel id=%s", request["id"])
                        self.commands.put_nowait(request)
            except _SessionFinished:
                pass
            except (KeyError, TypeError, IndexError):
                LOG.warning("NativeIPC reject reason=invalid_session_response")
            except ValueError as exc:
                # These messages come only from bounded local validators, never
                # raw frames or query values. Do not log filters/identities.
                LOG.warning("NativeIPC reject reason=%s", exc)
            except OSError:
                LOG.warning("NativeIPC reject reason=socket_error")
            except queue.Full:
                LOG.warning("NativeIPC reject reason=queue_full")
            finally:
                LOG.info("NativeIPC disconnect pending=%s", active is not None)
                connection.close()
                self.client = None
                if active is not None:
                    try:
                        self.commands.put_nowait({"op": "cancel", "id": active})
                    except queue.Full:
                        # Reserve a separate bounded cleanup path so a flooded
                        # command queue cannot lose cancellation of active work.
                        try:
                            self.cleanup.put_nowait({"op": "cancel", "id": active})
                        except queue.Full:
                            pass
                        self.stop.set()

    def _session_run(self, connection, first, buffered, lan_mode=False, multi_mode=False):
        """Serial finite snapshots plus prepare/commit/abort mutation fencing.

        Create/join are never forwarded as ordinary mutations: a disconnect or
        timeout aborts their transaction even if the prepare reply is delayed.
        Server-side transaction IDs must fence late requests and expire leases.
        """
        current = None
        phase = None
        retry_at = None
        deadline = time.monotonic() + 120
        buffer = first + buffered

        def send_command(command):
            self.commands.put_nowait(command)

        def transaction(generation, op, request=None):
            payload = {"version": 1, "op": op, "transaction_id": f"rpc-{generation}"}
            if request is not None:
                payload["request"] = request
            return {"id": generation, "op": op, "channel": "native_session_transaction", "request": payload}

        def reply(generation, state, descriptor=None):
            frame = f"RESULT3 {generation} {state}\n".encode("ascii")
            if descriptor is not None:
                frame += self._encode_local_descriptor(descriptor)
            connection.sendall(frame)

        try:
            while not self.stop.is_set():
                if time.monotonic() > deadline:
                    raise ValueError("session IPC timeout")
                if (retry_at is not None and time.monotonic() >= retry_at and current is not None
                        and current["op"] == "match" and phase == "preparing"):
                    send_command(transaction(current["id"], "prepare", current["request"]))
                    retry_at = None
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    command = parse_session_command(line + b"\n")
                    if lan_mode:
                        from lan_identity import translate_request
                        own = self._lan_identity()
                        if own is None:
                            raise ValueError("LAN binding unavailable; restart required")
                        command["request"] = translate_request(command["request"], own[6:].decode("ascii"), protocol=5 if multi_mode else 4)
                    generation, op = command["id"], command["op"]
                    if op in ("commit", "abort"):
                        if op == "abort" and (generation != self.session_latest or
                                (current is not None and generation != current["id"])):
                            reply(generation, "ERROR")
                            continue
                        if (op == "abort" and current is None and self.session_committed == generation
                                and self.session_latest == generation):
                            # Native completion can fail after COMMITTED has
                            # reached its worker. Explicit cancellation still
                            # revokes exactly that transaction, including after
                            # an IPC reconnect; ordinary socket close does not.
                            current = {"id": generation, "op": "create"}
                            phase = "prepared"
                        if current is None or generation != current["id"] or phase not in ("prepared", "preparing", "committing", "aborting"):
                            raise ValueError("session IPC transaction not active")
                        if op == "commit" and phase != "prepared":
                            raise ValueError("session IPC commit before prepare")
                        send_command(transaction(generation, op))
                        retry_at = None
                        phase = "committing" if op == "commit" else "aborting"
                    else:
                        if current is not None or generation <= self.session_latest:
                            raise ValueError("session IPC generation busy or replayed")
                        self.session_latest = generation
                        self.session_committed = None
                        if op == "poll":
                            snapshot = self.session_snapshot
                            connection.sendall(f"RESULT3 {generation} {'OK' if snapshot is not None else 'EMPTY'}\n".encode("ascii") + (snapshot or b""))
                            continue
                        current = command
                        retry_at = None
                        payload = command["request"]
                        member = payload.get("native_member", payload.get("native_data", {}).get("member"))
                        if member is not None:
                            self.session_identity = list(member["identity_hex"])
                        deadline = time.monotonic() + 120
                        if op in ("create", "match", "join"):
                            phase = "preparing"
                            send_command(transaction(generation, "prepare", command["request"]))
                        else:
                            phase = "pending"
                            send_command(command)
                while True:
                    try:
                        event = self.session_outbound.get_nowait()
                    except queue.Empty:
                        break
                    if current is None:
                        continue
                    generation = current["id"]
                    if event.get("request_id", event.get("transaction_id")) != f"rpc-{generation}":
                        continue
                    is_transaction = event.get("event") == "native_session_transaction"
                    if (phase in ("preparing", "prepared", "committing", "aborting")) != is_transaction:
                        continue
                    expected_op = {"preparing": "prepare", "prepared": "prepare", "committing": "commit", "aborting": "abort"}.get(phase)
                    if is_transaction and event.get("op") is not None and event["op"] != expected_op:
                        continue
                    state = event.get("state")
                    if (is_transaction and state == "error" and event.get("message") == "native_match_busy"
                            and current["op"] == "match" and phase == "preparing"):
                        # A simultaneous match-create is still provisional.
                        # Retry the identical generation after its lease can
                        # commit; never manufacture a second empty room.
                        retry_at = time.monotonic() + .1
                        continue
                    if event.get("error") is not None or state == "error":
                        reply(generation, "ERROR")
                        # Abort is idempotent and fences a late successful prepare.
                        if is_transaction:
                            send_command(transaction(generation, "abort"))
                        current, phase = None, None
                        continue
                    if is_transaction:
                        if state == "prepared" and phase == "preparing":
                            reply(generation, "PREPARED", event["session"]["native_descriptor"])
                            phase = "prepared"
                        elif state == "committed" and phase == "committing":
                            reply(generation, "COMMITTED")
                            self.session_committed = generation
                            current, phase = None, None
                        elif state == "aborted" and phase == "aborting":
                            self.session_committed = None
                            reply(generation, "CANCELLED")
                            current, phase = None, None
                        continue
                    sessions = event.get("sessions")
                    descriptor = (sessions[0]["native_descriptor"] if sessions else None) if sessions is not None else (
                        event["session"]["native_descriptor"] if "session" in event else None)
                    reply(generation, "EMPTY" if sessions == [] else "OK", descriptor)
                    current, phase = None, None
                if select.select([connection], [], [], 0.05)[0]:
                    chunk = connection.recv(MAX_SESSION_LINE + 1)
                    if not chunk:
                        break
                    buffer += chunk
                    if len(buffer) > MAX_SESSION_LINE:
                        raise ValueError("oversized session IPC frame")
        finally:
            if current is not None and current["op"] in ("create", "match", "join"):
                command = transaction(current["id"], "abort")
                try:
                    self.cleanup.put_nowait(command)
                except queue.Full:
                    self.stop.set()
