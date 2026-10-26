"""Equality-only telemetry privacy and server-owned identity correlation."""
import copy
import asyncio
import json
import unittest
from unittest.mock import patch

from native_identity_diagnostics import NativeIdentityDiagnostics
from native_sessions import NativeSessionDirectory
from szero_lan import GameServer, Peer, VERSION
from test_native_sessions_v2 import A, B, C, create, data, member, query, request


class Log:
    def __init__(self):
        self.lines = []

    def info(self, message, *args):
        self.lines.append(message % args)


class NativeIdentityDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.log = Log()
        self.diag = NativeIdentityDiagnostics(2, self.log)
        self.live = {A, B}

    def remember(self, owner=B, native=None, **kwargs):
        return self.diag.remember(owner, request("join", session_id="d" * 32,
            native_member=native or member("guest-private")), live_clients=self.live,
            validated=True, request_id="rpc-2", **kwargs)

    def returned(self, native=None):
        directory = NativeSessionDirectory()
        return create(directory, native=native or data("host-private"))

    def test_different_both_and_exact_privacy(self):
        self.assertTrue(self.remember())
        session = self.returned()
        unchanged = copy.deepcopy(session)
        self.diag.returned(B, "rpc-49", [session])
        text = "\n".join(self.log.lines)
        self.assertIn("primary_equal=0 secondary_equal=0", text)
        self.assertIn("client=" + B + " request=rpc-49 session=" + session["session_id"], text)
        for forbidden in ("guest-private", "host-private", "127.0.0.1", "identity_hex", "address_hex",
                          "guest-private".encode().hex(), "host-private".encode().hex(), "data_base64"):
            self.assertNotIn(forbidden, text)
        self.assertEqual(session, unchanged)

    def test_shared_primary_different_secondary(self):
        host = data("shared-private")
        guest = member("different-private")
        guest["identity_hex"][0] = host["member"]["identity_hex"][0]
        self.remember(native=guest)
        self.diag.returned(B, "rpc-97", [self.returned(host)])
        self.assertIn("primary_equal=1 secondary_equal=0", self.log.lines[-1])

    def test_initial_ingress_collision_visible_without_repeated_search_and_bounded(self):
        self.diag = NativeIdentityDiagnostics(8, self.log)
        self.live = {format(i, "032x") for i in range(8)}
        for i, owner in enumerate(sorted(self.live)):
            submitted = member("secondary-private-" + str(i))
            submitted["identity_hex"][0] = b"shared-private-primary".hex()
            self.diag.remember(owner, request("join", native_member=submitted),
                live_clients=self.live, validated=True, request_id="rpc-1")
        # No discovery call or repeated search was needed for this comparison.
        last = sorted(self.live)[-1]
        details = [line for line in self.log.lines if "ingress_compare" in line and "client=" + last + " " in line]
        self.assertEqual(len(details), 4)
        self.assertTrue(all("primary_equal=1 secondary_equal=0" in line for line in details))
        self.assertIn("compared=7 primary_equal_count=7 secondary_equal_count=0 pair_equal_count=0", self.log.lines[-1])
        self.assertNotIn("shared-private-primary", "\n".join(self.log.lines))

    def test_missing_identity_is_unknown(self):
        self.diag.returned(B, "rpc-1", [self.returned()])
        self.assertIn("primary_equal=-1 secondary_equal=-1", self.log.lines[-1])
        self.assertIn("requester_primary_len=-1", self.log.lines[-1])

    def test_malformed_unvalidated_and_nonlive_not_remembered(self):
        valid = request("join", native_member=member("private"))
        self.assertFalse(self.diag.remember(B, valid, live_clients=self.live))
        bad = copy.deepcopy(valid);bad["native_member"]["identity_hex"] = ["00", "61"]
        self.assertFalse(self.diag.remember(B, bad, live_clients=self.live, validated=True))
        self.assertFalse(self.diag.remember(C, valid, live_clients=self.live, validated=True))
        self.assertFalse(self.diag.identities)
        self.assertFalse(self.log.lines)

    def test_live_connection_key_not_payload_owner_and_cleanup_bound(self):
        native = member("payload-private")
        submitted = request("join", owner_id=A, native_member=native)
        self.assertTrue(self.diag.remember(B, submitted, live_clients=self.live, validated=True))
        native["identity_hex"][0] = "736f757263652d6d757461746564"
        self.assertIn(B, self.diag.identities)
        self.assertEqual(self.diag.identities[B][0], b"payload-private")
        self.assertNotIn(A, self.diag.identities)
        self.remember(A)
        self.live.add(C)
        self.assertFalse(self.remember(C))
        self.assertEqual(len(self.diag.identities), 2)
        self.diag.disconnect(B)
        self.assertNotIn(B, self.diag.identities)
        self.diag.returned(B, "rpc-3", [self.returned()])
        self.assertIn("primary_equal=-1 secondary_equal=-1", self.log.lines[-1])
        self.assertTrue(self.remember(C))
        self.live.remove(A)
        self.assertTrue(self.remember(C))
        self.assertNotIn(A, self.diag.identities)

    def test_candidate_details_bounded_and_metadata_sanitized(self):
        self.remember()
        session = self.returned()
        session["session_id"] = "bad\nidentity-private"
        self.diag.returned(B, "bad\nrequest", [session] * 9)
        candidates = [line for line in self.log.lines if "candidate" in line]
        self.assertEqual(len(candidates), 4)
        self.assertTrue(all("request=None session=None" in line for line in candidates))
        self.assertNotIn("identity-private", "\n".join(candidates))

    def test_server_records_only_successful_validation_and_transaction_prepare(self):
        server = GameServer("127.0.0.1", 27150)
        server.native_identity_diagnostics = self.diag
        peer = Peer(B, "Guest", None, "127.0.0.1")
        server.peers[B] = peer
        server.send = lambda *args: None
        server.notify_native_sessions = lambda *args: None
        server.notify_native_transport = lambda *args: None
        native = data("guest-private")
        payload = request("create", native_data=native, attributes={str(i): v for i, v in enumerate(native["numeric"])})
        bad = copy.deepcopy(payload);bad["attributes"] = {}
        with patch("szero_lan.LOG", self.log):
            server.native_transaction_request(peer, {"op": "native_session_transaction", "request":
                {"version": 1, "op": "prepare", "transaction_id": "rpc-1", "request": bad}})
            self.assertNotIn(B, self.diag.identities)
            server.native_transaction_request(peer, {"op": "native_session_transaction", "request":
                {"version": 1, "op": "prepare", "transaction_id": "rpc-2", "request": payload}})
            self.assertIn(B, self.diag.identities)
            self.assertTrue(any("wire=transaction action=create result=prepared" in line for line in self.log.lines))

    def test_server_search_compares_stored_owner_not_requester(self):
        server = GameServer("127.0.0.1", 27150)
        server.native_identity_diagnostics = self.diag
        peer = Peer(B, "Guest", None, "127.0.0.1")
        server.peers[B] = peer
        server.send = lambda *args: None
        create(server.native_sessions, native=data("host-private"))
        self.remember()
        with patch("szero_lan.LOG", self.log):
            server.native_request(peer, {"op": "native_session", "request": request("search", query=query(),
                materialization_profile=2, default_normalize=False, limit=1)})
        self.assertTrue(any("primary_equal=0 secondary_equal=0" in line for line in self.log.lines))


class NativeIdentityWireTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_tcp_ingress_search_and_disconnect(self):
        server = await GameServer("127.0.0.1", 0).start()
        log = Log()
        server.native_identity_diagnostics.log = log
        connections = []

        async def receive(client, wanted):
            async def read():
                for _ in range(64):
                    value = json.loads(await client[0].readline())
                    self.assertNotEqual(value["event"], "match_start")
                    if value["event"] == wanted:
                        return value
                self.fail("too many unrelated events")
            return await asyncio.wait_for(read(), 3)

        async def send(client, message, wanted):
            client[1].write((json.dumps(message) + "\n").encode())
            await client[1].drain()
            return await receive(client, wanted)

        try:
            for name in ("Host", "Guest"):
                client = await asyncio.open_connection("127.0.0.1", server.port)
                connections.append(client)
                await send(client, {"op": "hello", "version": VERSION, "name": name}, "welcome")
            host, guest = connections
            native = data("shared-private-primary")
            host_create = request("create", native_data=native,
                attributes={str(i): value for i, value in enumerate(native["numeric"])})
            created = await send(host, {"op": "native_session", "request": host_create}, "native_session_result")
            search_request = request("search", query=query(field_4d=1), default_normalize=False,
                materialization_profile=2, limit=1)
            found = await send(guest, {"op": "native_session", "request": search_request}, "native_session_result")
            self.assertEqual(found["sessions"], [created["session"]])
            self.assertTrue(any("primary_equal=-1 secondary_equal=-1" in line for line in log.lines))
            guest_native = data("guest-private-secondary")
            guest_native["member"]["identity_hex"][0] = native["member"]["identity_hex"][0]
            await send(guest, {"op": "native_session", "request": request("create", native_data=guest_native,
                attributes={str(i): value for i, value in enumerate(guest_native["numeric"])})}, "native_session_result")
            self.assertTrue(any("ingress_compare" in line and "primary_equal=1 secondary_equal=0" in line for line in log.lines))
            guest[1].close()
            await guest[1].wait_closed()
            async def removed():
                while len(server.native_identity_diagnostics.identities) != 1:
                    await asyncio.sleep(.01)
            await asyncio.wait_for(removed(), 3)
            self.assertNotIn("shared-private-primary", "\n".join(log.lines))
            self.assertNotIn("guest-private-secondary", "\n".join(log.lines))
        finally:
            for _, writer in connections:
                writer.close()
                await writer.wait_closed()
            await server.close()


if __name__ == "__main__":
    unittest.main()
