"""Server-owned LAN lobbies, matchmaking and UDP transport. Game adapter experimental."""
from __future__ import annotations

import argparse
import asyncio
from collections import OrderedDict, deque
from dataclasses import dataclass, field
import errno
import ipaddress
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import queue
import select
import socket
import struct
import threading
import time
import uuid

from native_sessions import NativeSessionDirectory
from native_session_transactions import NativeSessionTransactions
from native_search import NativeSearchRegistry
from native_identity_diagnostics import NativeIdentityDiagnostics
from lan_identity import validate_peer_request
from backend_services import LanBackendServices
from elo_matchmaking import RankedSessionPolicy,validate_config as validate_elo_config

VERSION = 2
HEADER = struct.Struct("!4sB16s16sH")
MAGIC = b"SZL2"
REGISTER, ACK, DATA, TARGET_DATA = 1, 2, 3, 4
ZERO = bytes(16)
MAX_PAYLOAD = 60000
MAX_LINE = 32768
MAX_CONTROL_LINE = 32768
MAX_REMOTE_ROUTES = 64
MAX_CLIENTS = 256
LOG = logging.getLogger("szero_lan")


def configure_logging(path):
    LOG.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(message)s")
    for handler in (RotatingFileHandler(path, maxBytes=1048576, backupCount=1, encoding="utf-8"),
                    logging.StreamHandler()):
        handler.setFormatter(formatter)
        LOG.addHandler(handler)


def packet(kind, client_id, match_id=ZERO, payload=b""):
    if len(client_id) != 16 or len(match_id) != 16 or len(payload) > MAX_PAYLOAD:
        raise ValueError("invalid datagram size")
    return HEADER.pack(MAGIC, kind, client_id, match_id, len(payload)) + payload


def unpack(data):
    if not HEADER.size <= len(data) <= HEADER.size + MAX_PAYLOAD:
        return None
    magic, kind, client, match, length = HEADER.unpack_from(data)
    if magic != MAGIC or kind not in (REGISTER, ACK, DATA, TARGET_DATA) or length != len(data) - HEADER.size:
        return None
    return kind, client.hex(), match.hex(), data[HEADER.size:]


def load_config(path):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        raise ValueError("config must be a JSON object")
    number = cfg.setdefault("server_port", 27150)
    if type(number) is not int or not 1 <= number <= 65535:
        raise ValueError("server_port must be an integer in 1..65535")
    if "server_host" in cfg and (not isinstance(cfg["server_host"], str)
                                or not 1 <= len(cfg["server_host"].strip()) <= 253):
        raise ValueError("server_host must be an IP address or hostname")
    # Fail clearly on the previous incompatible per-pair configuration.
    if any(key in cfg for key in ("secret", "slot", "room")):
        raise ValueError("old config: use the new example; secret, slot and room have been removed")
    if "elo_matchmaking" in cfg:cfg["elo_matchmaking"]=validate_elo_config(cfg["elo_matchmaking"])
    return cfg


def label(value, fallback=""):
    if value is None:
        value = fallback
    if not isinstance(value, str):
        raise ValueError("name must be text")
    value = value.strip()
    if not 1 <= len(value) <= 48 or any(ord(c) < 32 for c in value):
        raise ValueError("name must contain 1..48 printable characters")
    return value


@dataclass
class Peer:
    id: str
    name: str
    writer: asyncio.StreamWriter
    ip: str
    lobby: str | None = None
    ready: bool = False
    match: str | None = None
    udp: tuple | None = None
    udp_seen: float = 0.0
    udp_diagnostics: set[str] = field(default_factory=set)
    udp_packets: int = 0
    udp_bytes: int = 0
    udp_largest: int = 0
    udp_smallest: int = 0
    udp_session: str | None = None
    account: dict | None = None


@dataclass
class Lobby:
    id: str
    name: str
    members: list[str] = field(default_factory=list)
    match: str | None = None


class GameServer(asyncio.DatagramProtocol):
    """One TCP+UDP endpoint; all membership and pairing state lives here."""

    def __init__(self, host, port, account_store=None, elo_settings=None):
        address = ipaddress.IPv4Address(host)
        if (not address.is_private and not address.is_unspecified) or address.is_multicast:
            raise ValueError("bind_host must be a LAN IPv4 address or 0.0.0.0")
        self.host, self.port = str(address), port
        self.peers = {}
        self.lobbies = {}
        self.matches = {}
        self.waiting = []
        # Independent create/search/join lifecycle for a future native provider.
        # It does not issue match_start or manufacture game-owned session handles.
        self.account_store=account_store
        self.elo_policy=RankedSessionPolicy(self.ranked_profile,
            lambda:callable(getattr(self.account_store,'get_profile',None)),elo_settings)
        self.native_sessions = NativeSessionDirectory(candidate_policy=self.elo_policy)
        self.native_transactions = NativeSessionTransactions(self.native_sessions)
        self.native_search = NativeSearchRegistry()
        self.native_identity_diagnostics = NativeIdentityDiagnostics(MAX_CLIENTS, LOG)
        self.backend_services = LanBackendServices(self.resolve_card, self.resolve_battle, account_store)
        self.account_store = account_store
        self.account_attempts = OrderedDict()
        self.account_workers = asyncio.Semaphore(8)
        self.transport = None
        self.listener = None
        self.tasks = set()

    def ranked_profile(self,owner):
        peer=self.peers.get(owner)
        if peer is None or not peer.account:return None
        return self.account_store.get_profile(peer.account['id'])

    def resolve_card(self, owner, target):
        """Resolve only self or a live co-member; payload IDs confer no rights."""
        peer = self.peers.get(owner)
        if peer is None:
            raise ValueError("card connection closed")
        target_id = owner if target == "self" else target.removeprefix("szlan:")
        if target_id != owner and target_id not in self.native_sessions.member_owners(owner):
            raise ValueError("card target is not a current session participant")
        other = self.peers.get(target_id)
        if other is None:
            raise ValueError("card target disconnected")
        return dict(other.account or {}, display_name=other.name, principal="szlan:"+target_id,
                    native_state=self.backend_services.native_state(target_id))

    def resolve_battle(self, owner):
        """Battle roles come from the live ordered native room, never a body."""
        session = self.native_sessions.sessions.get(self.native_sessions.memberships.get(owner))
        if (session is None or session.version != 2 or session.capacity != 2
                or session.partition[1] not in (4, 5) or len(session.members) != 2
                or owner not in session.members or not session.native_data
                or session.native_data.get("profile") != 2):
            raise ValueError("LAN battle requires a current two-participant native room")
        members = tuple(session.members)
        if any(member not in self.peers or self.peers[member].account is None for member in members):
            raise ValueError("both LAN battle participants must authenticate")
        return {"session_id": session.id, "members": members,
                "membership": tuple(session.members[member] for member in members)}

    async def account_request(self, request, writer):
        """One-shot login/profile exchange on the existing game TCP listener.

        This socket never becomes a game peer. Credentials and session tokens
        are deliberately excluded from log messages and exception responses.
        """
        response = {"event": "account", "state": "error", "message": "Login refused"}
        try:
            if self.account_store is None:
                raise ValueError("Accounts unavailable")
            ip = writer.get_extra_info("peername")[0]
            now = time.monotonic()
            bucket = self.account_attempts.pop(ip, deque())
            while bucket and bucket[0] < now-60:
                bucket.popleft()
            admitted = len(bucket) < 24
            if admitted:
                bucket.append(now)
            self.account_attempts[ip] = bucket
            while len(self.account_attempts) > 2048:
                self.account_attempts.popitem(last=False)
            if not admitted:
                raise ValueError("Too many account requests")
            action = request.get("action")
            fields = {"op", "version", "action"} | ({"username", "password"} if action == "login" else {"token"})
            if set(request) != fields or action not in ("login", "me"):
                raise ValueError("Invalid account request")
            async with self.account_workers:
                if action == "login":
                    username, password = request["username"], request["password"]
                    if not isinstance(username, str) or not isinstance(password, str):
                        raise ValueError("Invalid credentials")
                    result = await asyncio.wait_for(asyncio.to_thread(
                        self.account_store.login, username, password), 8)
                else:
                    token = request["token"]
                    if not isinstance(token, str) or not 2 <= len(token) <= 256:
                        raise ValueError("Invalid account session")
                    profile = await asyncio.wait_for(asyncio.to_thread(self.account_store.authenticate, token), 8)
                    if not profile:
                        raise ValueError("Login expired")
                    result = {"token": token, "profile": profile}
            response = dict(event="account", state="ok", **result)
        except (ValueError, TypeError, asyncio.TimeoutError):
            pass
        except Exception:
            # DB/provider error text can contain connection details. Do not
            # expose it to the client or log the original request object.
            LOG.error("Account service unavailable")
        writer.write((json.dumps(response, separators=(",", ":"))+"\n").encode("utf-8"))
        await asyncio.wait_for(writer.drain(), 2)

    async def start(self):
        loop = asyncio.get_running_loop()
        requested_port = self.port
        for attempt in range(8):
            self.transport, _ = await loop.create_datagram_endpoint(
                lambda: self, local_addr=(self.host, requested_port))
            self.port = self.transport.get_extra_info("sockname")[1]
            try:
                self.listener = await asyncio.start_server(
                    self.connect, self.host, self.port, limit=MAX_LINE)
            except BaseException as exc:
                self.transport.close()
                self.transport = None
                # An OS-selected UDP port can already be occupied by TCP.
                # Retry only ephemeral allocation, never change an explicitly
                # configured tournament/server port behind the user's back.
                if requested_port == 0 and isinstance(exc, OSError) and exc.errno == errno.EADDRINUSE and attempt < 7:
                    continue
                raise
            return self

    async def close(self):
        if self.listener:
            self.listener.close()
            await self.listener.wait_closed()
        if self.transport:
            self.transport.close()
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def send(self, peer, event):
        if peer.writer.is_closing():
            return
        # Disconnect a stalled reader rather than growing an unbounded buffer.
        if peer.writer.transport.get_write_buffer_size() > 262144:
            peer.writer.close()
            return
        peer.writer.write((json.dumps(event, separators=(",", ":")) + "\n").encode())

    def broadcast(self):
        lobbies = [
            {"id": l.id, "name": l.name, "in_match": l.match is not None,
             "players": [{"id": p, "name": self.peers[p].name, "ready": self.peers[p].ready,
                          "playing": self.peers[p].match is not None} for p in l.members]}
            for l in self.lobbies.values()
        ]
        for peer in self.peers.values():
            self.send(peer, {"event": "state", "you": peer.id, "lobby": peer.lobby,
                             "match": peer.match, "queued": peer.id in self.waiting,
                             "connected": len(self.peers), "queued_count": len(self.waiting),
                             "lobbies": lobbies})

    async def connect(self, reader, writer):
        task = asyncio.current_task()
        self.tasks.add(task)
        peer = None
        try:
            if len(self.peers) >= MAX_CLIENTS:
                writer.close()
                return
            hello_line = await asyncio.wait_for(reader.readline(), 5)
            if len(hello_line) > 8192:
                raise ValueError("hello request is too large")
            hello = json.loads(hello_line)
            if not isinstance(hello, dict) or hello.get("version") != VERSION:
                raise ValueError("incompatible client version")
            if hello.get("op") == "account":
                await self.account_request(hello, writer)
                return
            if hello.get("op") != "hello":
                raise ValueError("incompatible client operation")
            if len(self.peers) >= MAX_CLIENTS:
                raise ValueError("server is full")
            token = hello.get("account_token", "")
            if not isinstance(token, str) or len(token) > 256:
                raise ValueError("invalid account session")
            account = None
            if token:
                if self.account_store is None:
                    raise ValueError("accounts are unavailable on this server")
                account = await asyncio.to_thread(self.account_store.authenticate, token)
                if not account:
                    raise ValueError("account session expired; log in again")
                # A concurrent account lookup must not bypass connection limits.
                if len(self.peers) >= MAX_CLIENTS:
                    raise ValueError("server is full")
            name = label(account["display_name"] if account else hello.get("name"), "Player")
            peer = Peer(uuid.uuid4().hex, name, writer,
                        writer.get_extra_info("peername")[0], account=account)
            self.peers[peer.id] = peer
            self.backend_services.bind_account(peer.id, account)
            LOG.info("Connected %s client=%s", peer.name, peer.id)
            self.send(peer, {"event": "welcome", "version": VERSION, "client_id": peer.id,
                             "account": {"authenticated": account is not None,
                                         "display_name": name,
                                         "ranked": account is not None},
                             "capabilities": {"native_sessions": 1,
                                              "native_search": 1,
                                              "native_search_query_profiles": [1, 2],
                                              "native_session_versions": [1, 2],
                                              "native_session_transactions": 1,
                                              "native_lan_identity": 1,
                                              "native_multi_transport": 1,
                                              "lan_backend_services": 1,
                                              "native_materialization_profiles": [1, 2]}})
            self.broadcast()
            while True:
                line = await asyncio.wait_for(reader.readline(), 20)
                if not line:
                    break
                try:
                    message = json.loads(line)
                    if not isinstance(message, dict):
                        raise ValueError("request must be an object")
                    self.request(peer, message)
                except (ValueError, KeyError, TypeError) as exc:
                    self.send(peer, {"event": "error", "message": str(exc)})
                await asyncio.wait_for(writer.drain(), 2)
        except (ValueError, ConnectionError, asyncio.TimeoutError):
            pass
        finally:
            if peer:
                LOG.info("Disconnected %s client=%s", peer.name, peer.id)
                self.trace_udp_summary(peer)
                self.native_search.disconnect(peer.id)
                self.native_transactions.disconnect(peer.id)
                self.native_identity_diagnostics.disconnect(peer.id)
                self.elo_policy.cancel(peer.id)
                self.backend_services.disconnect(peer.id)
                affected = self.native_sessions.disconnect(peer.id)
                self.elo_policy.forget(peer.id)
                self.notify_native_sessions(affected)
                self.notify_native_transport(affected)
                self.leave(peer)
                self.peers.pop(peer.id, None)
                self.broadcast()
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionError, OSError):
                pass
            self.tasks.discard(task)

    def leave(self, peer):
        if peer.match:
            self.end_match(peer.match, "A player left the match")
        if peer.id in self.waiting:
            self.waiting.remove(peer.id)
        lobby = self.lobbies.get(peer.lobby)
        if lobby and peer.id in lobby.members:
            lobby.members.remove(peer.id)
            if not lobby.members:
                self.lobbies.pop(lobby.id, None)
        peer.lobby, peer.ready, peer.match = None, False, None

    def notify_native_sessions(self, owner_ids):
        for owner_id in owner_ids:
            target = self.peers.get(owner_id)
            if target:
                self.send(target, {"event": "native_session_state", "version": 1,
                                   "session": self.native_sessions.describe_membership(owner_id)})

    def notify_native_transport(self, owner_ids):
        self.backend_services.prune_battles()
        for owner_id in owner_ids:
            target = self.peers.get(owner_id)
            if target is None:
                continue
            session = self.native_sessions.describe_membership(owner_id)
            if session and session.get("native_descriptor", {}).get("profile") == 2:
                own_member = self.native_sessions.sessions[session["session_id"]].members[owner_id]
                order = next(member["join_order"] for member in session["members"]
                             if member["member_id"] == own_member)
                self.send(target, {"event": "native_transport", "version": 1, "active": True,
                                   "session_id": session["session_id"], "join_order": order,
                                   "multi": session["partition"]["protocol"] == 5,
                                   "peers": list(self.native_sessions.member_owners(owner_id))})
            else:
                self.trace_udp_summary(target)
                self.send(target, {"event": "native_transport", "version": 1, "active": False})

    def native_request(self, peer, msg):
        """Only TCP connection identity may own sessions, never a payload ID.

        This protocol is a server-side prerequisite, not a native ABI hook.
        Existing Quickmatch selections are not read, changed or reconstructed.
        """
        request = msg.get("request")
        before = self.native_sessions.member_owners(peer.id)
        previous = self.native_sessions.describe_membership(peer.id)
        previous_native = bool(previous and previous.get("native_descriptor", {}).get("profile") == 2)
        try:
            if set(msg) != {"op", "request"}:
                raise ValueError("unexpected session envelope fields")
            if peer.lobby or peer.match or peer.id in self.waiting:
                raise ValueError("leave sidecar matchmaking before native session operations")
            if (peer.id in self.native_search.pending
                    and (type(request) is not dict or request.get("op") != "search")):
                raise ValueError("cancel native search before session mutation")
            validate_peer_request(self.native_sessions, peer.id, request)
            response = self.native_transactions.direct(peer.id, request)
        except ValueError as exc:
            # Do not echo an unbounded or arbitrary object as a correlation ID.
            request_id = request.get("request_id") if type(request) is dict else None
            if (not isinstance(request_id, str) or not 1 <= len(request_id) <= 64
                    or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
                           for c in request_id)):
                request_id = None
            requested_version = request.get("version") if type(request) is dict else None
            error_version = requested_version if type(requested_version) is int and requested_version in (1, 2) else 1
            self.send(peer, {"event": "native_session_error", "version": error_version,
                             "request_id": request_id, "message": str(exc)})
            return
        self.native_identity_diagnostics.remember(peer.id, request, live_clients=self.peers,
            validated=True, request_id=request.get("request_id"))
        if request["op"] == "search":
            self.native_identity_diagnostics.returned(peer.id, request.get("request_id"), response.get("sessions"))
        self.send(peer, response)
        after = self.native_sessions.member_owners(peer.id)
        if previous and not after:
            self.trace_udp_summary(peer)
        if request["op"] != "search":
            self.notify_native_sessions((set(before) | set(after)) - {peer.id})
            if request.get("version") == 2 or previous_native:
                self.notify_native_transport(set(before) | set(after) | {peer.id})
        session = response.get("session") or previous or {}
        LOG.info("Native session operation %s client=%s request=%s action=%s session=%s members=%s flags=%s results=%s",
                 request["op"], peer.id, request["request_id"], response.get("action", request["op"]),
                 session.get("session_id"), len(session.get("members", ())), session.get("create_flags"),
                 len(response["sessions"]) if "sessions" in response else None)

    def native_transaction_request(self, peer, msg):
        request = msg.get("request")
        before = set(self.native_sessions.member_owners(peer.id))
        previous_record = self.native_transactions.records.get(peer.id)
        previous_session = (self.native_sessions._describe(previous_record.session)
                            if previous_record and previous_record.session is not None else {})
        try:
            if set(msg) != {"op", "request"}:
                raise ValueError("unexpected native transaction envelope")
            if peer.lobby or peer.match or peer.id in self.waiting or peer.id in self.native_search.pending:
                raise ValueError("leave other matchmaking before native transaction")
            if type(request) is dict and request.get("op") == "prepare":
                validate_peer_request(self.native_sessions, peer.id, request.get("request"))
            response = self.native_transactions.handle(peer.id, request)
            if request.get("op")=="abort" and response.get("state")=="aborted":self.elo_policy.cancel(peer.id)
        except ValueError as exc:
            token = request.get("transaction_id") if type(request) is dict else None
            if not isinstance(token, str) or len(token) > 32 or not token.startswith("rpc-") or not token[4:].isascii() or not token[4:].isdigit():
                token = None
            operation = request.get("op") if type(request) is dict else None
            response = {"event": "native_session_transaction", "version": 1,
                        "transaction_id": token, "op": operation if operation in ("prepare", "commit", "abort") else None,
                        "state": "error", "message": str(exc)}
        if response["state"] == "prepared":
            self.native_identity_diagnostics.remember(peer.id, request.get("request"), live_clients=self.peers,
                validated=True, wire_op="native_session_transaction",
                request_id=response.get("transaction_id"), result="prepared")
        self.send(peer, response)
        after = set(self.native_sessions.member_owners(peer.id))
        if response["state"] in ("committed", "aborted"):
            self.notify_native_sessions((before | after) - {peer.id})
            self.notify_native_transport(before | after | {peer.id})
        record = self.native_transactions.records.get(peer.id)
        session = response.get("session") or self.native_sessions.describe_membership(peer.id) or previous_session
        same_generation = record and response.get("transaction_id") == f"rpc-{record.generation}"
        # Record action is server-owned and bounded; do not log request/identity/stream payloads.
        LOG.info("Native transaction op=%s state=%s client=%s transaction=%s action=%s session=%s members=%s flags=%s",
                 response["op"], response["state"], peer.id, response.get("transaction_id"),
                 response.get("action", record.action if same_generation else None), session.get("session_id"),
                 len(session.get("members", ())), session.get("create_flags"))

    def native_search_request(self, peer, msg):
        request = msg.get("request")
        request_id = request.get("id") if type(request) is dict else None
        if type(request_id) is not int or not 1 <= request_id <= 2**31 - 1:
            request_id = None
        try:
            if set(msg) != {"op", "request"}:
                raise ValueError("unexpected native search envelope fields")
            if type(request) is dict and request.get("op") == "begin":
                if (peer.lobby or peer.match or peer.id in self.waiting or self.native_sessions.has_membership(peer.id)
                        or self.native_transactions.has_pending(peer.id)):
                    raise ValueError("leave other matchmaking before native search")
            response = self.native_search.handle(peer.id, request)
        except ValueError as exc:
            response = {"event": "native_search", "id": request_id,
                        "state": "error", "error": str(exc)}
        self.send(peer, response)
        operation = request.get("op") if type(request) is dict else None
        if operation not in ("begin", "cancel"):
            operation = "invalid"
        LOG.info("Native search %s id=%s state=%s client=%s error=%s",
                 operation, request_id, response["state"], peer.id,
                 response.get("error", "none"))

    def request(self, peer, msg):
        op = msg.get("op")
        if op == "native_session_transaction":
            self.native_transaction_request(peer, msg)
            return
        if op == "ping":
            self.send(peer, {"event": "pong"})
            return
        if op == "list":
            self.broadcast()
            return
        if op == "native_session":
            self.native_request(peer, msg)
            return
        if op == "native_search":
            self.native_search_request(peer, msg)
            return
        if op == "lan_backend_service":
            request = msg.get("request")
            request_id = request.get("request_id") if type(request) is dict else None
            if (type(request_id) is not str or not request_id.startswith("service-")
                    or not request_id[8:].isascii() or not request_id[8:].isdigit()
                    or len(request_id) > 32):
                raise ValueError("invalid LAN service request")
            try:
                body = self.backend_services.request(peer.id, peer.name, request.get("path"), request.get("body"))
                if request.get('path') in ('/pvp/start_battle_player1.php','/pvp/start_battle_player2.php'):
                    self.elo_policy.match.clear(self.native_sessions.member_owners(peer.id))
                if request.get('path') in ('/pvp/end_battle_player1.php','/pvp/end_battle_player2.php'):
                    self.elo_policy.invalidate_ratings()
                event = dict(event="lan_backend_service", request_id=request_id, state="ok", body=body)
                LOG.info("LAN service client=%s route=%s state=ok", peer.id, request.get("path"))
            except ValueError:
                # Never log request bodies (especially platform credentials).
                event = dict(event="lan_backend_service", request_id=request_id, state="error")
                LOG.info("LAN service client=%s state=refused", peer.id)
            except Exception as exc:
                # Storage failures refuse this operation without disconnecting
                # the TCP owner or exposing SQL/credentials/request contents.
                event = dict(event="lan_backend_service", request_id=request_id, state="error")
                LOG.error("LAN service client=%s state=failed error_type=%s", peer.id, type(exc).__name__)
            self.send(peer, event)
            return
        if peer.id in self.native_search.pending:
            raise ValueError("cancel native search before sidecar matchmaking")
        if self.native_sessions.has_membership(peer.id) or self.native_transactions.has_pending(peer.id):
            raise ValueError("leave the native session before sidecar matchmaking")
        if op == "create":
            name = label(msg.get("name"), peer.name + "'s lobby")
            self.leave(peer)
            lobby = Lobby(uuid.uuid4().hex[:12], name, [peer.id])
            self.lobbies[lobby.id] = lobby
            peer.lobby = lobby.id
        elif op == "join":
            lobby_id = msg.get("lobby_id")
            if not isinstance(lobby_id, str) or lobby_id not in self.lobbies:
                raise ValueError("lobby no longer exists")
            if peer.lobby == lobby_id:
                return
            lobby = self.lobbies[lobby_id]
            if len(lobby.members) >= 32:
                raise ValueError("lobby is full")
            self.leave(peer)
            lobby.members.append(peer.id)
            peer.lobby = lobby.id
        elif op == "leave":
            self.leave(peer)
        elif op == "ready":
            if peer.match or not peer.lobby:
                raise ValueError("join a lobby and finish the current match first")
            value = msg.get("value")
            if type(value) is not bool:
                raise ValueError("ready value must be true or false")
            peer.ready = value
            self.try_start(self.lobbies[peer.lobby])
        elif op == "queue":
            self.leave(peer)
            self.waiting.append(peer.id)
            while len(self.waiting) >= 2:
                ids = [self.waiting.pop(0), self.waiting.pop(0)]
                lobby = Lobby(uuid.uuid4().hex[:12], "Quick match", ids)
                self.lobbies[lobby.id] = lobby
                for client_id in ids:
                    self.peers[client_id].lobby = lobby.id
                    self.peers[client_id].ready = True
                self.try_start(lobby)
        elif op == "finish":
            if not peer.match:
                raise ValueError("no current match")
            lobby = self.lobbies[self.matches[peer.match]["lobby"]]
            self.end_match(peer.match, "Returned to lobby")
            # Give waiting players priority for the next fight.
            self.try_start(lobby)
        else:
            raise ValueError("unknown operation")
        LOG.info("%s: %s", peer.name, op)
        self.broadcast()

    def try_start(self, lobby):
        if lobby.match:
            return
        now = time.monotonic()
        eligible = [self.peers[p] for p in lobby.members
                    if self.peers[p].ready and self.peers[p].udp
                    and now - self.peers[p].udp_seen < 5]
        if len(eligible) < 2:
            return
        players = eligible[:2]
        match_id = uuid.uuid4().hex
        lobby.match = match_id
        self.matches[match_id] = {"players": [p.id for p in players], "lobby": lobby.id}
        LOG.info("Match %s lobby=%s players=%s vs %s", match_id, lobby.name,
                 players[0].name, players[1].name)
        for order, player in enumerate(players):
            player.match, player.ready = match_id, False
            self.send(player, {"event": "match_start", "match_id": match_id,
                               "join_order": order, "opponent": players[1 - order].name})

    def end_match(self, match_id, reason):
        match = self.matches.pop(match_id, None)
        if not match:
            return
        LOG.info("Match ended %s: %s", match_id, reason)
        lobby = self.lobbies.get(match["lobby"])
        if lobby:
            lobby.match = None
        for client_id in match["players"]:
            peer = self.peers.get(client_id)
            if peer:
                peer.match, peer.ready = None, False
                self.send(peer, {"event": "match_end", "reason": reason})

    def trace_udp_once(self, peer, result, match_id=None, size=0):
        # Four fixed categories per live peer, never packet contents/addresses.
        if result not in ("registered", "no_route", "peer_unavailable", "forwarded"):
            return
        if result == "forwarded":
            if peer.udp_session != match_id:
                peer.udp_packets = peer.udp_bytes = peer.udp_largest = 0
                peer.udp_smallest = size
                peer.udp_session = match_id
            peer.udp_packets += 1
            peer.udp_bytes += size
            peer.udp_largest = max(peer.udp_largest, size)
            peer.udp_smallest = min(peer.udp_smallest, size)
        if result in peer.udp_diagnostics:
            return
        peer.udp_diagnostics.add(result)
        LOG.info("LAN UDP client=%s session=%s result=%s bytes=%s",
                 peer.id, match_id, result, size)

    def trace_udp_summary(self, peer):
        if peer.udp_packets:
            LOG.info("LAN UDP summary client=%s session=%s forwarded_packets=%d forwarded_bytes=%d smallest=%d largest=%d",
                     peer.id, peer.udp_session, peer.udp_packets, peer.udp_bytes,
                     peer.udp_smallest, peer.udp_largest)
        peer.udp_packets = peer.udp_bytes = peer.udp_largest = peer.udp_smallest = 0
        peer.udp_session = None

    def datagram_received(self, data, address):
        decoded = unpack(data)
        if not decoded:
            return
        kind, client_id, match_id, payload = decoded
        peer = self.peers.get(client_id)
        if not peer or address[0] != peer.ip:
            return
        if kind == REGISTER and not payload and match_id == ZERO.hex():
            peer.udp, peer.udp_seen = address, time.monotonic()
            self.trace_udp_once(peer, "registered")
            self.transport.sendto(packet(ACK, bytes.fromhex(client_id)), address)
            lobby = self.lobbies.get(peer.lobby)
            if lobby and not lobby.match:
                self.try_start(lobby)
                if lobby.match:
                    self.broadcast()
        elif kind == TARGET_DATA and address == peer.udp:
            if len(payload) < 16:
                return
            destination, body = payload[:16].hex(), payload[16:]
            session = self.native_sessions.sessions.get(self.native_sessions.memberships.get(peer.id))
            if (session is None or session.id != match_id or session.partition[1] != 5
                    or destination == peer.id or destination not in session.members
                    or peer.id not in session.members):
                self.trace_udp_once(peer, "no_route", match_id, len(body))
                return
            other = self.peers.get(destination)
            if other and other.udp and time.monotonic()-other.udp_seen < 5:
                self.transport.sendto(packet(TARGET_DATA, bytes.fromhex(other.id),
                    bytes.fromhex(match_id), bytes.fromhex(peer.id)+body), other.udp)
                self.trace_udp_once(peer, "forwarded", match_id, len(body))
            else:
                self.trace_udp_once(peer, "peer_unavailable", match_id, len(body))
        elif kind == DATA and address == peer.udp:
            if match_id == peer.match:
                match = self.matches.get(match_id)
                if not match:
                    return
                other_id = next(p for p in match["players"] if p != peer.id)
            else:
                native = self.native_sessions.sessions.get(self.native_sessions.memberships.get(peer.id))
                if native and native.partition[1] == 5:
                    self.trace_udp_once(peer, "no_route", match_id, len(payload))
                    return
                other_id = self.native_sessions.relay_peer(peer.id, match_id)
                if other_id is None:
                    self.trace_udp_once(peer, "no_route", match_id, len(payload))
                    return
            other = self.peers.get(other_id)
            if other and other.udp and time.monotonic() - other.udp_seen < 5:
                self.transport.sendto(
                    packet(DATA, bytes.fromhex(other.id), bytes.fromhex(match_id), payload),
                    other.udp)
                self.trace_udp_once(peer, "forwarded", match_id, len(payload))
            else:
                self.trace_udp_once(peer, "peer_unavailable", match_id, len(payload))


def write_runtime(path, assignment):
    """Publish a tiny Lua data file atomically; no user-selected player role."""
    if not path:
        return
    path = Path(path)
    if not path.parent.is_dir():
        raise ValueError("adapter scripts folder does not exist")
    revision = uuid.uuid4().hex
    if assignment:
        match_id = assignment["match_id"]
        if not isinstance(match_id, str) or len(match_id) != 32 or any(c not in "0123456789abcdef" for c in match_id):
            raise ValueError("invalid match ID")
        content = ('return {active=true, revision="%s", join_order=%d, '
                   'game_port=%d, proxy_port=%d, match_id="%s"}\n') % (
                       revision, assignment["join_order"],
                       assignment["game_port"], assignment["proxy_port"], match_id)
    else:
        content = 'return {active=false, revision="%s"}\n' % revision
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as out:
            out.write(content)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return revision


class LobbyClient:
    """Identical clients connect to one server; roles arrive only in match_start."""

    def __init__(self, host, port=27150, name="Player", runtime_path=None, game_port=None, proxy_port=None,
                 account_token=""):
        for value in (game_port, proxy_port):
            if value is not None and (type(value) is not int or not 1 <= value <= 65535):
                raise ValueError("local UDP port must be an integer in 1..65535")
        self.name = label(name)
        self.events = queue.Queue(maxsize=128)
        self.stop = threading.Event()
        self.connected = threading.Event()
        self.udp_ready = threading.Event()
        self.send_lock = threading.Lock()
        self.state_lock = threading.Lock()
        self.client_id = None
        self.assignment = None
        self.state = None
        self.runtime_path = runtime_path
        self.runtime_revision = None
        self.adapter_status = None
        self.game_packets_sent = self.game_packets_received = 0
        self.tcp = self.udp = self.local = None
        self.multi_sockets = []
        self.multi_routes = {}
        self.threads = []
        try:
            self.tcp = socket.create_connection((host, port), timeout=5)
            self.tcp.settimeout(None)
            remote = self.tcp.getpeername()
            self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp.connect(remote)
            self.udp.settimeout(0.2)
            self.local = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.local.bind(("127.0.0.1", proxy_port if proxy_port is not None else 0))
            self.local.settimeout(0.2)
            if game_port is None:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserve:
                    reserve.bind(("127.0.0.1", 0))
                    game_port = reserve.getsockname()[1]
            self.game_port = game_port
            self.proxy_port = self.local.getsockname()[1]
            # Fixed lifetime pool: a native channel may retain an old endpoint,
            # so departed identities never receive another identity's socket.
            for _ in range(MAX_REMOTE_ROUTES):
                proxy = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    proxy.bind(("127.0.0.1", 0))
                    if proxy.getsockname()[1] == game_port:
                        proxy.close()
                        proxy = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        proxy.bind(("127.0.0.1", 0))
                        if proxy.getsockname()[1] == game_port:
                            raise OSError("Could not reserve distinct native UDP endpoints")
                    proxy.setblocking(False)
                except BaseException:
                    proxy.close()
                    raise
                self.multi_sockets.append(proxy)
            self.multi_proxy_ports = tuple(proxy.getsockname()[1] for proxy in self.multi_sockets)
            self.runtime_revision = write_runtime(self.runtime_path, None)
            if not isinstance(account_token, str) or len(account_token) > 256:
                raise ValueError("invalid account session")
            fields = dict(version=VERSION, name=self.name)
            if account_token:
                fields["account_token"] = account_token
            self.send("hello", **fields)
            for target in (self.control_loop, self.network_loop, self.local_loop):
                thread = threading.Thread(target=target, daemon=True)
                thread.start()
                self.threads.append(thread)
        except BaseException:
            self.close()
            raise

    def emit(self, event):
        try:
            self.events.put_nowait(event)
        except queue.Full:
            # A client UI that stopped consuming must not grow memory indefinitely.
            self.stop.set()

    def remote_proxy(self, peer_id):
        if (not isinstance(peer_id, str) or len(peer_id)!=32
                or any(c not in "0123456789abcdef" for c in peer_id)
                or peer_id == (self.client_id or b"").hex()):
            raise ValueError("invalid targeted LAN peer")
        with self.state_lock:
            if peer_id not in self.multi_routes:
                if len(self.multi_routes) == len(self.multi_sockets):
                    raise ValueError("LAN endpoint lifetime capacity reached; restart game")
                self.multi_routes[peer_id] = self.multi_sockets[len(self.multi_routes)]
            return self.multi_routes[peer_id].getsockname()[1]

    def send(self, op, **fields):
        line = (json.dumps(dict(op=op, **fields), separators=(",", ":")) + "\n").encode()
        if len(line) > MAX_LINE:
            raise ValueError("request is too large")
        with self.send_lock:
            self.tcp.sendall(line)

    def control_loop(self):
        try:
            with self.tcp.makefile("rb") as stream:
                while not self.stop.is_set():
                    line = stream.readline(MAX_CONTROL_LINE + 1)
                    if not line or len(line) > MAX_CONTROL_LINE:
                        break
                    msg = json.loads(line)
                    event = msg.get("event")
                    if event == "welcome":
                        self.client_id = bytes.fromhex(msg["client_id"])
                        self.connected.set()
                    elif event == "match_start":
                        assignment = dict(msg, game_port=self.game_port, proxy_port=self.proxy_port)
                        with self.state_lock:
                            self.runtime_revision = write_runtime(self.runtime_path, assignment)
                            self.assignment = assignment
                            self.adapter_status = None
                            self.game_packets_sent = self.game_packets_received = 0
                    elif event == "match_end":
                        with self.state_lock:
                            self.assignment = None
                            self.runtime_revision = write_runtime(self.runtime_path, None)
                            self.adapter_status = None
                    elif event == "native_transport":
                        if msg.get("version") != 1 or type(msg.get("active")) is not bool:
                            raise ValueError("invalid native transport response")
                        with self.state_lock:
                            if msg["active"]:
                                session = msg.get("session_id")
                                order = msg.get("join_order")
                                if (not isinstance(session, str) or len(session) != 32 or
                                        any(c not in "0123456789abcdef" for c in session) or
                                        type(order) is not int or not 0 <= order < 8):
                                    raise ValueError("invalid native transport assignment")
                                multi = msg.get("multi", False)
                                peers = msg.get("peers", [])
                                if (type(multi) is not bool or multi and (type(peers) is not list
                                        or not 1 <= len(peers) <= 8
                                        or any(not isinstance(p,str) or len(p)!=32 or any(c not in "0123456789abcdef" for c in p) for p in peers)
                                        or len(set(peers)) != len(peers)
                                        or (self.client_id or b"").hex() not in peers)):
                                    raise ValueError("invalid targeted transport membership")
                                if not self.assignment or self.assignment.get("match_id") != session:
                                    self.game_packets_sent = self.game_packets_received = 0
                                self.assignment = {"native": True, "match_id": session,
                                                   "join_order": order, "game_port": self.game_port,
                                                   "proxy_port": self.proxy_port, "multi": multi,
                                                   "peers": tuple(peers)}
                            elif self.assignment and self.assignment.get("native"):
                                self.assignment = None
                    elif event == "state":
                        self.state = msg
                    if event != "pong":
                        if event in ("welcome", "match_start", "match_end", "error"):
                            LOG.info("Server event: %s", json.dumps(msg))
                        self.emit(msg)
        except (OSError, ValueError) as exc:
            if not self.stop.is_set():
                self.emit({"event": "error", "message": str(exc)})
        finally:
            LOG.info("Lobby server connection closed")
            self.connected.clear()
            self.stop.set()
            with self.state_lock:
                self.assignment = None
            try:
                write_runtime(self.runtime_path, None)
            except (OSError, ValueError):
                pass
            self.emit({"event": "disconnected"})

    def network_loop(self):
        next_register = next_ping = next_status = 0.0
        last_ack = time.monotonic()
        while not self.stop.is_set():
            try:
                now = time.monotonic()
                if now >= next_status:
                    self.read_adapter_status()
                    next_status = now + 1
                if self.client_id and now >= next_register:
                    self.udp.send(packet(REGISTER, self.client_id))
                    next_register = now + 1
                if self.connected.is_set() and now >= next_ping:
                    self.send("ping")
                    next_ping = now + 5
                if now - last_ack > 5:
                    self.udp_ready.clear()
                try:
                    data = self.udp.recv(65535)
                except socket.timeout:
                    continue
                decoded = unpack(data)
                if not decoded or decoded[1] != (self.client_id or b"").hex():
                    continue
                kind, _, match_id, payload = decoded
                if kind == ACK and not payload and match_id == ZERO.hex():
                    self.udp_ready.set()
                    last_ack = time.monotonic()
                elif kind == DATA:
                    with self.state_lock:
                        active = self.assignment
                    if active and active["match_id"] == match_id:
                        self.local.sendto(payload, ("127.0.0.1", self.game_port))
                        with self.state_lock:
                            self.game_packets_received += 1
                            if self.game_packets_received == 1:
                                LOG.info("First relayed game UDP packet received: match=%s bytes=%d", match_id, len(payload))
                elif kind == TARGET_DATA and len(payload) >= 16:
                    source, body = payload[:16].hex(), payload[16:]
                    with self.state_lock:
                        active = self.assignment
                    if (active and active.get("multi") and active["match_id"] == match_id
                            and source in active.get("peers", ())
                            and source != (self.client_id or b"").hex()):
                        self.remote_proxy(source)
                        with self.state_lock:
                            proxy = self.multi_routes[source]
                        proxy.sendto(body, ("127.0.0.1", self.game_port))
                        with self.state_lock:
                            self.game_packets_received += 1
                            if self.game_packets_received == 1:
                                LOG.info("First relayed game UDP packet received: match=%s bytes=%d", match_id, len(body))
            except (OSError, ValueError) as exc:
                if not self.stop.is_set():
                    self.emit({"event": "error", "message": str(exc)})
                self.stop.set()

    def local_loop(self):
        while not self.stop.is_set():
            try:
                ready, _, _ = select.select([self.local, *self.multi_sockets], [], [], .2)
                with self.state_lock:
                    active = self.assignment
                    reverse = {sock: peer for peer, sock in self.multi_routes.items()}
                for source in ready:
                    payload, address = source.recvfrom(65535)
                    if not active or address != ("127.0.0.1", self.game_port):
                        continue
                    if source is self.local and not active.get("multi") and len(payload) <= MAX_PAYLOAD:
                        kind, body = DATA, payload
                    elif (active.get("multi") and source in reverse
                            and reverse[source] in active.get("peers", ())
                            and len(payload) <= MAX_PAYLOAD-16):
                        kind, body = TARGET_DATA, bytes.fromhex(reverse[source])+payload
                    else:
                        continue
                    self.udp.send(packet(kind, self.client_id, bytes.fromhex(active["match_id"]), body))
                    with self.state_lock:
                        self.game_packets_sent += 1
                        if self.game_packets_sent == 1:
                            LOG.info("First local game UDP packet sent: match=%s bytes=%d", active["match_id"], len(payload))
            except socket.timeout:
                pass
            except OSError:
                if not self.stop.is_set():
                    self.stop.set()

    def read_adapter_status(self):
        """Read bounded local diagnostics, never treat issued commands as a battle."""
        if not self.runtime_path:
            return
        try:
            path = Path(self.runtime_path).with_suffix(".status.json")
            with path.open("r", encoding="utf-8") as report:
                raw = report.read(8193)
            if len(raw) > 8192:
                return
            status = json.loads(raw)
            if not isinstance(status, dict) or status.get("version") != 1:
                return
            if any(not isinstance(status.get(key), str) or len(status[key]) > 2048
                   for key in ("revision", "match_id", "stage", "detail", "world")):
                return
            with self.state_lock:
                expected_match = self.assignment["match_id"] if self.assignment else ""
                if status["revision"] != self.runtime_revision or status["match_id"] != expected_match:
                    return  # Ignore stale reports from previous matches/processes.
                if status == self.adapter_status:
                    return
                self.adapter_status = status
            LOG.info("Game adapter: %s", json.dumps(status))
            self.emit(dict(status, event="adapter_status"))
        except (OSError, ValueError):
            pass  # A concurrent Lua write may be incomplete; retry next poll.

    def close(self):
        self.stop.set()
        if self.tcp:
            try:
                self.tcp.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        for thread in self.threads:
            if thread is not threading.current_thread():
                thread.join(1)
        for sock in (self.tcp, self.udp, self.local, *self.multi_sockets):
            if sock:
                sock.close()
        self.connected.clear()
        self.udp_ready.clear()
        if self.runtime_path:
            try:
                write_runtime(self.runtime_path, None)
            except (OSError, ValueError):
                pass


async def serve(cfg):
    account_store = None
    if os.environ.get("ARENA_DB_HOST") or os.environ.get("ARENA_SQLITE_PATH"):
        from account_store import AccountStore
        account_store = AccountStore.from_env()
    server = await GameServer(cfg["bind_host"], cfg["server_port"], account_store,cfg.get("elo_matchmaking")).start()
    print(f"LAN lobby server: {server.host}:{server.port} (TCP + UDP)", flush=True)
    print("Quick play is available; registered accounts enable ranked play.", flush=True)
    if server.host == "0.0.0.0":
        print("Listening on all IPv4 interfaces. Clients use this PC's actual IP.", flush=True)
    try:
        async with server.listener:
            await server.listener.serve_forever()
    finally:
        await server.close()
        if account_store is not None:
            account_store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("server",))
    parser.add_argument("--config", default=str(Path(__file__).with_name("server.example.json")))
    parser.add_argument("--log", default=str(Path(__file__).with_name("server.log")))
    args = parser.parse_args()
    try:
        configure_logging(args.log)
        asyncio.run(serve(load_config(args.config)))
    except KeyboardInterrupt:
        pass
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
