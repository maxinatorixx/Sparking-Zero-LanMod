"""Issued-round finish receipts, native leave ordering and rematch fencing.

Outcome values remain raw native reports; no winner/rank interpretation occurs.
"""
import asyncio
import copy
import json
import unittest
from unittest.mock import Mock, patch

import test_battle_start as fixtures

A,B,C=fixtures.A,fixtures.B,fixtures.C
P1,P2=fixtures.P1,fixtures.P2
E1='/pvp/end_battle_player1.php'
E2='/pvp/end_battle_player2.php'
SNAPSHOT={'rank_title':'Sparking Rank A','rank_point':3456,'prev_need_point':3000,
          'next_need_point':4000,'win_streak':9,'win_streak_r_bits':0x3fa00000,
          'app_multiplayer_mode':2,'battle_type':1,'pvp_extra_type':0,
          'rank_range':3,'rank':7}


def end_body(code,outcome,snapshot=None):
    return {'match_code':code,'outcome':outcome,
            'rank_snapshot':copy.deepcopy(SNAPSHOT if snapshot is None else snapshot)}


class BattleEndTests(unittest.TestCase):
    setUp=fixtures.BattleStartTests.setUp
    add_peer=fixtures.BattleStartTests.add_peer
    operation=fixtures.BattleStartTests.operation
    room=fixtures.BattleStartTests.room

    def start(self,owner,route,code=None):
        return self.service.request(owner,self.server.peers[owner].name,route,
                                    {} if route==P1 else {'match_code':code})

    def both_start(self):
        sid=self.room()
        code=self.start(A,P1)['match_code']
        self.assertEqual(self.start(B,P2,code)['match_code'],code)
        return sid,code

    def end(self,owner,route,code,outcome,snapshot=None):
        return self.service.request(owner,self.server.peers[owner].name,route,
                                    end_body(code,outcome,snapshot))

    def test_each_role_acknowledges_immediately_in_either_arrival_order(self):
        for sequence in (((A,E1,1),(B,E2,2)),((B,E2,2),(A,E1,1))):
            self.setUp()
            _,code=self.both_start()
            for index,(owner,route,value) in enumerate(sequence,1):
                self.assertEqual(self.end(owner,route,code,value)['res'],0)
                self.assertEqual(len(self.service._battle_history[code]['reports']),index)
            self.assertEqual(self.service._battle_history[code]['reports'],{A:1,B:2})

    def test_normal_end_requires_both_start_and_cannot_supply_authority(self):
        self.room();code=self.start(A,P1)['match_code']
        with self.assertRaises(ValueError):self.end(A,E1,code,1)
        self.start(B,P2,code)
        for owner,route in ((A,E2),(B,E1)):
            with self.assertRaises(ValueError):self.end(owner,route,code,1)
        bodies=[end_body(code,value) for value in (True,0,3,1.0,'1')]
        bodies += [dict(end_body(code,1),role=0),dict(end_body(code,1),account_id=1),
                   {'match_code':code,'outcome':1},{'outcome':1},
                   {'match_code':code,'result':1},{}]
        for body in bodies:
            with self.subTest(body=body),self.assertRaises(ValueError):
                self.service.request(A,'Alpha',E1,body)
        self.assertFalse(self.service._battle_history[code]['reports'])

    def test_first_native_leave_does_not_erase_other_end_receipt(self):
        _,code=self.both_start()
        self.end(A,E1,code,1)
        self.operation(A,'leave')
        self.assertFalse(self.service._battles)
        self.assertIn(code,self.service._battle_history)
        self.assertEqual(self.end(B,E2,code,2)['res'],0)
        self.assertEqual(self.end(A,E1,code,1)['res'],0)
        self.assertFalse(self.service._battles)

    def test_tcp_disconnect_preserves_connected_peer_cleanup_without_forfeit(self):
        _,code=self.both_start()
        self.service.disconnect(A)
        self.server.peers.pop(A)
        self.assertIn(code,self.service._battle_history)
        self.assertEqual(self.end(B,E2,code,1)['res'],0)
        self.assertEqual(self.service._battle_history[code]['reports'],{B:1})
        with self.assertRaises(ValueError):
            self.service.request(A,'Alpha',E1,end_body(code,2))

    def test_duplicate_response_snapshot_and_conflicting_duplicate(self):
        _,code=self.both_start()
        response=self.end(A,E1,code,1)
        expected=copy.deepcopy(response)
        response['battle_result']['rank_match_info']['rank_point']=999999
        response['battle_result']['match_result_list'].append({'mode':123})
        changed=dict(SNAPSHOT,rank_point=9000,rank=12)
        self.assertEqual(self.end(A,E1,code,1,changed),expected)
        with self.assertRaises(ValueError):self.end(A,E1,code,2)
        self.assertEqual(self.service._battle_history[code]['reports'],{A:1})

    def test_full_result_echoes_only_each_callers_snapshot_and_preserves_stats(self):
        _,code=self.both_start()
        other=dict(SNAPSHOT,rank_title='Opponent own state',rank_point=9876,win_streak=4,rank=12)
        first=self.end(A,E1,code,1)['battle_result']
        second=self.end(B,E2,code,2,other)['battle_result']
        for result,role,point,rank in ((first,1,3456,7),(second,2,9876,12)):
            self.assertEqual(result['match_code'],code)
            self.assertEqual(result['rank_match_info']['rank_point'],point)
            self.assertEqual(result['rank_match_info']['rank'],rank)
            self.assertEqual(result['rank_match_info']['win_streak_r'],1.25)
            self.assertNotIn('win_streak_r_bits',result['rank_match_info'])
            self.assertEqual(result['is_host'],role);self.assertIs(type(result['is_host']),int)
            self.assertEqual(result['match_result_list'],[])
            self.assertEqual(result['battle_rank_point'],0)
            self.assertEqual(result['battle_disconnect_count'],0)
            self.assertEqual(result['matching_penalty_seconds'],0)
            self.assertIs(result['is_disconnect'],False);self.assertIs(result['is_rollback'],False)
            self.assertNotIn('character_result_list',result)
        self.assertEqual(first['rank_match_info']['rank_title'],SNAPSHOT['rank_title'])
        self.assertEqual(second['rank_match_info']['rank_title'],other['rank_title'])

    def test_invalid_rank_state_and_other_player_authority_are_refused_without_mutation(self):
        _,code=self.both_start()
        snapshots=[{},None,dict(SNAPSHOT,rank_title='bad\x00title'),
                   dict(SNAPSHOT,win_streak_r_bits=0x7f800000),
                   dict(SNAPSHOT,account_id=2),dict(SNAPSHOT,player_id=B)]
        for snapshot in snapshots:
            body=end_body(code,1);body['rank_snapshot']=snapshot
            with self.subTest(snapshot=snapshot),self.assertRaises(ValueError):
                self.service.request(A,'Alpha',E1,body)
        self.assertFalse(self.service._battle_history[code]['reports'])

    def test_rematch_rotates_and_old_p2_start_or_end_cannot_modify_new_round(self):
        sid,old=self.both_start()
        self.end(A,E1,old,1)
        with self.assertRaises(ValueError):self.start(B,P2,old)
        fresh=self.start(A,P1)['match_code']
        self.assertNotEqual(fresh,old)
        self.assertEqual(self.start(A,P1)['match_code'],fresh)
        with self.assertRaises(ValueError):self.start(B,P2,old)
        self.assertEqual(self.start(B,P2,fresh)['match_code'],fresh)
        self.assertEqual(self.end(B,E2,old,2)['res'],0)
        self.assertFalse(self.service._battle_history[fresh]['reports'])
        self.assertEqual(self.service._battles[sid]['match_code'],fresh)
        self.assertEqual(self.end(A,E1,old,1)['res'],0)
        self.end(A,E1,fresh,2)
        self.assertEqual(self.service._battle_history[fresh]['reports'],{A:2})

    def test_other_room_unknown_code_and_new_tcp_peer_cannot_claim_issued_round(self):
        _,code=self.both_start()
        d='d'*32
        self.add_peer(C,'Outside');self.add_peer(d,'Other')
        self.room(C,d)
        foreign=self.start(C,P1)['match_code'];self.start(d,P2,foreign)
        for owner,route,wrong in ((A,E1,foreign),(C,E1,code),(A,E1,'f'*32)):
            with self.assertRaises(ValueError):self.end(owner,route,wrong,1)
        original=copy.deepcopy(self.service._accounts[A])
        self.service.disconnect(A)
        self.server.peers[C].account=original
        self.service.bind_account(C,original)
        with self.assertRaises(ValueError):self.end(C,E1,code,1)
        self.assertFalse(self.service._battle_history[code]['reports'])

    def test_end_requires_current_own_login_and_same_account_snapshot(self):
        _,code=self.both_start()
        original=self.service._accounts[A]
        self.service._accounts[A]={'id':999,'display_name':'Other'}
        with self.assertRaises(ValueError):self.end(A,E1,code,1)
        self.service._accounts[A]=original
        session=self.service._sessions.pop(A)
        with self.assertRaises(ValueError):self.end(A,E1,code,1)
        self.service._sessions[A]=session
        self.assertEqual(self.end(A,E1,code,1)['res'],0)

    def test_receipt_ttl_is_not_renewed_by_retries_or_leave(self):
        with patch('backend_services.time.monotonic') as clock:
            clock.return_value=100
            _,code=self.both_start();self.end(A,E1,code,1)
            expires=self.service._battle_history[code]['expires_at']
            self.assertEqual(expires,700)
            clock.return_value=200
            self.operation(A,'leave')
            self.assertEqual(self.service._battle_history[code]['expires_at'],expires)
            clock.return_value=699
            self.end(A,E1,code,1)
            self.assertEqual(self.service._battle_history[code]['expires_at'],expires)
            clock.return_value=700
            with self.assertRaises(ValueError):self.end(B,E2,code,2)
            self.assertNotIn(code,self.service._battle_history)

    def test_receipt_storage_bound_preserves_unexpired_idempotence(self):
        with patch('backend_services.MAX_BATTLE_RECEIPTS',2),patch('backend_services.time.monotonic') as clock:
            clock.return_value=100
            sid,first=self.both_start();self.end(A,E1,first,1)
            second=self.start(A,P1)['match_code'];self.start(B,P2,second)
            self.end(A,E1,second,1)
            with self.assertRaises(ValueError):self.start(A,P1)
            self.assertEqual(len(self.service._battle_history),2)
            self.assertEqual(self.service._battles[sid]['match_code'],second)
            self.assertEqual(self.end(A,E1,first,1)['res'],0)
            clock.return_value=701
            third=self.start(A,P1)['match_code']
            self.assertNotIn(third,(first,second))
            self.assertEqual(len(self.service._battle_history),1)

    def test_self_play_and_reports_do_not_call_unverified_rating_boundary(self):
        self.server.peers[B].account=copy.deepcopy(self.server.peers[A].account)
        self.service._accounts[B]=copy.deepcopy(self.service._accounts[A])
        self.server.account_store=Mock()
        _,code=self.both_start()
        self.end(A,E1,code,1);self.end(B,E2,code,2)
        self.server.account_store.record_result.assert_not_called()

    def test_force_end_is_closed_until_its_native_contract_is_confirmed(self):
        _,code=self.both_start()
        for outcome in range(4):
            with self.assertRaises(ValueError):
                self.service.request(A,'Alpha','/pvp/force_end_battle.php',
                                     end_body(code,outcome))
        self.assertFalse(self.service._battle_history[code]['reports'])


class BattleEndTCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_end_after_other_native_leave_and_replay_through_game_port(self):
        class Store:
            def get_native_state(self, account_id): return {}
            def authenticate(self, token):
                return {'id':1 if token=='first' else 2,'display_name':token} if token in ('first','second') else None
        server=await fixtures.GameServer('127.0.0.1',0,Store()).start()
        streams=[];serial=0
        async def send(index,payload,event):
            reader,writer=streams[index]
            writer.write((json.dumps(payload)+'\n').encode());await writer.drain()
            while True:
                line=await asyncio.wait_for(reader.readline(),3)
                self.assertTrue(line)
                reply=json.loads(line)
                if reply.get('event')==event:return reply
        async def service(index,route,body):
            nonlocal serial
            serial+=1
            return await send(index,{'op':'lan_backend_service','request':{
                'request_id':f'service-{serial}','path':route,'body':body}},'lan_backend_service')
        try:
            owners=[]
            for index,token in enumerate(('first','second')):
                streams.append(await asyncio.open_connection('127.0.0.1',server.port))
                welcome=await send(index,{'op':'hello','version':2,'account_token':token},'welcome')
                owners.append(welcome['client_id'])
                self.assertEqual((await service(index,'/user/login.php',{}))['state'],'ok')
            native=fixtures.data('first')
            command=fixtures.translate_request(fixtures.request('create',native_data=native,
                attributes={str(i):n for i,n in enumerate(native['numeric'])}),owners[0],protocol=5)
            room=await send(0,{'op':'native_session','request':command},'native_session_result')
            command=fixtures.translate_request(fixtures.request('join',session_id=room['session']['session_id'],
                native_member=fixtures.member('second')),owners[1],protocol=5)
            await send(1,{'op':'native_session','request':command},'native_session_result')
            first=await service(0,P1,{})
            self.assertEqual(first['state'],'ok');code=first['body']['match_code']
            self.assertEqual((await service(1,P2,{'match_code':code}))['state'],'ok')
            first_end=await service(0,E1,end_body(code,1))
            self.assertEqual(first_end['state'],'ok')
            command=fixtures.translate_request(fixtures.request('leave'),owners[0],protocol=5)
            await send(0,{'op':'native_session','request':command},'native_session_result')
            self.assertFalse(server.backend_services._battles)
            second_end=await service(1,E2,end_body(code,2))
            self.assertEqual(second_end['state'],'ok')
            replay=await service(0,E1,end_body(code,1))
            self.assertEqual(replay['body'],first_end['body'])
            conflict=await service(0,E1,end_body(code,2))
            self.assertEqual(conflict['state'],'error')
            self.assertEqual(server.backend_services._battle_history[code]['reports'],{owners[0]:1,owners[1]:2})
        finally:
            for _,writer in streams:
                writer.close();await writer.wait_closed()
            await server.close()


if __name__=='__main__':unittest.main()
