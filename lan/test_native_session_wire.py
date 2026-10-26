"""Real local TCP tests; no game, platform login, or native ABI invocation."""
import asyncio
import json
import unittest

from szero_lan import GameServer, VERSION


PARTITION = {"build": "a" * 64, "protocol": 1, "mode": 7}


class NativeSessionWireTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = await GameServer("127.0.0.1", 0).start()
        self.connections = []

    async def asyncTearDown(self):
        for _, writer in self.connections:
            writer.close()
        for _, writer in self.connections:
            await writer.wait_closed()
        await self.server.close()

    async def receive(self, client, expected):
        async def read():
            for _ in range(64):
                line = await client[0].readline()
                self.assertTrue(line, "unexpected disconnect")
                result = json.loads(line)
                self.assertNotEqual(result["event"], "match_start",
                                    "directory membership must not imply game battle start")
                if result["event"] == expected:
                    return result
            self.fail("excess unrelated events")
        return await asyncio.wait_for(read(), 3)

    async def connect_client(self, name):
        client = await asyncio.open_connection("127.0.0.1", self.server.port)
        self.connections.append(client)
        client[1].write((json.dumps({"op": "hello", "version": VERSION, "name": name}) + "\n").encode())
        await client[1].drain()
        welcome = await self.receive(client, "welcome")
        self.assertEqual(welcome["capabilities"]["native_sessions"], 1)
        return client

    async def operation(self, client, op, expected="native_session_result", **fields):
        request = {"version": 1, "request_id": "req-" + op, "op": op, **fields}
        client[1].write((json.dumps({"op": "native_session", "request": request}) + "\n").encode())
        await client[1].drain()
        response = await self.receive(client, expected)
        self.assertEqual(response["request_id"], request["request_id"])
        return response

    async def create(self, client, value=10):
        return (await self.operation(client, "create", partition=PARTITION,
                                     attributes={"3": value}))["session"]

    async def test_search_join_preserves_attributes_without_starting_battle(self):
        host = await self.connect_client("Host")
        guest = await self.connect_client("Guest")
        session = await self.create(host)
        found = await self.operation(guest, "search", partition=PARTITION, limit=4,
                                     filters=[{"key": "3", "comparison": "eq", "value": 10}])
        self.assertEqual(found["sessions"], [session])
        joined = await self.operation(guest, "join", partition=PARTITION,
                                      session_id=session["session_id"])
        self.assertEqual(joined["session"]["attributes"], {"3": 10})
        self.assertEqual([m["join_order"] for m in joined["session"]["members"]], [0, 1])
        state = await self.receive(host, "native_session_state")
        self.assertEqual(state["session"], joined["session"])
        self.assertEqual(self.server.matches, {})
        self.assertEqual(self.server.waiting, [])

    async def test_disconnect_revokes_session_for_remaining_member(self):
        host = await self.connect_client("Host")
        guest = await self.connect_client("Guest")
        session = await self.create(host)
        await self.operation(guest, "join", partition=PARTITION, session_id=session["session_id"])
        await self.receive(host, "native_session_state")
        host[1].close()
        await host[1].wait_closed()
        state = await self.receive(guest, "native_session_state")
        self.assertIsNone(state["session"])
        found = await self.operation(guest, "search", partition=PARTITION, limit=4, filters=[])
        self.assertEqual(found["sessions"], [])
        self.assertFalse(self.server.native_sessions.memberships)

    async def test_native_constructor_data_survives_real_tcp_create_and_join(self):
        host = await self.connect_client("Host")
        guest = await self.connect_client("Guest")
        member = {"identity_hex": ["6964656e74697479", "7365636f6e64"],
                  "address_hex": "3132372e302e302e313a3333303031", "field_88": 5,
                  "optional_present": True, "optional_value": 7, "field_8b": 9}
        native = {"profile": 1, "compatibility": 1234, "numeric": [42], "capacity": 2,
                  "field_e1": 11, "stream": None, "properties": [], "member": member}
        created = await self.operation(host, "create", partition=PARTITION,
                                       attributes={"0": 42}, native_data=native)
        session = created["session"]
        found = await self.operation(guest, "search", partition=PARTITION, filters=[],
                                     limit=4, materialization_profile=1)
        self.assertEqual(found["sessions"], [session])
        joined = await self.operation(guest, "join", partition=PARTITION,
                                      session_id=session["session_id"], native_member=member)
        descriptor = joined["session"]["native_descriptor"]
        self.assertEqual(descriptor["numeric"], [42])
        self.assertEqual(descriptor["compatibility"], 1234)
        self.assertEqual([m["owner"] for m in descriptor["members"]], [True, False])
        for item in descriptor["members"]:
            self.assertEqual(item["identity_hex"], member["identity_hex"])
            self.assertEqual(item["address_hex"], member["address_hex"])
        update = await self.receive(host, "native_session_state")
        self.assertEqual(update["session"], joined["session"])
        self.assertEqual(self.server.matches, {})

    async def test_three_independent_sessions_and_full_join_rejection(self):
        clients = [await self.connect_client("Player" + str(i)) for i in range(7)]
        identifiers = set()
        for index in range(3):
            session = await self.create(clients[index * 2], index)
            identifiers.add(session["session_id"])
            await self.operation(clients[index * 2 + 1], "join", partition=PARTITION,
                                 session_id=session["session_id"])
            await self.receive(clients[index * 2], "native_session_state")
        self.assertEqual(len(identifiers), 3)
        full = await self.operation(clients[-1], "join", expected="native_session_error",
                                    partition=PARTITION, session_id=session["session_id"])
        self.assertIn("full", full["message"])
        found = await self.operation(clients[-1], "search", partition=PARTITION, limit=4, filters=[])
        self.assertEqual(found["sessions"], [])
        self.assertEqual(self.server.matches, {})

    async def test_spoofed_owner_rejected_and_native_sidecar_membership_exclusive(self):
        client = await self.connect_client("Player")
        error = await self.operation(client, "create", expected="native_session_error",
                                     partition=PARTITION, attributes={}, owner_id="b" * 32)
        self.assertIn("fields", error["message"])
        self.assertFalse(self.server.native_sessions.sessions)
        await self.create(client)
        client[1].write(b'{"op":"queue"}\n')
        await client[1].drain()
        error = await self.receive(client, "error")
        self.assertIn("native session", error["message"])
        await self.operation(client, "leave")
        client[1].write(b'{"op":"create","name":"Sidecar"}\n')
        await client[1].drain()
        await self.receive(client, "state")
        error = await self.operation(client, "search", expected="native_session_error",
                                     partition=PARTITION, limit=4, filters=[])
        self.assertIn("sidecar", error["message"])


if __name__ == "__main__":
    unittest.main()
