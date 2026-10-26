"""Windows one-file GUI and bridge smoke under a disposable Wine prefix."""
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import unittest

import test_native_session_bridge as fixture
from test_lan_identity import CREATE


@unittest.skipUnless(os.getenv("SZERO_WINDOWS_DESKTOP_EXE"), "Windows standalone not selected")
class WindowsStandaloneTests(unittest.TestCase):
    setUp=fixture.NativeSessionBridgeTests.setUp
    tearDown=fixture.NativeSessionBridgeTests.tearDown

    def test_frozen_windows_ui_resources_and_embedded_bridge(self):
        prefix=os.environ.get("SZERO_WINDOWS_TEST_PREFIX","")
        self.assertTrue(prefix.startswith("/tmp/szero-"),"Use a disposable build prefix, never the game prefix")
        environment=dict(os.environ,WINEPREFIX=prefix,WINEDEBUG="-all")
        command=["wine",os.environ["SZERO_WINDOWS_DESKTOP_EXE"]]
        result=subprocess.run([*command,"--self-check","--ui"],env=environment,
                              capture_output=True,text=True,timeout=45)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        folder=Path(self.folder.name)
        (folder/"SzeroLAN.json").write_text(json.dumps({"server_host":"127.0.0.1",
            "server_port":self.server.port,"name":"Windows onefile","native_search":True,"native_session":True}))
        instance="f"*32
        runtime=folder/f"lan_runtime_{instance}.lua"
        def windows(path):
            return "Z:"+str(path).replace("/","\\")
        child=subprocess.Popen([*command,"--bridge","--game-root",windows(folder),"--runtime",windows(runtime),"--watch-parent-stdin"],
            env=environment,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        sock=reader=None
        try:
            endpoint=runtime.with_suffix(".native.endpoint")
            deadline=time.monotonic()+20
            while not endpoint.exists() and time.monotonic()<deadline:
                time.sleep(.05)
            self.assertTrue(endpoint.exists())
            port=int(endpoint.read_text().split()[1])
            while time.monotonic()<deadline:
                sock=socket.create_connection(("127.0.0.1",port),timeout=3)
                reader=sock.makefile("rb")
                sock.sendall(f"HELLO5 {instance}\n".encode())
                if reader.readline().startswith(b"READY5 "):
                    break
                reader.close();sock.close();reader=sock=None
                time.sleep(.05)
            self.assertIsNotNone(reader)
            sock.sendall(CREATE)
            self.assertEqual(reader.readline(),b"RESULT3 1 PREPARED\n")
            self.assertTrue(reader.readline().startswith(b"SESSION4 "))
            sock.sendall(b"ACK3 1\n")
            self.assertEqual(reader.readline(),b"RESULT3 1 COMMITTED\n")
            self.assertEqual(len(self.server.native_sessions.sessions),1)
            service=runtime.with_suffix(".service.endpoint")
            self.assertTrue(fixture.until(service.exists))
            with socket.create_connection(("127.0.0.1",int(service.read_text())),timeout=3) as backend:
                backend.settimeout(7)
                backend.sendall(f"SERVICE1 {instance} /user/login.php\n".encode())
                with backend.makefile("rb") as response:
                    size=int(response.readline())
                    login=json.loads(response.read(size))
                    self.assertEqual(login["res"],0)
                    self.assertTrue(login["session_code"].startswith("szlan-"))
        finally:
            if reader:
                reader.close()
            if sock:
                sock.close()
            child.stdin.close()
            child.stdin=None
            try:
                stdout,stderr=child.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                child.terminate();stdout,stderr=child.communicate(timeout=5)
            self.assertEqual(child.returncode,0,stdout+stderr)
            self.assertTrue(fixture.until(lambda: not self.server.peers))
            self.assertFalse(self.server.native_sessions.sessions)
            self.assertFalse(runtime.with_suffix(".service.endpoint").exists())
