from pathlib import Path
import tempfile
import threading
import unittest

from account_store import AccountStore
from arena_supervisor import read_secrets


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / "accounts.db")
        self.store = AccountStore.for_sqlite(self.path, "bootstrap-secret")

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def account(self, name="alice"):
        return self.store.register(name, "test-password", "bootstrap-secret")

    def test_first_admin_token_and_later_registration(self):
        with self.assertRaises(ValueError):
            self.store.register("alice", "test-password")
        admin = self.account()
        self.assertTrue(admin["profile"]["is_admin"])
        other = self.account("bobby")
        self.assertFalse(other["profile"]["is_admin"])
        with self.assertRaises(ValueError):
            self.account("ALICE")
        self.assertEqual(self.store.login("ALICE", "test-password")["profile"]["id"], admin["profile"]["id"])
        with self.assertRaises(ValueError):
            self.store.login("alice", "wrong-password")

    def test_two_character_passwords_and_unicode_admin_token(self):
        for password in ("", "x"):
            with self.assertRaises(ValueError):
                self.store.register("short", password, "bootstrap-secret")
        self.store.admin_token = "ä!"
        account = self.store.register("short", "a!", "ä!")
        self.assertTrue(account["profile"]["is_admin"])
        self.assertEqual(self.store.login("short", "a!")["profile"]["id"], account["profile"]["id"])

    def test_server_secrets_only_require_more_than_one_character(self):
        values = {key: "ä!" for key in ("ARENA_ADMIN_TOKEN", "ARENA_DB_PASSWORD", "ARENA_DB_EDITOR_PASSWORD")}
        self.assertEqual(read_secrets(values), values)
        for key in values:
            for invalid in ("", "x"):
                with self.assertRaisesRegex(ValueError, key):
                    read_secrets(dict(values, **{key: invalid}))
        self.assertEqual(read_secrets(dict(values, ARENA_ADMIN_TOKEN="!"*200))["ARENA_ADMIN_TOKEN"], "!"*200)

    def test_profile_persists_revocation_and_no_plaintext_secrets(self):
        account = self.account()
        token = account["token"]
        profile = self.store.update_profile(token, "Son Goku", "fighter", "blue")
        self.assertEqual(profile["display_name"], "Son Goku")
        with self.assertRaises(ValueError):
            self.store.update_profile(token, "Name\nInjection")
        with self.assertRaises(ValueError):
            self.store.update_profile(token, "Name", "../../file")
        self.store.close()
        self.store = AccountStore.for_sqlite(self.path, "bootstrap-secret")
        self.assertEqual(self.store.authenticate(token)["display_name"], "Son Goku")
        raw = Path(self.path).read_bytes()
        self.assertNotIn(token.encode(), raw)
        self.assertNotIn(b"test-password", raw)
        self.store.logout(token)
        self.assertIsNone(self.store.authenticate(token))

    def test_rank_result_atomic_idempotent_independent_modes(self):
        a = self.account()["profile"]["id"]
        b = self.account("bobby")["profile"]["id"]
        self.assertTrue(self.store.record_result("match-1", "single", a, b, 1))
        self.assertFalse(self.store.record_result("match-1", "single", a, b, 1))
        with self.assertRaises(ValueError):
            self.store.record_result("match-1", "single", a, b, 0)
        rank = self.store.rankings("single")
        self.assertEqual([r["rating"] for r in rank], [1016, 984])
        self.assertEqual(rank[0]["wins"], 1)
        self.assertEqual(rank[1]["losses"], 1)
        self.assertEqual([r["rating"] for r in self.store.rankings("dp")], [1000, 1000])
        with self.assertRaises(ValueError):
            self.store.record_result("missing", "single", a, 999, 1)
        self.assertEqual(self.store.rankings()[0]["games"], 1)

    def test_concurrent_first_registration_only_one_admin(self):
        second = AccountStore.for_sqlite(self.path, "bootstrap-secret")
        result = []
        def register(store, name):
            result.append(store.register(name, "test-password", "bootstrap-secret")["profile"])
        threads = [threading.Thread(target=register, args=(store, name)) for store, name in ((self.store,"alice"),(second,"bobby"))]
        try:
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(sum(profile["is_admin"] for profile in result), 1)
        finally:
            second.close()
