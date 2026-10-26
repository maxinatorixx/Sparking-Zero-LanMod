import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest

from backend_rpc import BackendServiceRPC


class BackendRPCTests(unittest.TestCase):
    def test_instance_capability_identity_response_and_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            instance = "a"*32
            rpc = BackendServiceRPC(Path(directory)/("lan_runtime_"+instance+".lua"), instance)
            port = int(rpc.endpoint.read_text())
            def call(line):
                with socket.create_connection(("127.0.0.1", port), 2) as connection:
                    connection.settimeout(7)
                    connection.sendall(line)
                    stream = connection.makefile("rb")
                    header = stream.readline(32)
                    return header, stream.read(int(header)) if header != b"ERR\n" else b""
            try:
                request = f"SERVICE1 {instance} /user/login.php\n".encode()
                self.assertEqual(call(request)[0], b"ERR\n")
                self.assertTrue(rpc.bind("b"*32, {"lan_backend_services": 1}))
                self.assertEqual(call(request.replace(b"a"*32, b"c"*32))[0], b"ERR\n")
                self.assertEqual(call(request.replace(b"/user/login.php", b"/unknown.php"))[0], b"ERR\n")
                result = []
                thread = threading.Thread(target=lambda: result.append(call(request)))
                thread.start()
                deadline = time.monotonic()+2
                commands = []
                while not commands and time.monotonic() < deadline:
                    commands = list(rpc.drain())
                    time.sleep(.01)
                self.assertEqual(len(commands), 1)
                command = commands[0]
                self.assertEqual(command["body"], {})
                rpc.publish(dict(request_id="stale", state="ok", body={"wrong": 1}))
                rpc.publish(dict(request_id=command["request_id"], state="ok", body={"result": "LAN"}))
                thread.join(3)
                self.assertFalse(thread.is_alive())
                self.assertEqual(json.loads(result[0][1]), {"result": "LAN"})
                rpc.invalidate()
                self.assertFalse(rpc.bind("d"*32, {"lan_backend_services": 1}))
                self.assertEqual(call(request)[0], b"ERR\n")
            finally:
                rpc.close()
            self.assertFalse(rpc.endpoint.exists())
            self.assertFalse(rpc.worker.is_alive())

    def test_boolean_capability_is_not_version(self):
        with tempfile.TemporaryDirectory() as directory:
            rpc = BackendServiceRPC(Path(directory)/"runtime.lua", "a"*32)
            try:
                self.assertFalse(rpc.bind("b"*32, {"lan_backend_services": True}))
                self.assertFalse(rpc.ready.is_set())
            finally:
                rpc.close()

    def test_close_interrupts_accepted_partial_request(self):
        with tempfile.TemporaryDirectory() as directory:
            rpc = BackendServiceRPC(Path(directory)/"runtime.lua", "a"*32)
            with socket.create_connection(("127.0.0.1", int(rpc.endpoint.read_text())), 2) as connection:
                connection.sendall(b"S")
                deadline = time.monotonic()+2
                while rpc.active is None and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertIsNotNone(rpc.active)
                start = time.monotonic()
                rpc.close()
                self.assertLess(time.monotonic()-start, 1)
                self.assertFalse(rpc.worker.is_alive())
                try:
                    self.assertEqual(connection.recv(1), b"")
                except ConnectionResetError:
                    pass  # Closing an accepted socket with unread bytes may send RST.

    def test_typed_finish_and_peer_start_frames_keep_only_approved_values(self):
        snapshot={'rank_title':'LAN','rank_point':1234,'prev_need_point':1000,'next_need_point':2000,
            'win_streak':4,'win_streak_r_bits':0x3f000000,'app_multiplayer_mode':0,
            'battle_type':1,'pvp_extra_type':0,'rank_range':-1,'rank':3}
        with tempfile.TemporaryDirectory() as directory:
            ident='a'*32;code='c'*32
            rpc=BackendServiceRPC(Path(directory)/'runtime.lua',ident)
            try:
                self.assertTrue(rpc.bind('b'*32,{'lan_backend_services':1}))
                def call(line):
                    with socket.create_connection(('127.0.0.1',rpc.listener.getsockname()[1]),2) as connection:
                        connection.settimeout(7);connection.sendall(line)
                        with connection.makefile('rb') as stream:
                            header=stream.readline(16)
                            return header,stream.read(int(header)) if header!=b'ERR\n' else b''
                prefix=f'SERVICE3 {ident} /pvp/end_battle_player1.php {code} 1 '
                encoded=json.dumps(snapshot,separators=(',',':')).encode().hex()
                valid=(prefix+encoded+'\n').encode()
                for line,body in ((f'SERVICE3 {ident} /pvp/start_battle_player2.php {code} - -\n'.encode(),{'match_code':code}),
                                  (valid,{'match_code':code,'outcome':1,'rank_snapshot':snapshot}),
                                  (f'SERVICE5 {ident} /pvp/end_battle_player2.php {code} 1 3 2 {encoded}\n'.encode(),
                                   {'match_code':code,'outcome':1,'native_category':3,'native_result':2,'rank_snapshot':snapshot})):
                    result=[];thread=threading.Thread(target=lambda:result.append(call(line)));thread.start()
                    deadline=time.monotonic()+2;commands=[]
                    while not commands and time.monotonic()<deadline:
                        commands=list(rpc.drain());time.sleep(.01)
                    self.assertEqual(len(commands),1);self.assertEqual(commands[0]['body'],body)
                    rpc.publish({'request_id':commands[0]['request_id'],'state':'ok','body':{'res':0}})
                    thread.join(3);self.assertFalse(thread.is_alive());self.assertEqual(json.loads(result[0][1]),{'res':0})
                bad_snapshot=dict(snapshot,account_id=7)
                duplicate=json.dumps(snapshot)[:-1]+',"rank":4}'
                bad_lines=[f'SERVICE1 {ident} /pvp/start_battle_player2.php\n'.encode(),
                    valid.replace(b' 1 ',b' true '),valid.replace(code.encode(),b'not-issued'),
                    (prefix+json.dumps(bad_snapshot).encode().hex()+'\n').encode(),
                    (prefix+duplicate.encode().hex()+'\n').encode(),
                    (prefix+(b'['*1023).hex()+'\n').encode(),
                    f'SERVICE3 {ident} /pvp/start_battle_player2.php {code} 1 {encoded}\n'.encode()]
                typed=f'SERVICE5 {ident} /pvp/end_battle_player2.php {code} 1 3 2 {encoded}\n'.encode()
                bad_lines += [typed.replace(b' 1 3 2 ',value) for value in (b' 1 4 2 ',b' 1 3 7 ',b' true 3 2 ',b' 1 3 true ')]
                for line in bad_lines:
                    self.assertEqual(call(line)[0],b'ERR\n')
                self.assertTrue(rpc.worker.is_alive());self.assertTrue(rpc.ready.is_set());self.assertFalse(list(rpc.drain()))
            finally:
                rpc.close()
