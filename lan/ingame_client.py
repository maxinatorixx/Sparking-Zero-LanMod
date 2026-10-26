"""Background LAN bridge: the game panel owns lobby commands, not a desktop UI."""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import queue
import re
import threading
import time

from installer import atomic_write
from lifecycle import install_stop_signals, parent_stream, restore_signals, watch_parent_stream
from native_search import NativeSearchRPC
from backend_rpc import BackendServiceRPC
from szero_lan import LobbyClient, configure_logging, label, load_config

LOG = logging.getLogger("szero_lan")


def lua_value(value):
    """Encode data only, including untrusted player/lobby names, as Lua literals."""
    if value is None:
        return "nil"
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is int:
        return str(value)
    if isinstance(value, str):
        return '"' + "".join("\\%03d" % byte for byte in value.encode("utf-8")) + '"'
    if isinstance(value, list):
        return "{" + ",".join(lua_value(item) for item in value) + "}"
    if isinstance(value, dict):
        return "{" + ",".join("[" + lua_value(key) + "]=" + lua_value(item)
                              for key, item in value.items()) + "}"
    raise ValueError("unsupported UI data type")


class GameBridge:
    def __init__(self, game_root, runtime):
        self.game_root, self.runtime = Path(game_root), Path(runtime)
        self.ui_path = self.runtime.with_suffix(".ui.lua")
        self.command_path = self.runtime.with_suffix(".command.json")
        self.stop_path = self.runtime.with_suffix(".stop")
        self.client = None
        self.message = "Connecting to LAN server"
        self.last_command = 0
        self.last_view = None
        # Per-launch paths must be new. Never consume an old pending command.
        self.command_path.unlink(missing_ok=True)
        self.cfg = load_config(self.game_root / "SzeroLAN.json")
        if self.cfg.get("server_host") == "0.0.0.0":
            raise ValueError("SzeroLAN.json needs the server PC's actual IP, not 0.0.0.0")
        self.name = label(self.cfg.get("name"), "Player")
        enabled = self.cfg.get("native_search", False)
        if type(enabled) is not bool:
            raise ValueError("native_search must be true or false")
        session_enabled = self.cfg.get("native_session", False)
        if type(session_enabled) is not bool or (session_enabled and not enabled):
            raise ValueError("native_session must be boolean and requires native_search")
        self.native_rpc = None
        self.backend_rpc = None
        self.native_game_port = None
        self.native_proxy_port = None
        self.native_capability = False
        self.native_session_capability = False
        self.native_session_pending = {}
        self.native_pending = set()
        if enabled:
            match = re.fullmatch(r"lan_runtime_([0-9a-f]{32})", self.runtime.stem)
            if match is None:
                raise ValueError("native search needs an instance-scoped runtime filename")
            self.native_rpc = NativeSearchRPC(self.runtime, match.group(1))

    def publish(self):
        client = self.client
        state = client.state if client and client.state else {}
        lobbies = [{"id": lobby["id"], "name": lobby["name"],
                    "players": len(lobby["players"]), "in_match": lobby["in_match"]}
                   for lobby in state.get("lobbies", [])]
        me = next((p for lobby in state.get("lobbies", []) for p in lobby["players"]
                   if p["id"] == state.get("you")), {})
        report = client.adapter_status if client else None
        view = dict(version=1, name=self.name, message=self.message,
                    connected=bool(client and client.connected.is_set()),
                    udp_ready=bool(client and client.udp_ready.is_set()),
                    queued=state.get("queued", False), ready=me.get("ready", False),
                    in_match=bool(state.get("match")), lobbies=lobbies,
                    adapter_stage=report["stage"] if report else "waiting_for_adapter",
                    adapter_detail=report["detail"] if report else "No adapter report yet",
                    sent=client.game_packets_sent if client else 0,
                    received=client.game_packets_received if client else 0)
        if view != self.last_view:
            atomic_write(self.ui_path, ("return " + lua_value(view) + "\n").encode("utf-8"))
            self.last_view = view

    def command(self):
        try:
            with self.command_path.open("r", encoding="utf-8") as source:
                raw = source.read(2049)
            if len(raw) > 2048:
                return
            command = json.loads(raw)
        except (OSError, ValueError):
            return  # Retry incomplete writes; do not delete a newer command.
        if not isinstance(command, dict):
            return
        serial = command.get("serial")
        if type(serial) is not int or serial <= self.last_command:
            return
        self.last_command = serial
        if not self.client or not self.client.connected.is_set():
            self.message = "Not connected; retrying automatically"
            return
        op = command.get("op")
        fields = {}
        if op == "create":
            fields["name"] = (self.name[:36] + "'s lobby")
        elif op == "join":
            lobby_id = command.get("lobby_id")
            if not isinstance(lobby_id, str) or len(lobby_id) != 12 or any(c not in "0123456789abcdef" for c in lobby_id):
                return
            fields["lobby_id"] = lobby_id
        elif op == "ready":
            if type(command.get("value")) is not bool:
                return
            fields["value"] = command["value"]
        elif op not in ("queue", "leave", "finish"):
            return
        self.client.send(op, **fields)
        self.message = "Sent: " + op

    def step(self):
        if self.client:
            while True:
                try:
                    event = self.client.events.get_nowait()
                except queue.Empty:
                    break
                kind = event.get("event")
                if kind == "welcome":
                    if self.backend_rpc is not None:
                        self.backend_rpc.bind(event.get("client_id"), event.get("capabilities"), event.get("account"))
                    if self.native_rpc is not None:
                        self.native_rpc.transport_ports = (self.client.game_port, self.client.proxy_port)
                        self.native_rpc.multi_proxy_ports = getattr(self.client, "multi_proxy_ports", None)
                        self.native_rpc.remote_proxy = getattr(self.client, "remote_proxy", None)
                        caps = event.get("capabilities", {})
                        self.native_rpc.multi_capability = (type(caps) is dict
                            and type(caps.get("native_multi_transport")) is int and caps["native_multi_transport"] == 1)
                        self.native_rpc.bind_lan_identity(event.get("client_id"), event.get("capabilities"))
                    capabilities = event.get("capabilities")
                    capability = capabilities.get("native_search") if type(capabilities) is dict else None
                    self.native_capability = type(capability) is int and capability == 1
                    versions = capabilities.get("native_session_versions", []) if type(capabilities) is dict else []
                    transaction_capability = capabilities.get("native_session_transactions") if type(capabilities) is dict else None
                    self.native_session_capability = (type(versions) is list and any(type(v) is int and v == 2 for v in versions)
                        and type(transaction_capability) is int and transaction_capability == 1)
                    self.message = "Connected. Choose Quick match or a lobby"
                elif kind == "lan_backend_service" and self.backend_rpc is not None:
                    self.backend_rpc.publish(event)
                elif kind == "native_search" and self.native_rpc is not None:
                    LOG.info("Native bridge reply id=%s state=%s error=%r",
                             event.get("id"), event.get("state"), str(event.get("error", "none"))[:120])
                    self.native_rpc.publish(event)
                    if event.get("state") in ("cancelled", "error"):
                        self.native_pending.discard(event.get("id"))
                elif kind == "native_session_state" and self.native_rpc is not None:
                    self.native_rpc.publish(event)
                elif kind in ("native_session_result", "native_session_error", "native_session_transaction") and self.native_rpc is not None:
                    if kind == "native_session_error":
                        event = {"event": "native_session_result", "request_id": event.get("request_id"),
                                 "state": "error", "error": "native_session_rejected"}
                    self.native_rpc.publish(event)
                    if kind != "native_session_transaction" or event.get("state") != "prepared":
                        self.native_session_pending.pop(event.get("request_id", event.get("transaction_id")), None)
                elif kind == "match_start":
                    self.message = "Paired with " + event["opponent"] + "; selection entry not yet implemented"
                elif kind == "match_end":
                    self.message = event["reason"]
                elif kind == "error":
                    self.message = event["message"]
                elif kind == "disconnected":
                    self.native_disconnect()
                    self.client.close()
                    self.client = None
                    self.message = "Disconnected; reconnecting"
                    break
        self.native_commands()
        if self.backend_rpc is not None:
            for request in self.backend_rpc.drain():
                if self.client and self.client.connected.is_set():
                    try:
                        self.client.send("lan_backend_service", request=request)
                    except (OSError, ValueError):
                        self.backend_rpc.publish(dict(request_id=request["request_id"], state="error"))
                else:
                    self.backend_rpc.publish(dict(request_id=request["request_id"], state="error"))
        if self.native_rpc is None:
            self.command()
        self.publish()

    def native_disconnect(self):
        if getattr(self, "backend_rpc", None) is not None:
            self.backend_rpc.invalidate()
        self.native_capability = False
        self.native_session_capability = False
        if self.native_rpc is not None:
            self.native_rpc.invalidate_lan_identity()
            self.native_rpc.transport_ports = None
            self.native_rpc.publish({"event": "native_session_state", "session": None})
            for request_id in self.native_pending:
                self.native_rpc.publish({"event": "native_search", "id": request_id,
                                         "state": "error", "error": "disconnected"})
            for request_id, channel in getattr(self, "native_session_pending", {}).items():
                self.native_rpc.publish({"event": "native_session_transaction" if channel == "native_session_transaction" else "native_session_result",
                    "request_id" if channel == "native_session" else "transaction_id": request_id,
                    "state": "error", "error": "disconnected"})
        getattr(self, "native_session_pending", {}).clear()
        self.native_pending.clear()

    def native_commands(self):
        if self.native_rpc is None:
            return
        for request in self.native_rpc.drain():
            channel = request.get("channel")
            if channel in ("native_session", "native_session_transaction"):
                payload = request["request"]
                key = payload.get("request_id", payload.get("transaction_id"))
                if not self.client or not self.client.connected.is_set() or not getattr(self, "native_session_capability", False):
                    self.native_rpc.publish({"event": "native_session_transaction" if channel == "native_session_transaction" else "native_session_result",
                        "request_id" if channel == "native_session" else "transaction_id": key,
                        "state": "error", "error": "native_session_unavailable"})
                    continue
                try:
                    self.client.send(channel, request=payload)
                    self.native_session_pending[key] = channel
                    LOG.info("Native session forwarded op=%s generation=%s", payload["op"], request["id"])
                except (OSError, ValueError):
                    self.native_rpc.publish({"event": "native_session_transaction" if channel == "native_session_transaction" else "native_session_result",
                        "request_id" if channel == "native_session" else "transaction_id": key,
                        "state": "error", "error": "disconnected"})
                continue
            if not self.client or not self.client.connected.is_set() or not self.native_capability:
                LOG.warning("Native bridge unavailable op=%s id=%s connected=%s capability=%s",
                            request["op"], request["id"],
                            bool(self.client and self.client.connected.is_set()), self.native_capability)
                self.native_rpc.publish({"event": "native_search", "id": request["id"],
                                         "state": "error", "error": "native_search_unavailable"})
                continue
            try:
                self.client.send("native_search", request=request)
                query = request.get("query", {})
                LOG.info("Native bridge forwarded op=%s id=%s numeric=%s compound=%s",
                         request["op"], request["id"], len(query.get("filters", [])),
                         query.get("compound_count", 0))
                if request["op"] == "begin":
                    self.native_pending.add(request["id"])
            except (OSError, ValueError) as exc:
                LOG.warning("Native bridge send failed op=%s id=%s error=%r",
                            request["op"], request["id"], str(exc)[:120])
                self.native_rpc.publish({"event": "native_search", "id": request["id"],
                                         "state": "error", "error": "disconnected"})

    def run(self, stop=None):
        stop = stop or threading.Event()
        retry_at = 0
        try:
            if self.native_rpc is not None and not stop.is_set():
                self.backend_rpc = BackendServiceRPC(self.runtime, self.runtime.stem.removeprefix("lan_runtime_"))
            while not stop.is_set() and not self.stop_path.exists():
                if self.client is None and time.monotonic() >= retry_at:
                    try:
                        self.client = LobbyClient(self.cfg["server_host"], self.cfg["server_port"],
                                                  self.name, self.runtime,
                                                  game_port=self.native_game_port,
                                                  proxy_port=self.native_proxy_port,
                                                  account_token=(os.environ.get("SZERO_ARENA_ACCOUNT_TOKEN", "")
                                                      if self.cfg.get("account_mode") == "login" else ""))
                        if self.native_rpc is not None and self.native_game_port is None:
                            # A reconnect may replace the sidecar proxy socket,
                            # but not the port of an already-bound native game
                            # channel. Never require active-context reinit.
                            self.native_game_port = self.client.game_port
                            self.native_proxy_port = self.client.proxy_port
                    except (OSError, ValueError) as exc:
                        self.message = "Connection failed: " + str(exc)
                        LOG.warning(self.message)
                    retry_at = time.monotonic() + 3
                try:
                    self.step()
                except (OSError, ValueError) as exc:
                    self.message = str(exc)
                    LOG.warning("Game bridge: %s", exc)
                stop.wait(0.2)
        finally:
            # Runtime files can disappear or become unwritable. Their failure
            # must never prevent the TCP FIN/shutdown that releases server state.
            try:
                self.native_disconnect()
            except Exception:
                LOG.exception("Cannot publish final native disconnect")
            try:
                for ipc in (getattr(self, "backend_rpc", None), self.native_rpc):
                    try:
                        if ipc is not None:
                            ipc.close()
                    except Exception:
                        LOG.exception("Cannot close native IPC")
            finally:
                if self.client:
                    try:
                        self.client.close()
                    finally:
                        self.client = None
            self.message = "LAN bridge stopped"
            try:
                self.publish()
            except (OSError, ValueError):
                LOG.warning("Cannot publish final bridge status")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--watch-parent-stdin", action="store_true",
                        help=argparse.SUPPRESS)
    args = parser.parse_args()
    runtime = Path(args.runtime)
    # This dedicated bridge process must not open a log file or emit our
    # diagnostics unless this launch explicitly enabled mod logging.
    LOG.disabled = os.getenv("SZERO_LAN_MOD_LOGGING") != "1"
    if not LOG.disabled:
        configure_logging(runtime.with_suffix(".client.log"))
    stop = threading.Event()
    previous_signals = install_stop_signals(stop)
    try:
        if args.watch_parent_stdin:
            watch_parent_stream(parent_stream(), stop)
        GameBridge(args.game_root, runtime).run(stop)
    except (OSError, ValueError, KeyError) as exc:
        LOG.error("Cannot start in-game LAN bridge: %s", exc)
        return 1
    finally:
        restore_signals(previous_signals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
