"""Real loopback IPC -> GameBridge -> TCP-owned service, no game execution."""
import json
import socket
import os
from pathlib import Path
import shutil
import subprocess
import unittest

import test_native_session_bridge as fixtures


class BackendBridgeTests(unittest.TestCase):
    setUp = fixtures.NativeSessionBridgeTests.setUp
    tearDown = fixtures.NativeSessionBridgeTests.tearDown
    bridge = fixtures.NativeSessionBridgeTests.bridge

    def call(self, bridge, path, target=None):
        rpc = bridge.backend_rpc
        with socket.create_connection(("127.0.0.1", int(rpc.endpoint.read_text())), 2) as connection:
            connection.settimeout(7)
            line = (f"SERVICE1 {rpc.instance} {path}" if target is None else
                    f"SERVICE2 {rpc.instance} {path} {target}")
            connection.sendall((line+"\n").encode("ascii"))
            with connection.makefile("rb") as stream:
                line = stream.readline(16)
                if line == b"ERR\n":
                    return None
                size = int(line)
                return json.loads(stream.read(size))

    def test_socket_owned_login_followups_and_disconnect(self):
        a, _, _ = self.bridge("a")
        b, _, _ = self.bridge("b")
        self.assertIsNone(self.call(a, "/user/check_transaction.php"))
        login_a = self.call(a, "/user/login.php")
        login_b = self.call(b, "/user/login.php")
        self.assertIs(type(login_a["res"]), int)
        self.assertEqual(login_a["res"], 0)
        self.assertTrue(login_a["session_code"].startswith("szlan-"))
        self.assertNotEqual(login_a["session_code"], login_b["session_code"])
        self.assertEqual(self.call(a, "/user/login.php")["session_code"], login_a["session_code"])
        self.assertEqual(self.call(a, "/user/check_transaction.php"),
                         {"res": 0, "reward_ids": [], "match_phase": 0, "is_present_receive": False})
        self.assertEqual(self.call(a, "/system/get_notice.php"), {"res": 0})
        self.assertEqual(self.call(a, "/shop_banner/get_list.php"), {"res": 0, "shop_banner_info_list": []})
        self.assertEqual(len(self.call(a, "/pvp/get_report_taken_counts.php")), 5)
        self.assertIsNone(self.call(a, "/user/get_player_card.php"))
        own_card = self.call(a, "/user/get_player_card.php", "self")
        self.assertEqual(own_card["res"], 0)
        self.assertIs(type(own_card["player_card"]["player_rank"]), int)
        self.assertIsNone(self.call(a, "/user/get_player_card.php", "szlan:"+b.backend_rpc.bound))
        self.assertIsNone(self.call(a, "/user/get_player_card.php", "official-account"))
        a.native_disconnect()
        self.assertIsNone(self.call(a, "/user/login.php"))
        self.assertEqual(len(self.server.native_sessions.sessions), 0)

    @unittest.skipUnless(shutil.which("x86_64-w64-mingw32-gcc") and shutil.which("wine"), "requires MinGW/Wine")
    def test_compiled_native_worker_full_server_path(self):
        prefix = os.environ.get("WINEPREFIX", "")
        self.assertTrue(prefix.startswith("/tmp/szero-"), "Use disposable test Wine prefix")
        a, _, _ = self.bridge("a")
        native = Path(__file__).resolve().parent/"native"
        exe = a.runtime.parent/"adapter.exe"
        subprocess.run(["x86_64-w64-mingw32-gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                        "-static-libgcc", "-Wl,--no-insert-timestamp", "-municode",
                        str(native/"test_backend_adapter.c"), str(native/"backend_response.c"),
                        *(str(native/"vendor/minhook/src"/name) for name in
                          ("buffer.c", "hook.c", "trampoline.c", "hde/hde64.c")),
                        "-o", str(exe), "-lbcrypt", "-lws2_32"], check=True, capture_output=True)
        result = subprocess.run(["wine", str(exe), a.backend_rpc.instance, "bridge"],
                                capture_output=True, text=True, timeout=25,
                                env=dict(os.environ, WINEDEBUG="-all"))
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn("real bridge/server LAN login contract passed", result.stdout)
