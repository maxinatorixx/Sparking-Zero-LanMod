"""Typed own-result consensus -> persistent LAN Elo, never completion outcome."""
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from account_store import AccountStore
import test_battle_end as battle_fixture


class RankedReportStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'ranked.db'
        self.store=AccountStore.for_sqlite(self.path,'aa')
        self.a=self.store.register('alpha','aa','aa')['profile']['id']
        self.b=self.store.register('bravo','bb')['profile']['id']
        self.code='e'*32

    def tearDown(self):
        self.store.close();self.temp.cleanup()

    def report(self, role, result, category=1, code=None):
        return self.store.record_ranked_report(code or self.code,self.a,self.b,role,category,result)

    def ranks(self, mode='single'):
        return {r['id']:r for r in self.store.rankings(mode)}

    def test_pending_ack_consensus_and_replay_survive_reopen(self):
        self.assertEqual(self.report(1,2),'pending')
        self.assertTrue(all(r['games']==0 for r in self.ranks().values()))
        self.store.close();self.store=AccountStore.for_sqlite(self.path,'aa')
        self.assertEqual(self.report(0,1),'recorded')
        self.assertEqual(self.ranks()[self.a]['rating'],1016)
        self.assertEqual(self.ranks()[self.b]['rating'],984)
        for role,result in ((0,1),(1,2)):
            self.assertEqual(self.report(role,result),'recorded')
        self.assertEqual(self.ranks()[self.a]['games'],1)
        self.assertEqual(self.ranks()[self.a]['wins'],1)
        self.assertEqual(self.ranks()[self.b]['losses'],1)
        with self.assertRaises(ValueError):self.report(0,2)
        self.assertEqual(self.ranks()[self.a]['games'],1)

    def test_no_rating_for_unknown_conflicting_modes_results_or_selfplay(self):
        cases=[((0,1),(1,1)),((0,1),(1,2,2)),((0,0),(1,2)),((0,3),(1,1))]
        for index,pair in enumerate(cases):
            code=f'{index:032x}'
            for args in pair:self.report(*args,code=code)
        self.assertEqual(self.store.record_ranked_report('f'*32,self.a,self.a,0,1,1),'self_play')
        self.assertEqual(self.store.record_ranked_report('f'*32,self.a,self.a,1,1,2),'self_play')
        self.assertTrue(all(r['games']==0 for r in self.ranks().values()))
        self.assertEqual(self.report(0,0),'pending')
        self.assertEqual(self.report(1,2),'pending')
        self.assertEqual(self.report(0,1),'recorded')
        self.assertEqual(self.ranks()[self.a]['games'],1)

    def test_draw_and_per_mode_isolation(self):
        self.report(0,3,category=2);self.report(1,3,category=2)
        dp=self.ranks('dp')
        self.assertEqual((dp[self.a]['draws'],dp[self.a]['rating']),(1,1000))
        self.report(0,2,category=3,code='d'*32);self.report(1,1,category=3,code='d'*32)
        self.assertEqual(self.ranks('team')[self.b]['rating'],1016)
        self.assertTrue(all(r['games']==0 for r in self.ranks().values()))

    def test_transaction_failure_rolls_back_both_second_report_and_elo(self):
        self.report(0,1)
        execute=self.store._execute
        def fail(cursor,sql,params=()):
            if sql.startswith('INSERT INTO rank_events'):raise RuntimeError('fixture commit failure')
            return execute(cursor,sql,params)
        with patch.object(self.store,'_execute',fail),self.assertRaises(RuntimeError):self.report(1,2)
        self.assertTrue(all(r['games']==0 for r in self.ranks().values()))
        self.assertEqual(self.report(1,2),'recorded')
        self.assertTrue(all(r['games']==1 for r in self.ranks().values()))

    def test_parallel_connections_commit_one_event(self):
        errors=[]
        def send(role,result):
            store=AccountStore.for_sqlite(self.path,'aa')
            try:
                for _ in range(4):store.record_ranked_report(self.code,self.a,self.b,role,1,result)
            except BaseException as exc:errors.append(exc)
            finally:store.close()
        threads=[threading.Thread(target=send,args=pair) for pair in ((0,1),(1,2))]
        for thread in threads:thread.start()
        for thread in threads:thread.join()
        self.assertFalse(errors)
        self.assertTrue(all(r['games']==1 for r in self.ranks().values()))

    def test_strict_fields_ownership_and_canonical_legacy_scores(self):
        for role,category,result in ((True,1,1),(0,True,1),(0,1,True),(0,1,4),(2,1,1)):
            with self.assertRaises(ValueError):self.store.record_ranked_report(self.code,self.a,self.b,role,category,result)
        self.report(0,1)
        with self.assertRaises(ValueError):self.store.record_ranked_report(self.code,self.b,self.a,1,1,2)
        self.assertTrue(self.store.record_result('canonical','single',self.a,self.b,1))
        self.assertFalse(self.store.record_result('canonical','single',self.a,self.b,1.0))


class RankedEndIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=AccountStore.for_sqlite(Path(self.temp.name)/'db','aa')
        self.a=self.store.register('alpha','aa','aa')['profile']['id']
        self.b=self.store.register('bravo','bb')['profile']['id']
        self.fixture=battle_fixture.BattleEndTests();self.fixture.setUp()
        self.service=self.fixture.service;self.service.native_store=self.store
        _,self.code=self.fixture.both_start()

    def tearDown(self):self.store.close();self.temp.cleanup()

    def end(self, owner, route, result, category=1, code=None):
        body=battle_fixture.end_body(code or self.code,1)
        body.update(native_category=category,native_result=result)
        return self.service.request(owner,self.fixture.server.peers[owner].name,route,body)

    def test_both_completion_outcome_one_but_native_win_loss_controls_scores(self):
        self.assertEqual(self.end(battle_fixture.A,battle_fixture.E1,2)['res'],0)
        self.assertTrue(all(r['games']==0 for r in self.store.rankings()))
        self.fixture.operation(battle_fixture.A,'leave')
        self.assertEqual(self.end(battle_fixture.B,battle_fixture.E2,1)['res'],0)
        ranks={r['id']:r for r in self.store.rankings()}
        self.assertEqual((ranks[self.a]['rating'],ranks[self.b]['rating']),(984,1016))
        self.assertEqual(self.service._battle_history[self.code]['rating_state'],'recorded')
        fresh=self.service.request(battle_fixture.A,'Alpha','/user/login.php',{})
        single=next(r for r in fresh['lan_rankings'] if r['mode']=='single')
        self.assertEqual((single['losses'],single['games']),(1,1))
        # Existing native rank values are preserved; never overwrite them with
        # invented mappings from Elo into official title/threshold fields.
        self.assertEqual(self.end(battle_fixture.A,battle_fixture.E1,2)['battle_result']['rank_match_info']['rank_point'],3456)
        self.assertTrue(all(r['games']==1 for r in self.store.rankings()))

    def test_legacy_unknown_conflict_and_db_failure_are_not_cached_as_scores(self):
        original=battle_fixture.end_body(self.code,1)
        self.service.request(battle_fixture.A,'Alpha',battle_fixture.E1,original)
        self.end(battle_fixture.B,battle_fixture.E2,1)
        self.assertTrue(all(r['games']==0 for r in self.store.rankings()))
        # A later own typed report may complete an originally legacy receipt.
        self.end(battle_fixture.A,battle_fixture.E1,2)
        self.assertTrue(all(r['games']==1 for r in self.store.rankings()))
        with self.assertRaises(ValueError):self.end(battle_fixture.A,battle_fixture.E1,1)

    def test_invalid_typed_metadata_cannot_reach_durable_result_writer(self):
        for category,result in ((True,1),(1,True),(0,1),(4,1),(1,4),(1,1.0)):
            body=battle_fixture.end_body(self.code,1)
            body.update(native_category=category,native_result=result)
            with self.assertRaises(ValueError):
                self.service.request(battle_fixture.A,'Alpha',battle_fixture.E1,body)
        self.assertFalse(self.service._battle_history[self.code]['typed_reports'])
        self.assertTrue(all(row['games']==0 for row in self.store.rankings()))

    def test_store_failure_leaves_retryable_second_end(self):
        self.end(battle_fixture.A,battle_fixture.E1,1)
        with patch.object(self.store,'record_ranked_report',side_effect=RuntimeError('db unavailable')):
            with self.assertRaises(RuntimeError):self.end(battle_fixture.B,battle_fixture.E2,2)
        receipt=self.service._battle_history[self.code]
        self.assertNotIn(battle_fixture.B,receipt['reports'])
        self.assertNotIn(battle_fixture.B,receipt['typed_reports'])
        self.assertEqual(self.end(battle_fixture.B,battle_fixture.E2,2)['res'],0)
        self.assertTrue(all(r['games']==1 for r in self.store.rankings()))


class RankedReportTCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_account_tcp_native_room_and_late_typed_result_commit(self):
        import asyncio
        import json
        from szero_lan import GameServer
        import test_battle_start as fixture
        with tempfile.TemporaryDirectory() as directory:
            store=AccountStore.for_sqlite(Path(directory)/'accounts.db','aa')
            tokens=[store.register('alpha','aa','aa')['token'],store.register('bravo','bb')['token']]
            server=await GameServer('127.0.0.1',0,store).start()
            streams=[];serial=0
            now=[0];server.elo_policy.match.clock=lambda:now[0]
            with store._tx() as cursor:store._execute(cursor,"UPDATE rankings SET rating=1901 WHERE account_id=? AND mode=?",(1,'single'))
            async def send(index,payload,event):
                reader,writer=streams[index]
                writer.write((json.dumps(payload)+'\n').encode());await writer.drain()
                while True:
                    line=await asyncio.wait_for(reader.readline(),3)
                    self.assertTrue(line)
                    reply=json.loads(line)
                    if reply.get('event')==event:return reply
            async def service(index,path,body):
                nonlocal serial
                serial+=1
                return await send(index,{'op':'lan_backend_service','request':{
                    'request_id':f'service-{serial}','path':path,'body':body}},'lan_backend_service')
            try:
                owners=[]
                for index,token in enumerate(tokens):
                    streams.append(await asyncio.open_connection('127.0.0.1',server.port))
                    welcome=await send(index,{'op':'hello','version':2,'account_token':token},'welcome')
                    owners.append(welcome['client_id'])
                    self.assertEqual((await service(index,'/user/login.php',{}))['state'],'ok')
                native=dict(fixture.data('first'),compatibility=20002)
                created=fixture.translate_request(fixture.request('create',native_data=native,
                    attributes={str(i):n for i,n in enumerate(native['numeric'])}),owners[0],protocol=5)
                room=await send(0,{'op':'native_session','request':created},'native_session_result')
                from test_native_sessions_v2 import query
                search=fixture.translate_request(fixture.request('search',query=query(compatibility=20002),
                    default_normalize=False,materialization_profile=2,limit=1),owners[1],protocol=5)
                self.assertEqual((await send(1,{'op':'native_session','request':search},'native_session_result'))['sessions'],[])
                now[0]=120
                found=await send(1,{'op':'native_session','request':search},'native_session_result')
                self.assertEqual([r['session_id'] for r in found['sessions']],[room['session']['session_id']])
                join=fixture.translate_request(fixture.request('join',session_id=room['session']['session_id'],
                    native_member=fixture.member('second')),owners[1],protocol=5)
                await send(1,{'op':'native_session','request':join},'native_session_result')
                first=await service(0,battle_fixture.P1,{})
                code=first['body']['match_code']
                self.assertEqual((await service(1,battle_fixture.P2,{'match_code':code}))['state'],'ok')
                a=battle_fixture.end_body(code,1);a.update(native_category=1,native_result=2)
                b=battle_fixture.end_body(code,1);b.update(native_category=1,native_result=1)
                initial=await service(0,battle_fixture.E1,a)
                self.assertEqual(initial['state'],'ok')
                self.assertTrue(all(row['games']==0 for row in store.rankings('single')))
                leave=fixture.translate_request(fixture.request('leave'),owners[0],protocol=5)
                await send(0,{'op':'native_session','request':leave},'native_session_result')
                self.assertEqual((await service(1,battle_fixture.E2,b))['state'],'ok')
                self.assertEqual((await service(0,battle_fixture.E1,a))['body'],initial['body'])
                ranks=store.rankings('single')
                self.assertEqual([(r['display_name'],r['rating']) for r in ranks],[('alpha',1869),('bravo',1032)])
                self.assertTrue(all(row['games']==1 for row in ranks))
                self.assertTrue(all(row['games']==0 for row in store.rankings('dp')))
            finally:
                for _,writer in streams:
                    writer.close();await writer.wait_closed()
                await server.close();store.close()


class NativeRankedStatisticsTests(unittest.TestCase):
    def test_native_ranked_rate_rows_and_no_season_policy(self):
        from backend_services import LanBackendServices
        rankings=[{'mode':'single','games':3,'wins':2,'max_win_streak':2},
                  {'mode':'dp','games':1,'wins':0,'max_win_streak':0},
                  {'mode':'team','games':50,'wins':50,'max_win_streak':50}]
        rows=LanBackendServices.native_statistics(rankings)
        self.assertEqual(len(rows),4)
        for period in (1,2):
            selected=[r for r in rows if r['type']==period and r['session_kind'] in (2,3)]
            self.assertEqual(sum(r['win'] for r in selected)/sum(r['match'] for r in selected)*100,50)
            self.assertEqual({r['session_kind'] for r in selected},{2,3})
            self.assertEqual(next(r for r in selected if r['session_kind']==2)['max_win_streak'],2)
        card=LanBackendServices.player_card({'ranks':rankings})
        self.assertEqual(card['match_result_list'],rows)
        self.assertNotIn('rank_point',rows[0])  # Elo never becomes an invented native threshold.

    def test_streaks_are_persistent_idempotent_and_old_schema_migrates(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'old.db'
            connection=sqlite3.connect(path)
            connection.execute('CREATE TABLE rankings (account_id BIGINT NOT NULL,mode VARCHAR(32) NOT NULL,rating INTEGER NOT NULL DEFAULT 1000,wins INTEGER NOT NULL DEFAULT 0,losses INTEGER NOT NULL DEFAULT 0,draws INTEGER NOT NULL DEFAULT 0,games INTEGER NOT NULL DEFAULT 0,updated_at BIGINT NOT NULL,PRIMARY KEY(account_id,mode))')
            connection.commit();connection.close()
            store=AccountStore.for_sqlite(path,'aa')
            a=store.register('alpha','aa','aa')['profile']['id'];b=store.register('bravo','aa')['profile']['id']
            for index,score in enumerate((1,1,.5)):
                self.assertTrue(store.record_result(f'streak-{index}','single',a,b,score))
                self.assertFalse(store.record_result(f'streak-{index}','single',a,b,score))
            store.close();store=AccountStore.for_sqlite(path,'aa')
            row=next(r for r in store.get_profile(a)['ranks'] if r['mode']=='single')
            self.assertEqual((row['wins'],row['games'],row['win_streak'],row['max_win_streak']),(2,3,0,2))
            store.close()
