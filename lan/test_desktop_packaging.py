"""Run the actual standalone executable, including its embedded bridge mode."""
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import unittest

import test_native_session_bridge as fixture
from test_lan_identity import CREATE


@unittest.skipUnless(os.getenv("SZERO_DESKTOP_TEST_EXE"), "standalone desktop not selected")
class StandaloneTests(unittest.TestCase):
    setUp=fixture.NativeSessionBridgeTests.setUp
    tearDown=fixture.NativeSessionBridgeTests.tearDown

    def test_actual_onefile_resources_and_background_bridge(self):
        executable=os.environ["SZERO_DESKTOP_TEST_EXE"]
        environment=dict(os.environ, PATH="/no-python-required")
        result=subprocess.run([executable,"--self-check","--ui"],capture_output=True,text=True,timeout=30,env=environment)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(json.loads(result.stdout)["frozen"])
        self.assertTrue(json.loads(result.stdout)["ui"])
        folder=Path(self.folder.name)
        (folder / "SzeroLAN.json").write_text(json.dumps({"server_host":"127.0.0.1",
            "server_port":self.server.port,"name":"Onefile fixture","native_search":True,"native_session":True}))
        instance="e"*32
        runtime=folder / f"lan_runtime_{instance}.lua"
        process=subprocess.Popen([executable,"--bridge","--game-root",str(folder),"--runtime",str(runtime),"--watch-parent-stdin"],
                                 stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=environment)
        try:
            endpoint=runtime.with_suffix(".native.endpoint")
            self.assertTrue(fixture.until(endpoint.exists))
            _,port,_=endpoint.read_text().split()
            with socket.create_connection(("127.0.0.1",int(port)),timeout=3) as sock:
                sock.settimeout(3)
                reader=sock.makefile("rb")
                # Initial binding is asynchronous; wait for its server welcome.
                self.assertTrue(fixture.until(lambda: len(self.server.peers)==1))
                time.sleep(.3)
                sock.sendall(f"HELLO5 {instance}\n".encode())
                self.assertTrue(reader.readline().startswith(b"READY5 "))
                sock.sendall(CREATE)
                self.assertEqual(reader.readline(),b"RESULT3 1 PREPARED\n")
                self.assertTrue(reader.readline().startswith(b"SESSION4 "))
                sock.sendall(b"ACK3 1\n")
                self.assertEqual(reader.readline(),b"RESULT3 1 COMMITTED\n")
                self.assertEqual(len(self.server.native_sessions.sessions),1)
                reader.close()
            service=runtime.with_suffix(".service.endpoint")
            self.assertTrue(fixture.until(service.exists))
            with socket.create_connection(("127.0.0.1",int(service.read_text())),timeout=3) as sock:
                sock.settimeout(7)
                sock.sendall(f"SERVICE1 {instance} /user/login.php\n".encode())
                with sock.makefile("rb") as reader:
                    size=int(reader.readline())
                    login=json.loads(reader.read(size))
                    self.assertEqual(login["res"],0)
                    self.assertTrue(login["session_code"].startswith("szlan-"))
        finally:
            process.stdin.close()
            process.stdin=None
            try:
                stdout,stderr=process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate();stdout,stderr=process.communicate(timeout=5)
            self.assertEqual(process.returncode,0,stdout+stderr)
            self.assertTrue(fixture.until(lambda: not self.server.peers))
            self.assertFalse(self.server.native_sessions.sessions)
            self.assertFalse(runtime.with_suffix(".service.endpoint").exists())
