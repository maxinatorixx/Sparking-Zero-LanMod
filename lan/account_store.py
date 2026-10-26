"""Persistent LAN accounts. Native match-result ingestion is a separate contract.

MariaDB is the production backend. SQLite is an explicit development/test backend,
never an automatic fallback when MariaDB is unavailable.
"""
import contextlib
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time

MODES = ("single", "dp", "team")
AVATARS = ("four-star", "fighter", "capsule")
BANNERS = ("orange", "blue", "purple")
TOKEN_SECONDS = 30 * 24 * 3600
# MariaDB TEXT permits at most65535bytes, including UTF8 rather than characters.
MAX_NATIVE_STATE_BYTES = 65535


def _native_state_json(state):
    """Bounded JSON storage envelope; callers still validate native schemas."""
    def check(value, depth=0):
        if depth > 64:
            raise ValueError("Native state is too deeply nested")
        if type(value) is dict:
            if any(type(key) is not str for key in value):
                raise ValueError("Native state keys must be strings")
            for item in value.values():
                check(item, depth + 1)
        elif type(value) is list:
            for item in value:
                check(item, depth + 1)
        elif type(value) not in (str, int, float, bool, type(None)):
            raise ValueError("Native state must contain only JSON values")
    if type(state) is not dict:
        raise ValueError("Native state must be an object")
    try:
        check(state)
        encoded = json.dumps(state, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False)
        size = len(encoded.encode("utf-8"))
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise ValueError("Invalid native state") from None
    if size > MAX_NATIVE_STATE_BYTES:
        raise ValueError("Native state exceeds storage bound")
    return encoded


def _password_hash(password, salt=None):
    if not isinstance(password, str) or len(password) <= 1:
        raise ValueError("Password must be longer than 1 character")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1)
    return salt.hex() + ":" + digest.hex()


def _password_matches(password, stored):
    try:
        salt, _ = stored.split(":", 1)
        return hmac.compare_digest(_password_hash(password, bytes.fromhex(salt)), stored)
    except (ValueError, TypeError, AttributeError):
        return False


def display_name(value):
    if not isinstance(value, str):
        raise ValueError("Display name is required")
    value = value.strip()
    if not 1 <= len(value) <= 32 or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("Display name must contain 1–32 printable characters")
    return value


class AccountStore:
    def __init__(self, connection, *, sqlite=False, admin_token=""):
        self.connection = connection
        self.sqlite = sqlite
        self.admin_token = admin_token
        self.lock = threading.RLock()
        self._migrate()

    @classmethod
    def from_env(cls):
        if os.getenv("ARENA_SQLITE_PATH"):
            return cls.for_sqlite(os.environ["ARENA_SQLITE_PATH"], os.getenv("ARENA_ADMIN_TOKEN", ""))
        import pymysql
        connection = pymysql.connect(host=os.getenv("ARENA_DB_HOST", "127.0.0.1"),
            port=int(os.getenv("ARENA_DB_PORT", "3306")), user=os.getenv("ARENA_DB_USER", "arena"),
            password=os.environ["ARENA_DB_PASSWORD"], database=os.getenv("ARENA_DB_NAME", "arena"),
            charset="utf8mb4", autocommit=False, connect_timeout=5,
            read_timeout=10, write_timeout=10)
        return cls(connection, admin_token=os.environ["ARENA_ADMIN_TOKEN"])

    @classmethod
    def for_sqlite(cls, path=":memory:", admin_token="test-admin-token"):
        connection = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        connection.execute("PRAGMA foreign_keys=ON")
        return cls(connection, sqlite=True, admin_token=admin_token)

    def close(self):
        with self.lock:
            self.connection.close()

    @contextlib.contextmanager
    def _tx(self):
        with self.lock:
            if not self.sqlite:
                self.connection.ping(reconnect=True)
            cursor = self.connection.cursor()
            try:
                cursor.execute("BEGIN IMMEDIATE" if self.sqlite else "START TRANSACTION")
                yield cursor
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise
            finally:
                cursor.close()

    def _execute(self, cursor, sql, params=()):
        cursor.execute(sql if self.sqlite else sql.replace("?", "%s"), params)
        return cursor

    def _migrate(self):
        identity = "INTEGER PRIMARY KEY AUTOINCREMENT" if self.sqlite else "BIGINT PRIMARY KEY AUTO_INCREMENT"
        statements = [
            "CREATE TABLE IF NOT EXISTS arena_setup (id INTEGER PRIMARY KEY, admin_claimed INTEGER NOT NULL)",
            f"CREATE TABLE IF NOT EXISTS accounts (id {identity}, username VARCHAR(32) NOT NULL UNIQUE, password_hash VARCHAR(200) NOT NULL, display_name VARCHAR(128) NOT NULL, is_admin INTEGER NOT NULL DEFAULT 0, avatar VARCHAR(32) NOT NULL DEFAULT 'four-star', banner VARCHAR(32) NOT NULL DEFAULT 'orange', created_at BIGINT NOT NULL, profile_json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS account_sessions (token_hash VARCHAR(64) PRIMARY KEY, account_id BIGINT NOT NULL, expires_at BIGINT NOT NULL, FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE)",
            "CREATE TABLE IF NOT EXISTS rankings (account_id BIGINT NOT NULL, mode VARCHAR(32) NOT NULL, rating INTEGER NOT NULL DEFAULT 1000, wins INTEGER NOT NULL DEFAULT 0, losses INTEGER NOT NULL DEFAULT 0, draws INTEGER NOT NULL DEFAULT 0, games INTEGER NOT NULL DEFAULT 0, win_streak INTEGER NOT NULL DEFAULT 0, max_win_streak INTEGER NOT NULL DEFAULT 0, updated_at BIGINT NOT NULL, PRIMARY KEY(account_id,mode), FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE)",
            "CREATE TABLE IF NOT EXISTS rank_events (event_id VARCHAR(128) PRIMARY KEY, payload_json TEXT NOT NULL, created_at BIGINT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS ranked_reports (event_id VARCHAR(128) PRIMARY KEY, account_a BIGINT NOT NULL, account_b BIGINT NOT NULL, category_a INTEGER, result_a INTEGER, category_b INTEGER, result_b INTEGER, updated_at BIGINT NOT NULL, FOREIGN KEY(account_a) REFERENCES accounts(id), FOREIGN KEY(account_b) REFERENCES accounts(id))",
            "CREATE TABLE IF NOT EXISTS native_profile_state (account_id BIGINT PRIMARY KEY, state_json TEXT NOT NULL, updated_at BIGINT NOT NULL, FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE)",
        ]
        with self.lock:
            cursor = self.connection.cursor()
            try:
                for sql in statements:
                    cursor.execute(sql)
                def ranking_columns():
                    cursor.execute('PRAGMA table_info(rankings)' if self.sqlite else 'SHOW COLUMNS FROM rankings')
                    return {row[1 if self.sqlite else 0] for row in cursor.fetchall()}
                for column in ('win_streak','max_win_streak'):
                    if column not in ranking_columns():
                        try:cursor.execute('ALTER TABLE rankings ADD COLUMN '+column+' INTEGER NOT NULL DEFAULT 0')
                        except Exception:
                            if column not in ranking_columns():raise
                cursor.execute("INSERT OR IGNORE INTO arena_setup VALUES (1,0)" if self.sqlite else
                               "INSERT IGNORE INTO arena_setup VALUES (1,0)")
                self.connection.commit()
            finally:
                cursor.close()

    def _profile(self, cursor, account_id):
        row = self._execute(cursor, "SELECT id,username,display_name,is_admin,avatar,banner,profile_json FROM accounts WHERE id=?", (account_id,)).fetchone()
        if not row:
            return None
        profile = dict(zip(("id", "username", "display_name", "is_admin", "avatar", "banner", "extensions"), row))
        profile["is_admin"] = bool(profile["is_admin"])
        profile["extensions"] = json.loads(profile["extensions"])
        ranks = self._execute(cursor, "SELECT mode,rating,wins,losses,draws,games,win_streak,max_win_streak FROM rankings WHERE account_id=? ORDER BY mode", (account_id,)).fetchall()
        profile["ranks"] = [dict(zip(("mode", "rating", "wins", "losses", "draws", "games", "win_streak", "max_win_streak"), rank)) for rank in ranks]
        return profile

    def _new_session(self, cursor, account_id):
        token = secrets.token_urlsafe(32)
        self._execute(cursor, "DELETE FROM account_sessions WHERE expires_at<=?", (int(time.time()),))
        self._execute(cursor, "INSERT INTO account_sessions (token_hash,account_id,expires_at) VALUES (?,?,?)",
                      (hashlib.sha256(token.encode()).hexdigest(), account_id, int(time.time()) + TOKEN_SECONDS))
        return {"token": token, "profile": self._profile(cursor, account_id)}

    def register(self, username, password, admin_token=""):
        if not isinstance(username, str) or not re.fullmatch(r"[A-Za-z0-9_]{3,32}", username):
            raise ValueError("Username must contain 3–32 letters, numbers or underscores")
        username = username.lower()
        encoded = _password_hash(password)
        with self._tx() as cursor:
            row = self._execute(cursor, "SELECT admin_claimed FROM arena_setup WHERE id=1" + ("" if self.sqlite else " FOR UPDATE")).fetchone()
            first = row[0] == 0
            if first and (not self.admin_token or not isinstance(admin_token, str) or not hmac.compare_digest(admin_token.encode('utf-8'), self.admin_token.encode('utf-8'))):
                raise ValueError("First registration requires the server admin token")
            if self._execute(cursor, "SELECT id FROM accounts WHERE username=?", (username,)).fetchone():
                raise ValueError("Username is already registered")
            self._execute(cursor, "INSERT INTO accounts (username,password_hash,display_name,is_admin,created_at,profile_json) VALUES (?,?,?,?,?,?)",
                          (username, encoded, username, int(first), int(time.time()), "{}"))
            account_id = cursor.lastrowid
            if first:
                cursor.execute("UPDATE arena_setup SET admin_claimed=1 WHERE id=1")
            for mode in MODES:
                self._execute(cursor, "INSERT INTO rankings (account_id,mode,updated_at) VALUES (?,?,?)", (account_id, mode, int(time.time())))
            return self._new_session(cursor, account_id)

    def login(self, username, password):
        if not isinstance(username, str) or not isinstance(password, str):
            raise ValueError("Invalid username or password")
        with self._tx() as cursor:
            row = self._execute(cursor, "SELECT id,password_hash FROM accounts WHERE username=?", (username.lower(),)).fetchone()
            # Equal-cost hashing for nonexistent accounts avoids a cheap enumeration signal.
            stored = row[1] if row else "00" * 16 + ":" + "00" * 64
            if not _password_matches(password, stored) or not row:
                raise ValueError("Invalid username or password")
            return self._new_session(cursor, row[0])

    def _account_for_token(self, cursor, token):
        if not isinstance(token, str) or not 20 <= len(token) <= 128:
            return None
        row = self._execute(cursor, "SELECT account_id FROM account_sessions WHERE token_hash=? AND expires_at>?",
                            (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()
        return row[0] if row else None

    def authenticate(self, token):
        with self._tx() as cursor:
            account_id = self._account_for_token(cursor, token)
            return self._profile(cursor, account_id) if account_id else None

    def logout(self, token):
        if not isinstance(token, str):
            return
        with self._tx() as cursor:
            self._execute(cursor, "DELETE FROM account_sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))

    def get_profile(self, account_id):
        if type(account_id) is not int or account_id < 1:
            return None
        with self._tx() as cursor:
            profile = self._profile(cursor, account_id)
            if profile:
                profile.pop("username", None)
                profile.pop("is_admin", None)
            return profile

    def update_profile(self, token, name, avatar="four-star", banner="orange"):
        name = display_name(name)
        if avatar not in AVATARS or banner not in BANNERS:
            raise ValueError("Unknown profile asset")
        with self._tx() as cursor:
            account_id = self._account_for_token(cursor, token)
            if not account_id:
                raise ValueError("Login expired")
            self._execute(cursor, "UPDATE accounts SET display_name=?,avatar=?,banner=? WHERE id=?", (name, avatar, banner, account_id))
            return self._profile(cursor, account_id)

    def rankings(self, mode="single", limit=100):
        if mode not in MODES or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Unknown ranking mode")
        with self._tx() as cursor:
            rows = self._execute(cursor, "SELECT a.id,a.display_name,a.avatar,a.banner,r.rating,r.wins,r.losses,r.draws,r.games FROM rankings r JOIN accounts a ON a.id=r.account_id WHERE r.mode=? ORDER BY r.rating DESC,r.wins DESC,a.id ASC LIMIT ?", (mode, limit)).fetchall()
            return [dict(zip(("id", "display_name", "avatar", "banner", "rating", "wins", "losses", "draws", "games"), row)) for row in rows]

    def setup_required(self):
        with self._tx() as cursor:
            return self._execute(cursor, "SELECT admin_claimed FROM arena_setup WHERE id=1").fetchone()[0] == 0

    def get_native_state(self, account_id):
        """Read an own-account snapshot without exposing it as web extensions."""
        if type(account_id) is not int or account_id < 1:
            raise ValueError("Invalid native-state account")
        with self._tx() as cursor:
            if self._execute(cursor, "SELECT id FROM accounts WHERE id=?", (account_id,)).fetchone() is None:
                raise ValueError("Unknown native-state account")
            row = self._execute(cursor, "SELECT state_json FROM native_profile_state WHERE account_id=?", (account_id,)).fetchone()
            if row is None:
                return {}
            # Revalidation also refuses malformed/out-of-bound manual DB edits.
            return json.loads(_native_state_json(json.loads(row[0])))

    def put_native_state(self, account_id, state):
        """Persist caller-validated native state, independent of LAN Elo.

        The server supplies the authenticated account ID. This is not a public
        player API, and the JSON envelope does not establish native field types.
        Locking the account row serializes first insert and replacement across
        distinct MariaDB connections; SQLite uses BEGIN IMMEDIATE instead.
        """
        if type(account_id) is not int or account_id < 1:
            raise ValueError("Invalid native-state account")
        encoded = _native_state_json(state)
        with self._tx() as cursor:
            if self._execute(cursor, "SELECT id FROM accounts WHERE id=?" + ("" if self.sqlite else " FOR UPDATE"), (account_id,)).fetchone() is None:
                raise ValueError("Unknown native-state account")
            present = self._execute(cursor, "SELECT account_id FROM native_profile_state WHERE account_id=?", (account_id,)).fetchone()
            now = int(time.time())
            if present:
                self._execute(cursor, "UPDATE native_profile_state SET state_json=?,updated_at=? WHERE account_id=?", (encoded, now, account_id))
            else:
                self._execute(cursor, "INSERT INTO native_profile_state (account_id,state_json,updated_at) VALUES (?,?,?)", (account_id, encoded, now))
            return json.loads(encoded)

    def record_result(self, match_id, mode, account_a, account_b, outcome_a):
        """Trusted server-only result boundary; never exposed as a player HTTP API.

        LAN Elo starts at 1000, K=32; native/offical ranks are independent. Caller
        must establish both participants and the result before invoking this.
        """
        if (not isinstance(match_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", match_id)
                or mode not in MODES or type(account_a) is not int or type(account_b) is not int
                or account_a < 1 or account_b < 1 or account_a == account_b
                or type(outcome_a) not in (int, float) or outcome_a not in (0, 0.5, 1)):
            raise ValueError("Invalid ranked result")
        # Canonical score representation makes0 and0.0 the same event.
        score = 0.5 if outcome_a == 0.5 else int(outcome_a)
        with self._tx() as cursor:
            return self._record_result(cursor, match_id, mode, account_a, account_b, score)

    def _record_result(self, cursor, match_id, mode, account_a, account_b, outcome_a):
        event = json.dumps({"mode": mode, "a": account_a, "b": account_b, "score_a": outcome_a}, sort_keys=True)
        # Stable row-lock order serializes results sharing either player.
        ranks = {}
        for account_id in sorted((account_a, account_b)):
            row = self._execute(cursor, "SELECT rating FROM rankings WHERE account_id=? AND mode=?" + ("" if self.sqlite else " FOR UPDATE"), (account_id, mode)).fetchone()
            if row is None:
                raise ValueError("Unknown ranked participant")
            ranks[account_id] = row[0]
        previous = self._execute(cursor, "SELECT payload_json FROM rank_events WHERE event_id=?", (match_id,)).fetchone()
        if previous:
            if previous[0] != event:
                raise ValueError("Conflicting duplicate ranked result")
            return False
        expected = 1 / (1 + 10 ** (max(-4000, min(4000, ranks[account_b] - ranks[account_a])) / 400))
        delta = round(32 * (outcome_a - expected))
        for account_id, score, change in ((account_a, outcome_a, delta), (account_b, 1-outcome_a, -delta)):
            self._execute(cursor, "UPDATE rankings SET rating=rating+?,wins=wins+?,losses=losses+?,draws=draws+?,games=games+1,max_win_streak=CASE WHEN ?=1 AND win_streak+1>max_win_streak THEN win_streak+1 ELSE max_win_streak END,win_streak=CASE WHEN ?=1 THEN win_streak+1 ELSE 0 END,updated_at=? WHERE account_id=? AND mode=?",
                          (change, int(score == 1), int(score == 0), int(score == 0.5), int(score == 1), int(score == 1), int(time.time()), account_id, mode))
        self._execute(cursor, "INSERT INTO rank_events VALUES (?,?,?)", (match_id, event, int(time.time())))
        return True

    def record_ranked_report(self, match_id, account_a, account_b, role, category, result):
        """Persist an issued round's own typed report and reconcile atomically.

        The server, not a request body, supplies role and account IDs. A valid
        own report receives a pending receipt without waiting for the peer.
        Only complementary Win/Lose or Draw/Draw in the same raw category can
        update LAN Elo. Completion outcome and native rank points are unrelated.
        """
        if (type(match_id) is not str or re.fullmatch(r"[0-9a-f]{32}", match_id) is None
                or any(type(value) is not int or value < 1 for value in (account_a, account_b))
                or type(role) is not int or role not in (0, 1)
                or type(category) is not int or category not in (1, 2, 3)
                or type(result) is not int or result not in (0, 1, 2, 3)):
            raise ValueError("Invalid typed ranked report")
        with self._tx() as cursor:
            # Lock known participants first so first insert is serialized even
            # across independent MariaDB connections. SQLite BEGIN IMMEDIATE
            # supplies the same write exclusion.
            for account_id in sorted(set((account_a, account_b))):
                if self._execute(cursor, "SELECT id FROM accounts WHERE id=?" +
                        ("" if self.sqlite else " FOR UPDATE"), (account_id,)).fetchone() is None:
                    raise ValueError("Unknown ranked participant")
            row = self._execute(cursor,
                "SELECT account_a,account_b,category_a,result_a,category_b,result_b FROM ranked_reports WHERE event_id=?" +
                ("" if self.sqlite else " FOR UPDATE"), (match_id,)).fetchone()
            if row is None:
                values = [None, None, None, None]
                values[role*2:role*2+2] = [category, result]
                self._execute(cursor, "INSERT INTO ranked_reports (event_id,account_a,account_b,category_a,result_a,category_b,result_b,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                    (match_id, account_a, account_b, *values, int(time.time())))
            else:
                if tuple(row[:2]) != (account_a, account_b):
                    raise ValueError("Ranked report ownership changed")
                values = list(row[2:])
                previous_category, previous_result = values[role*2:role*2+2]
                if previous_category is not None and (previous_category != category or
                        (previous_result not in (None, 0) and previous_result != result)):
                    raise ValueError("Conflicting duplicate typed ranked report")
                values[role*2:role*2+2] = [category, result]
                side = "a" if role == 0 else "b"
                self._execute(cursor, "UPDATE ranked_reports SET category_"+side+"=?,result_"+side+"=?,updated_at=? WHERE event_id=?",
                    (category, result, int(time.time()), match_id))
            ca, ra, cb, rb = values
            if account_a == account_b:
                return "self_play"
            if ra in (None, 0) or rb in (None, 0):
                return "pending"
            if ca != cb or (ra, rb) not in ((1, 2), (2, 1), (3, 3)):
                return "conflict"
            mode = {1: "single", 2: "dp", 3: "team"}[ca]
            score = {1: 1, 2: 0, 3: 0.5}[ra]
            self._record_result(cursor, match_id, mode, account_a, account_b, score)
            return "recorded"
