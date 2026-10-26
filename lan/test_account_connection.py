"""Connection-owned accounts and fail-closed native ranked policy."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest

from backend_rpc import BackendServiceRPC
from szero_lan import GameServer


class AccountConnectionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        class Store:
            def get_native_state(self, account_id): return {}
            def authenticate(self, token):
                if token == "valid-session":
                    return {"id": 7, "display_name": "Server Vegeta", "username": "vegeta"}
                return None
            def login(self, username, password):
                if username == "vegeta" and password == "aa":
                    return {"token": "valid-session", "profile": self.authenticate("valid-session")}
                raise ValueError("bad credentials must never be echoed: "+str(password))
        self.server = await GameServer("127.0.0.1", 0, Store()).start()
        self.connections = []

    async def asyncTearDown(self):
        for writer in self.connections:
            writer.close()
            await writer.wait_closed()
        await self.server.close()

    async def hello(self, **fields):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.server.port)
        self.connections.append(writer)
        writer.write((json.dumps(dict(op="hello", version=2, name="Spoofed", **fields))+"\n").encode())
        await writer.drain()
        line = await asyncio.wait_for(reader.readline(), 3)
        return json.loads(line) if line else None

    async def account(self, **fields):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.server.port)
        self.connections.append(writer)
        writer.write((json.dumps(dict(op="account", version=2, **fields))+"\n").encode())
        await writer.drain()
        result = json.loads(await asyncio.wait_for(reader.readline(), 3))
        self.assertEqual(await asyncio.wait_for(reader.readline(), 3), b"")
        return result

    async def test_login_and_remembered_session_share_game_port_without_game_peer(self):
        login = await self.account(action="login", username="vegeta", password="aa")
        self.assertEqual(login["state"], "ok")
        self.assertEqual(login["profile"]["display_name"], "Server Vegeta")
        self.assertEqual(login["token"], "valid-session")
        self.assertEqual(await self.account(action="me", token=login["token"]), login)
        self.assertFalse(self.server.peers)
        self.assertFalse(self.server.native_sessions.sessions)

    async def test_account_refusals_never_echo_credentials_or_accept_unknown_fields(self):
        for request in (dict(action="login", username="vegeta", password="DO-NOT-ECHO"),
                        dict(action="me", token="expired-secret"),
                        dict(action="login", username="vegeta", password="aa", admin=True),
                        dict(action="register", token="unimplemented")):
            response = await self.account(**request)
            self.assertEqual(response, {"event": "account", "state": "error", "message": "Login refused"})
        self.assertFalse(self.server.peers)

    async def test_verified_token_owns_name_and_ranked_policy(self):
        event = await self.hello(account_token="valid-session")
        self.assertEqual(event["account"], {"authenticated": True,
                         "display_name": "Server Vegeta", "ranked": True})
        peer = self.server.peers[event["client_id"]]
        self.assertEqual(peer.name, "Server Vegeta")
        self.assertEqual(self.server.backend_services._accounts[peer.id]["id"], 7)

    async def test_invalid_token_never_silently_downgrades_to_guest(self):
        self.assertIsNone(await self.hello(account_token="expired"))
        self.assertFalse(self.server.peers)
        self.assertIsNone(await self.hello(account_token={"ranked": True}))
        self.assertFalse(self.server.peers)

    async def test_guest_cannot_select_account_by_name_or_claim(self):
        event = await self.hello(account_id=7, ranked=True)
        self.assertEqual(event["account"], {"authenticated": False,
                         "display_name": "Spoofed", "ranked": False})
        self.assertFalse(self.server.backend_services._accounts)

    async def test_card_resolves_opponent_only_while_sharing_a_room(self):
        first = await self.hello(account_token="valid-session")
        second = await self.hello()
        a, b = first["client_id"], second["client_id"]
        target = "szlan:"+b
        with self.assertRaises(ValueError):
            self.server.resolve_card(a, target)
        partition = {"build": "a"*64, "protocol": 1, "mode": 0}
        room = self.server.native_sessions.handle(a, {"version": 1, "op": "create",
            "request_id": "create-card-room", "partition": partition, "attributes": {}})
        self.server.native_sessions.handle(b, {"version": 1, "op": "join",
            "request_id": "join-card-room", "partition": partition,
            "session_id": room["session"]["session_id"]})
        profile = self.server.resolve_card(a, target)
        self.assertEqual(profile["display_name"], "Spoofed")
        self.assertEqual(profile["principal"], target)
        self.assertEqual(self.server.resolve_card(a, "self")["id"], 7)
        self.server.native_sessions.disconnect(b)
        with self.assertRaises(ValueError):
            self.server.resolve_card(a, target)


    async def test_storage_failure_refuses_one_operation_without_dropping_tcp(self):
        from unittest.mock import patch
        reader,writer=await asyncio.open_connection('127.0.0.1',self.server.port)
        self.connections.append(writer)
        writer.write(b'{"op":"hello","version":2,"name":"Fixture"}\n');await writer.drain()
        welcome=json.loads(await asyncio.wait_for(reader.readline(),3))
        self.assertEqual(welcome['event'],'welcome')
        async def request(serial):
            value={'op':'lan_backend_service','request':{'request_id':f'service-{serial}','path':'/user/login.php','body':{}}}
            writer.write((json.dumps(value)+'\n').encode());await writer.drain()
            while True:
                response=json.loads(await asyncio.wait_for(reader.readline(),3))
                if response.get('event')=='lan_backend_service':return response
        with patch.object(self.server.backend_services,'request',side_effect=RuntimeError('private-db-detail')),self.assertLogs('szero_lan',level='ERROR') as captured:
            self.assertEqual((await request(1))['state'],'error')
        self.assertNotIn('private-db-detail',' '.join(captured.output))
        self.assertEqual((await request(2))['state'],'ok')


class AccountPolicyTests(unittest.TestCase):
    def test_policy_follows_verified_welcome_and_disconnect(self):
        with tempfile.TemporaryDirectory() as directory:
            rpc = BackendServiceRPC(Path(directory)/"runtime.lua", "a"*32)
            try:
                self.assertEqual(rpc.account_policy.read_bytes(), b"0\n")
                rpc.bind("b"*32, {"lan_backend_services": 1},
                         {"authenticated": True, "ranked": 1})
                self.assertEqual(rpc.account_policy.read_bytes(), b"0\n")
                rpc.bind("b"*32, {"lan_backend_services": 1},
                         {"authenticated": True, "ranked": True})
                self.assertEqual(rpc.account_policy.read_bytes(), b"1\n")
                rpc.invalidate()
                self.assertEqual(rpc.account_policy.read_bytes(), b"0\n")
            finally:
                rpc.close()
            self.assertFalse(rpc.account_policy.exists())
