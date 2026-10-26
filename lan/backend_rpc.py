"""Instance-bound LAN service IPC. Never accepts URLs, tickets or native pointers.

Only the socket worker waits. GameBridge forwards value-only route requests over
its existing authenticated-by-connection LAN peer. Disconnect invalidates this
instance permanently; cached login credentials must not silently change owner.
"""
from __future__ import annotations

import json
from pathlib import Path
import queue
import re
import socket
import threading
import time

from installer import atomic_write
from native_rank import validate_rank_snapshot
from native_profile import PROFILE_ROUTES, validate_profile_update

ROUTES = frozenset(("/user/login.php", "/user/check_transaction.php",
                    "/system/get_notice.php", "/pvp/get_report_taken_counts.php",
                    "/shop_banner/get_list.php", "/pvp/start_battle_player1.php",
                    ))
CARD_ROUTE = "/user/get_player_card.php"
CODE_START_ROUTE = "/pvp/start_battle_player2.php"
END_ROUTES = ("/pvp/end_battle_player1.php", "/pvp/end_battle_player2.php")
MAX_BODY = 65536


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate rank snapshot field")
        result[key] = value
    return result


class BackendServiceRPC:
    def __init__(self, runtime, instance):
        if not re.fullmatch(r"[0-9a-f]{32}", instance):
            raise ValueError("invalid service instance")
        self.instance = instance
        self.endpoint = Path(runtime).with_suffix(".service.endpoint")
        self.account_policy = Path(runtime).with_suffix(".account.policy")
        self.commands = queue.Queue(maxsize=1)
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.ready = threading.Event()
        self.done = threading.Event()
        self.bound = None
        self.invalid = False
        self.serial = 0
        self.pending = None
        self.response = None
        self.active = None
        self.listener = socket.socket()
        try:
            self.listener.bind(("127.0.0.1", 0))
            self.listener.listen(1)
            self.listener.settimeout(.2)
            atomic_write(self.endpoint, (str(self.listener.getsockname()[1])+"\n").encode("ascii"))
            atomic_write(self.account_policy, b"0\n")
        except BaseException:
            self.listener.close()
            raise
        self.worker = threading.Thread(target=self._run, name="LAN backend IPC", daemon=True)
        self.worker.start()

    def bind(self, peer_id, capabilities, account=None):
        valid = (type(peer_id) is str and re.fullmatch(r"[0-9a-f]{32}", peer_id)
                 and type(capabilities) is dict
                 and type(capabilities.get("lan_backend_services")) is int
                 and capabilities["lan_backend_services"] == 1)
        with self.lock:
            if not valid or self.invalid or (self.bound is not None and peer_id != self.bound):
                self.invalid = True
                self.ready.clear()
                self.done.set()
                return False
            self.bound = peer_id
            ranked = (type(account) is dict and account.get("authenticated") is True
                      and account.get("ranked") is True)
            atomic_write(self.account_policy, b"1\n" if ranked else b"0\n")
            self.ready.set()
            return True

    def invalidate(self):
        with self.lock:
            # Failure before binding can still retry; an established native
            # cached session may never be rebound to a new TCP identity.
            self.invalid = self.invalid or self.bound is not None
            self.ready.clear()
            self.response = None
            self.done.set()
            atomic_write(self.account_policy, b"0\n")

    def drain(self):
        while True:
            try:
                request = self.commands.get_nowait()
            except queue.Empty:
                return
            with self.lock:
                valid = self.ready.is_set() and request["request_id"] == self.pending
            if valid:
                yield request

    def publish(self, event):
        with self.lock:
            if event.get("request_id") != self.pending or not self.ready.is_set():
                return
            body = event.get("body")
            if event.get("state") == "ok" and type(body) is dict:
                try:
                    encoded = json.dumps(body, separators=(",", ":"), allow_nan=False).encode("utf-8")
                except (ValueError, TypeError, RecursionError):
                    encoded = b""
                if len(encoded) <= MAX_BODY:
                    self.response = encoded
            self.done.set()

    def _serve(self, connection):
        connection.settimeout(2)
        # One bounded line, no buffering beyond this request and no body input.
        line = bytearray()
        deadline = time.monotonic()+2
        while len(line) < 4096:
            remaining = deadline-time.monotonic()
            if remaining <= 0 or self.stop.is_set():
                return
            connection.settimeout(remaining)
            byte = connection.recv(1)
            if not byte:
                return
            line += byte
            if byte == b"\n":
                break
        parts = bytes(line).rstrip(b"\n").split(b" ")
        if (not line.endswith(b"\n") or len(parts) not in (3, 4, 6, 8)
                or parts[1] != self.instance.encode("ascii")):
            connection.sendall(b"ERR\n")
            return
        try:
            path = parts[2].decode("ascii")
            body = {}
            if len(parts) == 3:
                valid = parts[0] == b"SERVICE1" and path in ROUTES
            elif len(parts) == 4 and parts[0]==b"SERVICE4":
                valid = path in PROFILE_ROUTES and re.fullmatch(rb"(?:[0-9a-f]{2}){1,1023}",parts[3]) is not None
                if valid:
                    body=json.loads(bytes.fromhex(parts[3].decode('ascii')).decode('utf-8'),object_pairs_hook=unique_object)
                    validate_profile_update(path,body)
            elif len(parts) == 4:
                target = parts[3].decode("ascii")
                valid = (parts[0] == b"SERVICE2" and path == CARD_ROUTE and
                         (target == "self" or re.fullmatch(r"szlan:[0-9a-f]{32}", target) is not None))
                body = {"target": target}
            elif len(parts)==8:
                code=parts[3].decode('ascii')
                valid=(parts[0]==b'SERVICE5' and path in END_ROUTES
                       and re.fullmatch(r'[0-9a-f]{32}',code) is not None
                       and parts[4] in (b'1',b'2') and parts[5] in (b'1',b'2',b'3')
                       and parts[6] in (b'0',b'1',b'2',b'3')
                       and re.fullmatch(rb'(?:[0-9a-f]{2}){1,1023}',parts[7]) is not None)
                if valid:
                    snapshot=json.loads(bytes.fromhex(parts[7].decode('ascii')).decode('utf-8'),object_pairs_hook=unique_object)
                    validate_rank_snapshot(snapshot)
                    body={'match_code':code,'outcome':int(parts[4]),'native_category':int(parts[5]),
                          'native_result':int(parts[6]),'rank_snapshot':snapshot}
            else:
                code = parts[3].decode("ascii")
                valid = parts[0] == b"SERVICE3" and re.fullmatch(r"[0-9a-f]{32}", code) is not None
                if path == CODE_START_ROUTE:
                    valid = valid and parts[4:] == [b"-", b"-"]
                    body = {"match_code": code}
                elif path in END_ROUTES:
                    valid = valid and parts[4] in (b"1", b"2") and re.fullmatch(rb"(?:[0-9a-f]{2}){1,1023}", parts[5]) is not None
                    if valid:
                        snapshot = json.loads(bytes.fromhex(parts[5].decode("ascii")).decode("utf-8"), object_pairs_hook=unique_object)
                        validate_rank_snapshot(snapshot)
                        body = {"match_code": code, "outcome": int(parts[4]), "rank_snapshot": snapshot}
                else:
                    valid = False
        except (UnicodeError, ValueError, TypeError, RecursionError):
            path = ""
            valid = False
        with self.lock:
            refused = not valid or not self.ready.is_set() or self.invalid
            if not refused:
                self.serial += 1
                self.pending = "service-" + str(self.serial)
                self.response = None
                self.done.clear()
                self.commands.put_nowait({"request_id": self.pending, "path": path, "body": body})
        connection.settimeout(2)
        if refused:
            connection.sendall(b"ERR\n")
            return
        self.done.wait(5)
        with self.lock:
            response = self.response if self.ready.is_set() else None
            self.pending = None
            self.response = None
        connection.sendall((str(len(response)).encode("ascii")+b"\n"+response) if response else b"ERR\n")

    def _run(self):
        while not self.stop.is_set():
            try:
                connection, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with connection:
                with self.lock:
                    if self.stop.is_set():
                        break
                    self.active = connection
                try:
                    self._serve(connection)
                except (OSError, ValueError, queue.Full):
                    pass
                finally:
                    with self.lock:
                        self.active = None

    def close(self):
        self.invalidate()
        self.stop.set()
        self.done.set()
        self.listener.close()
        with self.lock:
            active = self.active
        if active is not None:
            try:
                active.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            active.close()
        self.worker.join(3)
        self.endpoint.unlink(missing_ok=True)
        self.account_policy.unlink(missing_ok=True)
