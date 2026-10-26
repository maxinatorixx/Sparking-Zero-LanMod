"""Opt-in compiled Win64 IPC -> real bridge/server. Does not execute the game.

Build native/test_native_search_ipc.c with MinGW and set
SZERO_NATIVE_IPC_EXE to its absolute Unix path. WINEPREFIX must select a
disposable test prefix, never the user's game prefix. Requires loopback access.
"""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest

from ingame_client import GameBridge
from szero_lan import GameServer


def until(predicate):
    end = time.monotonic() + 5
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return False


@unittest.skipUnless(os.environ.get("SZERO_NATIVE_IPC_EXE"), "compiled Win64 IPC fixture not selected")
class CompiledNativeIPCTests(unittest.TestCase):
    def test_native_report_logging_gate(self):
        with tempfile.TemporaryDirectory(prefix="szero-native-logcheck-") as directory:
            report=Path(directory)/'native.json'
            windows='Z:'+str(report).replace('/','\\')
            result=subprocess.run(['wine',os.environ['SZERO_NATIVE_IPC_EXE'],'logcheck',windows],
                                  capture_output=True,text=True,timeout=15,env=dict(os.environ,WINEDEBUG='-all'))
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('Native report logging gate passed',result.stdout)
            self.assertFalse(report.exists())

    def test_production_socket_primitives_through_bridge(self):
        self.assertTrue(os.environ.get("WINEPREFIX"), "set a disposable Wine prefix explicitly")
        loop = asyncio.new_event_loop()
        started = threading.Event()
        servers, failures = [], []

        def server_main():
            asyncio.set_event_loop(loop)
            try:
                servers.append(loop.run_until_complete(GameServer("127.0.0.1", 0).start()))
            except BaseException as exc:
                failures.append(exc)
            started.set()
            if servers:
                loop.run_forever()
            loop.close()

        server_thread = threading.Thread(target=server_main, daemon=True)
        server_thread.start()
        self.assertTrue(started.wait(5))
        if failures:
            raise failures[0]
        server = servers[0]
        observed = []
        original_handle = server.native_search.handle

        def record_request(owner, request):
            observed.append(json.loads(json.dumps(request)))
            return original_handle(owner, request)

        server.native_search.handle = record_request
        try:
            for mode in ("normal", "crlf", "compound", "disconnect", "reject",
                         "tail", "overflow", "nul", "malformed", "worker_normal",
                         "worker_compound", "worker_reject"):
                with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                    observed.clear()
                    root = Path(directory)
                    (root / "SzeroLAN.json").write_text(json.dumps({"server_host": "127.0.0.1",
                        "server_port": server.port, "name": "Compiled fixture", "native_search": True}))
                    instance = "b" * 32
                    bridge = GameBridge(root, root / ("lan_runtime_" + instance + ".lua"))
                    stop = threading.Event()
                    thread = threading.Thread(target=bridge.run, args=(stop,), daemon=True)
                    thread.start()
                    try:
                        self.assertTrue(until(lambda: bridge.native_capability))
                        # Windows writers may use CRLF. Production C must accept this.
                        endpoint = bridge.native_rpc.endpoint
                        if mode == "crlf":
                            endpoint.write_bytes(endpoint.read_bytes().replace(b"\n", b"\r\n"))
                        elif mode in ("tail", "worker_reject"):
                            endpoint.write_bytes(endpoint.read_bytes() + b"extra")
                        elif mode == "overflow":
                            endpoint.write_bytes(("SZERO_NATIVE_ENDPOINT_V1 999999 " + instance + "\n").encode())
                        elif mode == "nul":
                            endpoint.write_bytes(endpoint.read_bytes() + b"\0")
                        elif mode == "malformed":
                            endpoint.write_bytes(b"unrecognized file\n")
                        token = "c" * 32 if mode == "reject" else instance
                        reject = mode in ("reject", "tail", "overflow", "nul", "malformed")
                        windows_path = "Z:" + str(endpoint).replace("/", "\\")
                        result = subprocess.run(["wine", os.environ["SZERO_NATIVE_IPC_EXE"],
                            windows_path, token, "reject" if reject else mode],
                            capture_output=True, text=True, timeout=30)
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        if not reject:
                            self.assertIn("123 0 -5", result.stdout)
                        self.assertTrue(until(lambda: not server.native_search.pending))
                        begins = [item for item in observed if item["op"] == "begin"]
                        if reject or mode == "worker_reject":
                            self.assertEqual(begins, [])
                        else:
                            self.assertEqual(len(begins), 1)
                            query = begins[0]["query"]
                            expected = {"key": "123", "comparison": 0, "value": -5}
                            self.assertEqual(query["filters"], [expected])
                            pairs = [{"first": expected, "second": expected}]
                            self.assertEqual(query["compound_filters"],
                                             pairs if mode.endswith("compound") else [])
                        self.assertFalse(server.matches)
                    finally:
                        stop.set()
                        thread.join(5)
                        self.assertFalse(thread.is_alive())
        finally:
            asyncio.run_coroutine_threadsafe(server.close(), loop).result(5)
            loop.call_soon_threadsafe(loop.stop)
            server_thread.join(5)
            self.assertFalse(server_thread.is_alive())


if __name__ == "__main__":
    unittest.main()
