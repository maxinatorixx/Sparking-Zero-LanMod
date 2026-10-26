"""Same-origin Arena account UI/API. No PHP, cookies, shell or Docker socket."""
import collections
import json
import logging
import os
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from account_store import AccountStore, AVATARS, BANNERS, MODES


class ArenaHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, store, *, static=None, logs="/logs/server.log", restart="/data/run/restart-game"):
        super().__init__(address, ArenaHandler)
        self.store = store
        self.static = Path(static or Path(__file__).with_name("web"))
        self.logs = Path(logs)
        self.restart = Path(restart)
        self.rate_lock = threading.Lock()
        self.rates = collections.OrderedDict()
        self.workers = threading.BoundedSemaphore(32)

    def process_request(self, request, client_address):
        if not self.workers.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.workers.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.workers.release()

    def allow_auth(self, ip):
        now = time.monotonic()
        with self.rate_lock:
            bucket = self.rates.pop(ip, collections.deque())
            while bucket and bucket[0] < now - 60:
                bucket.popleft()
            allowed = len(bucket) < 12
            if allowed:
                bucket.append(now)
            self.rates[ip] = bucket
            while len(self.rates) > 2048:
                self.rates.popitem(last=False)
            return allowed


class ArenaHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "Arena"

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, fmt, *args):
        # No request URLs, credentials, tokens or bodies in access logs.
        pass

    def _reply(self, code, data, content_type="application/json; charset=utf-8"):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        self.end_headers()
        self.wfile.write(data)

    def _token(self):
        value = self.headers.get("Authorization", "")
        return value[7:] if value.startswith("Bearer ") else ""

    def _profile(self, admin=False):
        profile = self.server.store.authenticate(self._token())
        if not profile or admin and not profile["is_admin"]:
            raise PermissionError("Administrator login required" if admin else "Login required")
        return profile

    def do_GET(self):
        try:
            path = urlsplit(self.path).path
            if path in ("/", "/index.html", "/arena.js", "/arena.css", "/avatar.svg"):
                name = "index.html" if path == "/" else path[1:]
                types = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}
                self._reply(200, (self.server.static / name).read_bytes(), types[Path(name).suffix] + "; charset=utf-8")
            elif path == "/api/status":
                self._reply(200, {"setup_required": self.server.store.setup_required(), "modes": MODES, "avatars": AVATARS, "banners": BANNERS,
                                  "ranking": {"initial": 1000, "k": 32, "automatic_result_sync": True}})
            elif path == "/api/me":
                self._reply(200, {"profile": self._profile()})
            elif path == "/api/rankings":
                mode = parse_qs(urlsplit(self.path).query).get("mode", ["single"])[0]
                self._reply(200, {"mode": mode, "rankings": self.server.store.rankings(mode)})
            elif path == "/api/admin/logs":
                self._profile(admin=True)
                try:
                    with self.server.logs.open("rb") as stream:
                        stream.seek(0, 2)
                        stream.seek(max(0, stream.tell() - 65536))
                        content = stream.read(65536).decode("utf-8", "replace")
                except FileNotFoundError:
                    content = "No game server log yet."
                self._reply(200, {"log": "\n".join(content.splitlines()[-200:])})
            else:
                self._reply(404, {"error": "Not found"})
        except PermissionError as exc:
            self._reply(401, {"error": str(exc)})
        except ValueError as exc:
            self._reply(400, {"error": str(exc)})
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        except Exception:
            logging.exception("Web request failed")
            self._reply(503, {"error": "Service temporarily unavailable"})

    def do_POST(self):
        self.close_connection = True
        try:
            # Bearer tokens avoid cookie CSRF. Explicitly reject cross-origin JSON
            # writes too, including login/registration. Proxy Host must be preserved.
            origin = self.headers.get("Origin")
            public = os.getenv("ARENA_PUBLIC_URL", "")
            allowed_host = urlsplit(public).netloc if public else self.headers.get("Host", "")
            if origin and (urlsplit(origin).netloc != allowed_host or urlsplit(origin).scheme not in ("http", "https")):
                raise PermissionError("Cross-origin request refused")
            if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json":
                raise ValueError("Expected a JSON request")
            length = int(self.headers.get("Content-Length", "0"))
            if not 2 <= length <= 16384:
                raise ValueError("Request is too large or empty")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("Expected a JSON object")
            path = urlsplit(self.path).path
            if path in ("/api/register", "/api/login"):
                if not self.server.allow_auth(self.client_address[0]):
                    self._reply(429, {"error": "Too many login attempts; wait one minute"})
                    return
                if path == "/api/register":
                    result = self.server.store.register(body.get("username"), body.get("password"), body.get("admin_token", ""))
                else:
                    result = self.server.store.login(body.get("username"), body.get("password"))
                self._reply(200, result)
            elif path == "/api/logout":
                self.server.store.logout(self._token())
                self._reply(200, {"ok": True})
            elif path == "/api/profile":
                self._profile()
                profile = self.server.store.update_profile(self._token(), body.get("display_name"), body.get("avatar", "four-star"), body.get("banner", "orange"))
                self._reply(200, {"profile": profile})
            elif path == "/api/admin/restart":
                self._profile(admin=True)
                self.server.restart.parent.mkdir(parents=True, exist_ok=True)
                # A fixed sentinel, never user-controlled process IDs or commands.
                self.server.restart.touch(exist_ok=True)
                self._reply(200, {"ok": True, "message": "Game server restart requested. Connected games will disconnect."})
            else:
                self._reply(404, {"error": "Not found"})
        except PermissionError as exc:
            self._reply(401, {"error": str(exc)})
        except (ValueError, UnicodeError) as exc:
            self._reply(400, {"error": str(exc)})
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        except Exception:
            logging.exception("Web request failed")
            self._reply(503, {"error": "Service temporarily unavailable"})


def main():
    logging.basicConfig(level=logging.INFO)
    store = AccountStore.from_env()
    server = ArenaHTTPServer(("0.0.0.0", int(os.getenv("ARENA_WEB_PORT", "8080"))), store)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        store.close()


if __name__ == "__main__":
    main()
