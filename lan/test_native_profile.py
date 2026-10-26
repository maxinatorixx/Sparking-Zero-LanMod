"""Recovered follow-ups persist own data and never award a match result."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import unittest
from account_store import AccountStore
from backend_services import LanBackendServices
from native_profile import RANK_ROUTE, PROFICIENCY_ROUTE, validate_profile_update
import test_backend_bridge as backend_fixture


class NativeProfileTests(unittest.TestCase):
    def test_typed_boundaries_and_authority_fields(self):
        for value in (-128,0,127):
            self.assertEqual(validate_profile_update(RANK_ROUTE,{'player_rank':value}),{'player_rank':value})
        invalid=[{}, {'player_rank':True},{'player_rank':128},{'player_rank':-129},
                 {'player_rank':1.0},{'player_rank':1,'account_id':2}]
        for body in invalid:
            with self.assertRaises(ValueError):validate_profile_update(RANK_ROUTE,body)
        for char in ('', 'bad\x00', '\ud800', 'x'*129):
            with self.assertRaises((ValueError,UnicodeError)):
                validate_profile_update(PROFICIENCY_ROUTE,{'character_id':char,'character_proficiency_rank':1})

    def test_persistent_login_card_freshness_account_isolation_no_elo_write(self):
        with tempfile.TemporaryDirectory() as directory:
            database=Path(directory)/'state.db'
            store=AccountStore.for_sqlite(database,'aa')
            a=store.register('alpha','aa','aa')['profile'];b=store.register('bravo','bb')['profile']
            service=LanBackendServices(native_store=store)
            peer='a'*32;other='b'*32
            for ident,profile in ((peer,a),(other,b)):
                service.bind_account(ident,profile);service.request(ident,profile['display_name'],'/user/login.php',{})
            self.assertEqual(service.request(peer,'alpha',RANK_ROUTE,{'player_rank':7}),{'res':0})
            self.assertEqual(service.request(peer,'alpha',PROFICIENCY_ROUTE,{'character_id':'Goku','character_proficiency_rank':4}),{'res':0})
            card=service.request(peer,'alpha','/user/login.php',{})['player_card']
            self.assertEqual((card['player_rank'],card['character_id'],card['character_proficiency_rank']),(7,'Goku',4))
            self.assertEqual(service.request(other,'bravo','/user/login.php',{})['player_card']['player_rank'],0)
            service.disconnect(peer)
            reopened=AccountStore.for_sqlite(database,'aa')
            fresh=LanBackendServices(native_store=reopened);fresh.bind_account(peer,a)
            self.assertEqual(fresh.request(peer,'alpha','/user/login.php',{})['player_card'],card)
            self.assertTrue(all(row['games']==0 for row in reopened.authenticate(store.login('alpha','aa')['token'])['ranks']))
            store.close();reopened.close()

    def test_failure_before_commit_never_acknowledged_and_guest_is_ephemeral(self):
        class FailingStore:
            def get_native_state(self,account_id):return {}
            def put_native_state(self,account_id,state):raise ValueError('DB failure')
        service=LanBackendServices(native_store=FailingStore());peer='a'*32
        service.bind_account(peer,{'id':1});service.request(peer,'A','/user/login.php',{})
        with self.assertRaises(ValueError):service.request(peer,'A',RANK_ROUTE,{'player_rank':2})
        guest=LanBackendServices();guest.request(peer,'A','/user/login.php',{})
        guest.request(peer,'A',RANK_ROUTE,{'player_rank':3})
        self.assertEqual(guest.request(peer,'A','/user/login.php',{})['player_card']['player_rank'],3)
        guest.disconnect(peer)
        self.assertEqual(guest.request(peer,'A','/user/login.php',{})['player_card']['player_rank'],0)


class NativeProfileBridgeTests(unittest.TestCase):
    setUp=backend_fixture.BackendBridgeTests.setUp
    tearDown=backend_fixture.BackendBridgeTests.tearDown
    bridge=backend_fixture.BackendBridgeTests.bridge
    call=backend_fixture.BackendBridgeTests.call

    @unittest.skipUnless(shutil.which('wine') and shutil.which('x86_64-w64-mingw32-gcc'),'requires MinGW/Wine')
    def test_compiled_profile_updates_strip_auth_and_refresh_self_card(self):
        self.assertTrue(os.environ.get('WINEPREFIX','').startswith('/tmp/szero-'))
        bridge,_,_=self.bridge('a')
        native=Path(__file__).resolve().parent/'native';exe=bridge.runtime.parent/'profile.exe'
        subprocess.run(['x86_64-w64-mingw32-gcc','-std=c11','-O2','-Wall','-Wextra','-Werror',
            '-static-libgcc','-Wl,--no-insert-timestamp','-municode',str(native/'test_backend_adapter.c'),
            str(native/'backend_response.c'),*(str(native/'vendor/minhook/src'/name) for name in
            ('buffer.c','hook.c','trampoline.c','hde/hde64.c')),'-o',str(exe),'-lbcrypt','-lws2_32'],check=True,capture_output=True)
        result=subprocess.run(['wine',str(exe),bridge.backend_rpc.instance,'profile'],capture_output=True,text=True,timeout=25,
                              env=dict(os.environ,WINEDEBUG='-all'))
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('profile updates and native ownership passed',result.stdout)
        bridge.backend_rpc.endpoint.write_text(str(bridge.backend_rpc.listener.getsockname()[1])+'\n')
        log=bridge.runtime.parent/f'native_backend_adapter_{bridge.backend_rpc.instance}.jsonl'
        if log.exists():log.unlink()
        quiet=subprocess.run(['wine',str(exe),bridge.backend_rpc.instance,'profilequiet'],capture_output=True,text=True,timeout=25,
                             env=dict(os.environ,WINEDEBUG='-all'))
        self.assertEqual(quiet.returncode,0,quiet.stdout+quiet.stderr)
        self.assertFalse(log.exists(),'disabled backend logging must create no file while updates still succeed')
        bridge.backend_rpc.endpoint.write_text(str(bridge.backend_rpc.listener.getsockname()[1])+'\n')
        card=self.call(bridge,'/user/get_player_card.php','self')['player_card']
        self.assertEqual((card['player_rank'],card['character_id'],card['character_proficiency_rank']),(7,'Goku',4))
        self.assertNotIn('NEVER-FORWARD',repr(self.server.backend_services._native_states))
        for body in ({'player_rank':True},{'player_rank':7,'account_id':1}):
            with socket.create_connection(('127.0.0.1',int(bridge.backend_rpc.endpoint.read_text())),2) as connection:
                frame=json.dumps(body,separators=(',',':')).encode().hex()
                connection.sendall(f'SERVICE4 {bridge.backend_rpc.instance} {RANK_ROUTE} {frame}\n'.encode())
                self.assertEqual(connection.recv(16),b'ERR\n')
