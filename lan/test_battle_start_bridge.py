"""Compiled route worker -> authenticated bridges -> current room battle code.

Native allocator/projector callbacks are synthetic; this does not run the game.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import unittest
from unittest.mock import patch

from ingame_client import GameBridge
import test_native_session_bridge as fixtures
import test_backend_bridge as backend_fixtures
from test_lan_identity import CREATE


class BattleStartBridgeTests(unittest.TestCase):
    setUp=fixtures.NativeSessionBridgeTests.setUp
    tearDown=fixtures.NativeSessionBridgeTests.tearDown
    def call(self, bridge, path, target=None, body=None):
        if body is None:
            return backend_fixtures.BackendBridgeTests.call(self, bridge, path, target)
        code=body["match_code"]
        suffix=f'{body["outcome"]} '+json.dumps(body["rank_snapshot"],separators=(",",":")).encode().hex() if "outcome" in body else '- -'
        with socket.create_connection(("127.0.0.1",int(bridge.backend_rpc.endpoint.read_text())),2) as connection:
            connection.settimeout(7)
            connection.sendall(f'SERVICE3 {bridge.backend_rpc.instance} {path} {code} {suffix}\n'.encode())
            with connection.makefile('rb') as stream:
                header=stream.readline(16)
                return None if header==b'ERR\n' else json.loads(stream.read(int(header)))

    def logged_bridge(self, identity):
        root=Path(self.folder.name)/identity
        root.mkdir()
        (root/'SzeroLAN.json').write_text(json.dumps({'server_host':'127.0.0.1',
            'server_port':self.server.port,'name':identity,'native_search':True,
            'account_mode':'login'}))
        bridge=GameBridge(root,root/f'lan_runtime_{identity*32}.lua')
        stop=threading.Event()
        thread=threading.Thread(target=bridge.run,args=(stop,),daemon=True)
        with patch.dict(os.environ,SZERO_ARENA_ACCOUNT_TOKEN=identity):
            thread.start()
            self.bridges.append((bridge,stop,thread))
            self.assertTrue(fixtures.until(lambda: bridge.native_session_capability and bridge.backend_rpc.bound))
        sock=socket.create_connection(('127.0.0.1',bridge.native_rpc.port),timeout=5)
        reader=sock.makefile('rb');self.connections.append((sock,reader))
        sock.sendall(f'HELLO5 {identity*32}\n'.encode())
        self.assertTrue(reader.readline().startswith(b'READY5 '))
        self.assertEqual(self.call(bridge,'/user/login.php')['res'],0)
        return bridge,sock,reader

    @unittest.skipUnless(shutil.which('x86_64-w64-mingw32-gcc') and shutil.which('wine'), 'requires MinGW/Wine')
    def test_compiled_both_sides_share_code_without_native_body_forwarding(self):
        self.assertTrue(os.environ.get('WINEPREFIX','').startswith('/tmp/szero-'))
        from account_store import AccountStore
        database=AccountStore.for_sqlite(Path(self.folder.name)/'ratings.db','aa')
        self.addCleanup(database.close)
        profiles={name:database.register('fighter_'+name,'aa','aa')['profile'] for name in ('a','b')}
        class Store:
            def authenticate(_,token): return profiles.get(token)
            def get_native_state(_,account_id): return database.get_native_state(account_id)
            def get_profile(_,account_id): return database.get_profile(account_id)
            def record_ranked_report(_, *args): return database.record_ranked_report(*args)
        self.server.account_store=Store()
        self.server.backend_services.native_store=self.server.account_store
        a,sa,ra=self.logged_bridge('a');b,sb,rb=self.logged_bridge('b')
        sa.sendall(CREATE)
        self.assertEqual(ra.readline(),b'RESULT3 1 PREPARED\n')
        sid=ra.readline().split()[1]
        sa.sendall(b'ACK3 1\n');self.assertEqual(ra.readline(),b'RESULT3 1 COMMITTED\n')
        sb.sendall(b'JOIN3 1 '+sid+b' 63 64 3132372e302e302e313a34303031 0 0 0\n')
        self.assertEqual(rb.readline(),b'RESULT3 1 PREPARED\n');rb.readline()
        sb.sendall(b'ACK3 1\n');self.assertEqual(rb.readline(),b'RESULT3 1 COMMITTED\n')
        self.assertIsNone(self.call(b,'/pvp/start_battle_player2.php'))
        native=Path(__file__).resolve().parent/'native'
        exe=Path(self.folder.name)/'battle-adapter.exe'
        subprocess.run(['x86_64-w64-mingw32-gcc','-std=c11','-O2','-Wall','-Wextra','-Werror',
            '-static-libgcc','-Wl,--no-insert-timestamp','-municode',str(native/'test_backend_adapter.c'),
            str(native/'backend_response.c'),*(str(native/'vendor/minhook/src'/name) for name in
            ('buffer.c','hook.c','trampoline.c','hde/hde64.c')),'-o',str(exe),'-lbcrypt','-lws2_32'],
            check=True,capture_output=True)
        codes=[]
        for bridge,mode,path in ((a,'battle1','/pvp/start_battle_player1.php'),
                                 (b,'battle2','/pvp/start_battle_player2.php')):
            # Helper finds its IPC file beside its EXE, as in the production mod.
            local=bridge.runtime.parent/exe.name;shutil.copyfile(exe,local)
            arguments=['wine',str(local),bridge.backend_rpc.instance,mode]
            if mode=='battle2': arguments.append(codes[0])
            result=subprocess.run(arguments,
                capture_output=True,text=True,timeout=25,env=dict(os.environ,WINEDEBUG='-all'))
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('native response ownership passed',result.stdout)
            # Fixture removes only its IPC endpoint after owned cleanup.
            bridge.backend_rpc.endpoint.write_text(str(bridge.backend_rpc.listener.getsockname()[1])+'\n')
            reply=self.call(bridge,path,body={"match_code":codes[0]} if mode=="battle2" else None)
            self.assertEqual(reply['res'],0);codes.append(reply['match_code'])
        self.assertEqual(codes[0],codes[1])
        self.assertRegex(codes[0],r'^[0-9a-f]{32}$')

        # Original completion ordering: P1 must receive its ACK before P2 reports.
        for bridge,mode in ((a,'end1'),(b,'end2')):
            local=bridge.runtime.parent/exe.name
            report=bridge.runtime.parent/f'native_backend_adapter_{bridge.backend_rpc.instance}.jsonl'
            before=report.read_bytes() if report.exists() else None
            result=subprocess.run(['wine',str(local),bridge.backend_rpc.instance,mode,codes[0]],
                capture_output=True,text=True,timeout=25,
                env=dict(os.environ,WINEDEBUG='-all',SZERO_LAN_MOD_LOGGING='0'))
            self.assertEqual(report.read_bytes() if report.exists() else None,before)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            bridge.backend_rpc.endpoint.write_text(str(bridge.backend_rpc.listener.getsockname()[1])+'\n')
        ranks={row['id']:row for row in database.rankings('single')}
        self.assertEqual((ranks[profiles['a']['id']]['rating'],ranks[profiles['a']['id']]['wins']),(1016,1))
        self.assertEqual((ranks[profiles['b']['id']]['rating'],ranks[profiles['b']['id']]['losses']),(984,1))
        new=self.call(a,'/pvp/start_battle_player1.php')
        self.assertNotEqual(new['match_code'],codes[0])
        self.assertIsNone(self.call(b,'/pvp/start_battle_player2.php',body={'match_code':codes[0]}))
        self.assertEqual(self.call(b,'/pvp/start_battle_player2.php',body={'match_code':new['match_code']}),new)
