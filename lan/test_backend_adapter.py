"""Actual Win64 helper/loopback IPC fixture, never game or authentication proof."""
import json
import hashlib
import os
from pathlib import Path
import shutil
import socketserver
import subprocess
import tempfile
import threading
import time
import unittest
import uuid


@unittest.skipUnless(shutil.which("x86_64-w64-mingw32-gcc") and shutil.which("wine"),
                     "requires existing MinGW and disposable Wine")
class BackendAdapterTests(unittest.TestCase):
    def test_portable_response_contracts(self):
        native = Path(__file__).resolve().parent / "native"
        with tempfile.TemporaryDirectory(prefix="szero-backend-response-") as folder:
            executable = Path(folder) / "response"
            subprocess.run(["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic",
                            str(native / "backend_response.c"), str(native / "test_backend_response.c"),
                            "-o", str(executable)], check=True, capture_output=True)
            result = subprocess.run([str(executable)], check=True, capture_output=True, text=True)
            self.assertIn("projection contracts passed", result.stdout)

    def test_real_worker_scope_cancellation_ownership_and_restore(self):
        prefix = os.environ.get("WINEPREFIX", "")
        if not prefix.startswith("/tmp/szero-"):
            raise RuntimeError("Use disposable /tmp/szero-* Wine prefix, never game prefix")
        native = Path(__file__).resolve().parent / "native"
        common = [native / "backend_response.c", *(native / "vendor/minhook/src" / name for name in
                  ("buffer.c", "hook.c", "trampoline.c", "hde/hde64.c"))]
        received = []
        ident = uuid.uuid4().hex

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                line = self.rfile.readline(160).decode("ascii")
                if not line:  # Cancellation can close after connect, before send.
                    return
                received.append(line)
                parts = line.rstrip("\n").split(" ")
                if parts == ["SERVICE2", ident, "/user/get_player_card.php",
                             "szlan:0123456789abcdef0123456789abcdef"]:
                    self.wfile.write(b"2\n{}")
                    return
                if len(parts) != 3 or parts[:2] != ["SERVICE1", ident]:
                    self.wfile.write(b"ERR\n")
                    return
                path = parts[2]
                if path == "/user/check_transaction.php":
                    self.wfile.write(b"ERR\n")
                elif path == "/system/get_notice.php":
                    time.sleep(.4)
                    try:
                        self.wfile.write(b"2\n{}")
                    except OSError:
                        pass
                elif path == "/shop_banner/get_list.php":
                    self.wfile.write(b"7\n{broken")
                else:
                    self.wfile.write(b"2\n{}")

        class Server(socketserver.ThreadingTCPServer):
            daemon_threads = True

        with tempfile.TemporaryDirectory(prefix="szero-backend-adapter-") as folder:
            folder = Path(folder)
            exe = folder / "adapter.exe"
            base = ["x86_64-w64-mingw32-gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                    "-static-libgcc", "-Wl,--no-insert-timestamp"]
            subprocess.run([*base, "-municode", str(native / "test_backend_adapter.c"),
                            *(str(p) for p in common), "-o", str(exe), "-lbcrypt", "-lws2_32"],
                           check=True, capture_output=True)
            with Server(("127.0.0.1", 0), Handler) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                endpoint = folder / f"lan_runtime_{ident}.service.endpoint"
                endpoint.write_text(f"{server.server_address[1]}\n", encoding="ascii")
                try:
                    result = subprocess.run(["wine", str(exe), ident, "normal"], capture_output=True,
                                            text=True, env=dict(os.environ, WINEDEBUG="-all", SZERO_LAN_MOD_LOGGING="1"), timeout=25)
                finally:
                    server.shutdown()
                    thread.join()
            log = folder / f"native_backend_adapter_{ident}.jsonl"
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr +
                             (log.read_text() if log.exists() else "no log"))
            self.assertIn("contracts passed", result.stdout)
            records = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(records[0]["event"], "ready")
            self.assertEqual(records[0]["schema"], 3)
            self.assertEqual(records[0]["revision"], "ranked-result1")
            self.assertRegex(records[0]["time_utc"], r"^\d{4}-\d\d-\d\dT.*Z$")
            self.assertTrue(records[0]["card_route"])
            self.assertRegex(records[0]["helper_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(records[0]["helper_sha256"], hashlib.sha256(exe.read_bytes()).hexdigest())
            refusals = {row["reason"] for row in records if row["event"] == "refusal"}
            self.assertIn("card_local_identity_mismatch", refusals)
            self.assertIn("card_local_context_unavailable", refusals)
            self.assertIn("request_scope", refusals)
            self.assertIn("battle_start_foreign_or_unbound_service", refusals)
            self.assertIn("battle_report_invalid", refusals)
            self.assertNotIn("unsupported_rank_update_route", refusals)
            self.assertNotIn("secret-never-forwarded", json.dumps(records))
            self.assertNotIn("76561198099999999", json.dumps(records))
            self.assertEqual(records[-1], {"event": "stopped", "restored": True})
            self.assertIn(len(received), (5, 6))
            simple = [line for line in received if line.startswith("SERVICE1 ")]
            self.assertTrue(all(line.startswith(f"SERVICE1 {ident} /") and line.endswith(".php\n")
                                for line in simple))
            self.assertEqual([line for line in received if line.startswith("SERVICE2 ")],
                             [f"SERVICE2 {ident} /user/get_player_card.php szlan:0123456789abcdef0123456789abcdef\n"])
            self.assertNotIn("secret-never-forwarded", "".join(received))
            self.assertNotIn("76561198099999999", "".join(received))
            self.assertNotIn("unknown.php", "".join(received))
            self.assertNotIn("update_player_rank.php", "".join(received))
            endpoint.write_text("12345\n", encoding="ascii")
            result = subprocess.run(["wine", str(exe), ident, "authenticated"], capture_output=True,
                                    text=True, env=dict(os.environ, WINEDEBUG="-all", SZERO_LAN_MOD_LOGGING="1"), timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("remains unpatched for diagnostics", result.stdout)
            dll = folder / "backend_adapter.dll"
            subprocess.run([*base, "-shared", str(native / "backend_adapter.c"),
                            *(str(p) for p in common), "-o", str(dll), "-lbcrypt", "-lws2_32"],
                           check=True, capture_output=True)
            production_id = uuid.uuid4().hex
            windows_dll = "Z:" + str(dll).replace("/", "\\")
            result = subprocess.run(["wine", str(exe), production_id, "production", windows_dll],
                                    capture_output=True, text=True, env=dict(os.environ, WINEDEBUG="-all", SZERO_LAN_MOD_LOGGING="1"), timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual([json.loads(line) for line in
                              (folder / f"native_backend_adapter_{production_id}.jsonl").read_text().splitlines()],
                             [{"event": "refused"}])


if __name__ == "__main__":
    unittest.main()
