"""LAN-owned battle-start contracts. Account verification is fixture-only.

Uses the actual native directory, GameServer resolver and TCP service route;
never submits official IDs, tickets, selection data or game packets.
"""
import asyncio
import json
import unittest
from unittest.mock import Mock, patch

from backend_services import LanBackendServices
from lan_identity import translate_request
from szero_lan import GameServer, Peer
from test_native_sessions_v2 import data, member, request

P1 = "/pvp/start_battle_player1.php"
P2 = "/pvp/start_battle_player2.php"
A, B, C = (value*32 for value in "abc")


class BattleStartTests(unittest.TestCase):
    def setUp(self):
        self.server = GameServer("127.0.0.1", 27150)
        self.server.send = Mock()
        self.service = self.server.backend_services
        self.add_peer(A, "Alpha")
        self.add_peer(B, "Beta")

    def add_peer(self, owner, name):
        # This only emulates the already-verified hello; real TCP test below
        # exercises the server token boundary rather than accepting body IDs.
        account = {"id": len(self.server.peers)+1, "display_name": name}
        self.server.peers[owner] = Peer(owner, name, None, "127.0.0.1", account=account)
        self.service.bind_account(owner, account)
        self.service.request(owner, name, "/user/login.php", {})

    def operation(self, owner, op, protocol=5, **fields):
        payload = translate_request(request(op, **fields), owner, protocol=protocol)
        self.server.native_request(self.server.peers[owner], {"op": "native_session", "request": payload})
        errors = [call.args[1] for call in self.server.send.call_args_list
                  if call.args[1].get("event") == "native_session_error"]
        self.assertFalse(errors, errors)

    def room(self, first=A, second=B, protocol=5, capacity=2):
        native = data(first)
        native["capacity"] = capacity
        self.operation(first, "create", protocol=protocol, native_data=native,
                       attributes={str(i): n for i, n in enumerate(native["numeric"])})
        sid = self.server.native_sessions.memberships[first]
        self.operation(second, "join", protocol=protocol, session_id=sid, native_member=member(second))
        return sid

    def start(self, owner, route, body=None):
        if body is None:
            if route == P2:
                sid = self.server.native_sessions.memberships.get(owner)
                battle = self.service._battles.get(sid)
                body = {"match_code": battle["match_code"] if battle else "0"*32}
            else:
                body = {}
        return self.service.request(owner, self.server.peers[owner].name, route, body)

    def test_ordered_start_is_idempotent_and_returns_owned_snapshots(self):
        sid = self.room()
        for owner, route in ((B, P2), (A, P2), (B, P1)):
            with self.subTest(owner=owner, route=route), self.assertRaises(ValueError):
                self.start(owner, route)
        self.assertFalse(self.service._battles)
        first = self.start(A, P1)
        self.assertEqual(first["res"], 0)
        self.assertRegex(first["match_code"], r"^[0-9a-f]{32}$")
        self.assertEqual(first["match_phase"], 0)
        self.assertIs(type(first["match_phase"]), int)
        self.assertEqual(first, self.start(A, P1))
        self.assertEqual(first, self.start(B, P2))
        first["match_code"] = "tampered"
        self.assertNotEqual(self.start(A, P1)["match_code"], "tampered")
        self.assertEqual(set(self.service._battles), {sid})

    def test_both_accounts_and_both_lan_logins_are_required(self):
        self.room()
        for owner in (A, B):
            account = self.service._accounts.pop(owner)
            with self.assertRaises(ValueError): self.start(A, P1)
            self.service._accounts[owner] = account
            session = self.service._sessions.pop(owner)
            with self.assertRaises(ValueError): self.start(A, P1)
            self.service._sessions[owner] = session
            peer_account = self.server.peers[owner].account
            self.server.peers[owner].account = None
            with self.assertRaises(ValueError): self.start(A, P1)
            self.server.peers[owner].account = peer_account
        self.assertFalse(self.service._battles)

    def test_bodies_unknown_routes_and_nonmember_cannot_supply_authority(self):
        self.room()
        self.add_peer(C, "Outside")
        for route in (P1, P2):
            for body in ({"match_code": "a"*32}, {"role": 0}, {"peer_id": A},
                         {"auth_info": "ticket"}, {"characters": [1]}, {"target": "self"}, [], None):
                with self.subTest(route=route, body=body), self.assertRaises(ValueError):
                    self.service.request(A, "Alpha", route, body)
            with self.assertRaises(ValueError): self.start(C, route)
        for route in ("/pvp/start_battle.php", "/pvp/start_battle_player3.php", P1+"?x=1",
                      "/pvp/end_battle.php"):
            with self.assertRaises(ValueError): self.start(A, route)
        self.assertFalse(self.service._battles)

    def test_room_capacity_partition_and_version_are_boundaries(self):
        for protocol in (4, 5):
            self.setUp()
            self.room(protocol=protocol)
            self.assertEqual(self.start(A, P1), self.start(B, P2))
        self.setUp()
        self.room(capacity=8)
        with self.assertRaises(ValueError): self.start(A, P1)
        self.setUp()
        with self.assertRaises(ValueError): self.start(A, P1)
        partition = {"build": "a"*64, "protocol": 1, "mode": 0}
        native = data(A)
        room = self.server.native_sessions.handle(A, request("create", native_data=native,
            attributes={str(i): n for i,n in enumerate(native["numeric"])}))
        self.server.native_sessions.handle(B, request("join", session_id=room["session"]["session_id"],
                                                    native_member=member(B)))
        with self.assertRaises(ValueError): self.start(A, P1)
        # A nominal LAN partition without the owned profile2 descriptor is also refused.
        self.server.native_sessions.sessions[room["session"]["session_id"]].partition = ("a"*64, 5, 0)
        self.server.native_sessions.sessions[room["session"]["session_id"]].version = 1
        with self.assertRaises(ValueError): self.start(A, P1)
        self.assertFalse(self.service._battles)

    def test_leave_notifies_invalidation_and_same_peer_rejoin_requires_new_start(self):
        sid = self.room()
        old = self.start(A, P1)["match_code"]
        self.operation(B, "leave")
        self.assertFalse(self.service._battles)
        self.operation(B, "join", session_id=sid, native_member=member(B))
        with self.assertRaises(ValueError): self.start(B, P2)
        self.assertNotEqual(self.start(A, P1)["match_code"], old)
        self.assertEqual(self.start(A, P1), self.start(B, P2))

    def test_another_room_cannot_use_the_first_rooms_start(self):
        self.room()
        first_code = self.start(A, P1)["match_code"]
        other = "d"*32
        self.add_peer(C, "Gamma")
        self.add_peer(other, "Delta")
        self.room(C, other)
        with self.assertRaises(ValueError): self.start(other, P2)
        second_code = self.start(C, P1)["match_code"]
        self.assertNotEqual(first_code, second_code)
        self.assertEqual(self.start(other, P2)["match_code"], second_code)
        self.assertEqual(self.start(B, P2)["match_code"], first_code)

    def test_lazy_validation_rejects_stale_record_even_without_notification(self):
        sid = self.room()
        old = self.start(A, P1)["match_code"]
        before = self.server.resolve_battle(A)["membership"]
        directory = self.server.native_sessions
        directory.disconnect(B)
        payload = translate_request(request("join", session_id=sid, native_member=member(B)), B, protocol=5)
        directory.handle(B, payload)
        self.assertNotEqual(self.server.resolve_battle(A)["membership"], before)
        with self.assertRaises(ValueError): self.start(B, P2)
        self.assertNotEqual(self.start(A, P1)["match_code"], old)

    def test_host_leave_and_tcp_disconnect_remove_records(self):
        self.room()
        old = self.start(A, P1)["match_code"]
        self.operation(A, "leave")
        self.assertFalse(self.service._battles)
        self.room()
        self.assertNotEqual(self.start(A, P1)["match_code"], old)
        self.service.disconnect(B)
        self.assertFalse(self.service._battles)
        with self.assertRaises(ValueError): self.start(A, P1)
        self.service.disconnect(B)

    def test_bounded_records_reuse_capacity_only_after_invalidation(self):
        rooms = []
        for index in range(3):
            owners = tuple(f"{index*2+n+1:032x}" for n in range(2))
            for owner in owners: self.add_peer(owner, "Player"+owner[-2:])
            self.room(*owners)
            rooms.append(owners)
        with patch("backend_services.MAX_PEERS", 2):
            for first, _ in rooms[:2]: self.start(first, P1)
            with self.assertRaises(ValueError): self.start(rooms[2][0], P1)
            self.assertEqual(len(self.service._battles), 2)
            self.operation(rooms[0][0], "leave")
            self.start(rooms[2][0], P1)
            self.assertEqual(len(self.service._battles), 2)


class BattleStartTCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_game_port_authentication_room_order_and_disconnect(self):
        class Store:
            def get_native_state(self, account_id): return {}
            def authenticate(self, token):
                if token in ("fixture-first", "fixture-second"):
                    return {"id": 1 if token.endswith("first") else 2, "display_name": token}
                return None
        server = await GameServer("127.0.0.1", 0, Store()).start()
        streams = []
        async def send(index, payload, event):
            reader, writer = streams[index]
            writer.write((json.dumps(payload)+"\n").encode())
            await writer.drain()
            while True:
                response = json.loads(await asyncio.wait_for(reader.readline(), 3))
                if response.get("event") == event: return response
        async def service(index, route, generation, body=None):
            return await send(index, {"op": "lan_backend_service", "request": {
                "request_id": f"service-{generation}", "path": route, "body": {} if body is None else body}}, "lan_backend_service")
        try:
            owners = []
            for index, token in enumerate(("fixture-first", "fixture-second")):
                streams.append(await asyncio.open_connection("127.0.0.1", server.port))
                welcome = await send(index, {"op": "hello", "version": 2, "account_token": token}, "welcome")
                owners.append(welcome["client_id"])
                self.assertEqual((await service(index, "/user/login.php", 1))["state"], "ok")
            native = data("first")
            payload = translate_request(request("create", native_data=native,
                attributes={str(i): n for i,n in enumerate(native["numeric"])}), owners[0], protocol=5)
            room = await send(0, {"op": "native_session", "request": payload}, "native_session_result")
            payload = translate_request(request("join", session_id=room["session"]["session_id"],
                                                native_member=member("second")), owners[1], protocol=5)
            await send(1, {"op": "native_session", "request": payload}, "native_session_result")
            self.assertEqual((await service(1, P2, 2))["state"], "error")
            first = await service(0, P1, 2)
            second = await service(1, P2, 3, {"match_code": first["body"]["match_code"]})
            self.assertEqual(first["state"], "ok")
            self.assertEqual(first["body"], second["body"])
            self.assertRegex(first["body"]["match_code"], r"^[0-9a-f]{32}$")
            streams[1][1].close()
            await streams[1][1].wait_closed()
            for _ in range(100):
                if len(server.peers) == 1: break
                await asyncio.sleep(.01)
            self.assertEqual(len(server.peers), 1)
            self.assertFalse(server.backend_services._battles)
            self.assertEqual((await service(0, P1, 3))["state"], "error")
        finally:
            for _, writer in streams:
                writer.close()
                await writer.wait_closed()
            await server.close()


if __name__ == "__main__":
    unittest.main()
