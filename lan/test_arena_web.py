import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from account_store import AccountStore
from arena_web import ArenaHTTPServer


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = AccountStore.for_sqlite(admin_token="admin-secret")
        root = Path(self.temp.name)
        self.logs = root / "server.log"
        self.logs.write_text("game server fixture line\n")
        self.restart = root / "run/restart-game"
        self.server = ArenaHTTPServer(("127.0.0.1", 0), self.store, logs=self.logs, restart=self.restart)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:" + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.store.close()
        self.temp.cleanup()

    def request(self, path, body=None, token="", origin=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        if origin:
            headers["Origin"] = origin
        request = Request(self.base + path, headers=headers, data=json.dumps(body).encode() if body is not None else None)
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            with error:
                return error.code, json.load(error)

    def register(self, username="alice"):
        code, data = self.request("/api/register", {"username": username, "password": "test-password", "admin_token": "admin-secret"})
        self.assertEqual(code, 200)
        return data

    def test_register_login_profile_rankings_and_logout(self):
        self.assertTrue(self.request("/api/status")[1]["setup_required"])
        data = self.register()
        token = data["token"]
        self.assertFalse(self.request("/api/status")[1]["setup_required"])
        self.assertEqual(self.request("/api/me", token=token)[1]["profile"]["username"], "alice")
        self.assertEqual(self.request("/api/profile", {"display_name": "Vegeta", "avatar": "capsule", "banner": "purple"}, token)[0], 200)
        ranks = self.request("/api/rankings?mode=dp")[1]["rankings"]
        self.assertEqual(ranks[0]["display_name"], "Vegeta")
        self.assertEqual(ranks[0]["rating"], 1000)
        self.assertEqual(self.request("/api/logout", {}, token)[0], 200)
        self.assertEqual(self.request("/api/me", token=token)[0], 401)
        self.assertEqual(self.request("/api/login", {"username": "alice", "password": "test-password"})[0], 200)

    def test_admin_controls_and_cross_origin_refusal(self):
        admin = self.register()["token"]
        normal = self.register("bobby")["token"]
        self.assertEqual(self.request("/api/admin/logs", token=normal)[0], 401)
        self.assertEqual(self.request("/api/admin/restart", {}, normal)[0], 401)
        self.assertFalse(self.restart.exists())
        self.assertIn("fixture line", self.request("/api/admin/logs", token=admin)[1]["log"])
        self.assertEqual(self.request("/api/admin/restart", {}, admin, "https://other.example")[0], 401)
        self.assertFalse(self.restart.exists())
        self.assertEqual(self.request("/api/admin/restart", {}, admin, self.base)[0], 200)
        self.assertTrue(self.restart.exists())
        self.assertEqual(self.request("/api/result", {"wins": 100}, normal)[0], 404)

    def test_static_and_unknown_asset_path(self):
        with urlopen(self.base + "/", timeout=3) as response:
            self.assertIn(b"FIGHTER NETWORK", response.read())
            self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])
        self.assertEqual(self.request("/../account_store.py")[0], 404)
