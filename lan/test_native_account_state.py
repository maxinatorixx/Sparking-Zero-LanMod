"""Own-account native snapshot persistence; independent from LAN Elo."""
from pathlib import Path
import tempfile
import threading
import unittest

from account_store import AccountStore, MAX_NATIVE_STATE_BYTES


class NativeAccountStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / "accounts.db")
        self.store = AccountStore.for_sqlite(self.path, "bootstrap-secret")

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def account(self, name="alice"):
        return self.store.register(name, "test-password", "bootstrap-secret")

    def test_native_state_persists_independently_without_web_or_elo_changes(self):
        a = self.account()["profile"]["id"]
        b = self.account("bobby")["profile"]["id"]
        self.assertEqual(self.store.get_native_state(a), {})
        state = {"schema": 1, "rank": [{"battle_type": 1, "rank_point": 3456}],
                 "stats": {"wins": 1, "name": "悟空"}}
        returned = self.store.put_native_state(a, state)
        state["rank"][0]["rank_point"] = 9999
        returned["stats"]["wins"] = 99
        self.assertEqual(self.store.get_native_state(a)["rank"][0]["rank_point"], 3456)
        self.assertEqual(self.store.get_native_state(a)["stats"]["wins"], 1)
        self.assertEqual(self.store.get_native_state(b), {})
        self.assertEqual(self.store.get_profile(a)["extensions"], {})
        self.assertNotIn("native_state", self.store.get_profile(a))
        self.assertEqual([rank["rating"] for rank in self.store.rankings()], [1000, 1000])
        self.assertEqual([rank["games"] for rank in self.store.rankings()], [0, 0])
        self.store.close()
        self.store = AccountStore.for_sqlite(self.path, "bootstrap-secret")
        self.assertEqual(self.store.get_native_state(a)["stats"]["name"], "悟空")
        self.assertEqual(self.store.put_native_state(a, {"schema": 2}), {"schema": 2})
        self.assertEqual(self.store.get_native_state(a), {"schema": 2})

    def test_native_state_refuses_invalid_json_and_unknown_account_atomically(self):
        a = self.account()["profile"]["id"]
        self.store.put_native_state(a, {"valid": 1})
        nested = {}
        for _ in range(66):
            nested = {"next": nested}
        invalid = [None, [], True, {1: "key"}, {"tuple": (1, 2)},
                   {"bytes": b"not JSON"}, {"nan": float("nan")},
                   {"inf": float("inf")}, {"bad": "\ud800"}, nested,
                   {"huge": "x" * MAX_NATIVE_STATE_BYTES},
                   {"utf8": "悟" * (MAX_NATIVE_STATE_BYTES // 2)}]
        for state in invalid:
            with self.subTest(kind=type(state).__name__), self.assertRaises(ValueError):
                self.store.put_native_state(a, state)
            self.assertEqual(self.store.get_native_state(a), {"valid": 1})
        for account in (True, 0, -1, "1", 9999):
            with self.subTest(account=account), self.assertRaises(ValueError):
                self.store.get_native_state(account)
            with self.subTest(account=account), self.assertRaises(ValueError):
                self.store.put_native_state(account, {})

    def test_native_state_text_bound_and_concurrent_replacements(self):
        a = self.account()["profile"]["id"]
        exact = {"x": "a" * (MAX_NATIVE_STATE_BYTES - len('{"x":""}'))}
        self.assertEqual(self.store.put_native_state(a, exact), exact)
        other = AccountStore.for_sqlite(self.path, "bootstrap-secret")
        errors = []
        def write(store, value):
            try:
                for _ in range(4):
                    store.put_native_state(a, {"whole": [value] * 100})
            except Exception as error:
                errors.append(error)
        threads = [threading.Thread(target=write, args=(store, value))
                   for store, value in ((self.store, "first"), (other, "second"))]
        try:
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertFalse(errors)
            self.assertIn(self.store.get_native_state(a),
                          ({"whole": ["first"] * 100}, {"whole": ["second"] * 100}))
        finally:
            other.close()
