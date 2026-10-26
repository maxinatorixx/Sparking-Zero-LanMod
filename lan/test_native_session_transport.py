"""Actual session-v2 TCP/UDP path. Game/channel handshake is NOT simulated."""
import asyncio
import socket
import threading
import time
import unittest

from szero_lan import GameServer, LobbyClient
from test_native_sessions_v2 import data, member, request


def until(predicate):
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


class NativeSessionTransportTests(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.ready = threading.Event()
        self.clients, self.games = [], []
        self.error = None

        def run():
            asyncio.set_event_loop(self.loop)
            try:
                self.server = self.loop.run_until_complete(GameServer("127.0.0.1", 0).start())
            except BaseException as exc:
                self.error = exc
            self.ready.set()
            if self.error is None:
                self.loop.run_forever()
            self.loop.close()

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        self.assertTrue(self.ready.wait(4))
        if self.error:
            raise self.error

    def tearDown(self):
        for client in self.clients:
            client.close()
        for game in self.games:
            game.close()
        asyncio.run_coroutine_threadsafe(self.server.close(), self.loop).result(4)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(4)

    def connect(self, name):
        game = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        game.bind(("127.0.0.1", 0))
        game.settimeout(0.3)
        self.games.append(game)
        client = LobbyClient("127.0.0.1", self.server.port, name,
                             game_port=game.getsockname()[1])
        self.clients.append(client)
        self.assertTrue(client.connected.wait(4))
        self.assertTrue(client.udp_ready.wait(4))
        return client, game

    def operation(self, client, operation, **fields):
        payload = request(operation, **fields)
        client.send("native_session", request=payload)
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            event = client.events.get(timeout=4)
            if event.get("event") in ("native_session_result", "native_session_error"):
                self.assertEqual(event["event"], "native_session_result", event)
                self.assertEqual(event["request_id"], payload["request_id"])
                return event
        self.fail("no native session response")

    def create(self, client, name):
        native = data(name)
        return self.operation(client, "create", native_data=native,
            attributes={str(i): v for i, v in enumerate(native["numeric"])})["session"]

    def test_two_simultaneous_native_sessions_relay_without_legacy_pairing(self):
        pairs = [self.connect(str(i)) for i in range(5)]
        a, b, c, d, waiting = [value[0] for value in pairs]
        session1, session2 = self.create(a, "a"), self.create(c, "c")
        self.operation(b, "join", session_id=session1["session_id"], native_member=member("b"))
        self.operation(d, "join", session_id=session2["session_id"], native_member=member("d"))
        for client in (a, b, c, d):
            self.assertTrue(until(lambda: client.assignment and client.assignment.get("native")))
        self.assertIsNone(waiting.assignment)
        for sender, receiver, text in ((0, 1, b"native-A"), (1, 0, b"native-B"),
                                       (2, 3, b"native-C"), (3, 2, b"native-D")):
            client, game = pairs[sender]
            game.sendto(text, ("127.0.0.1", client.proxy_port))
            payload, address = pairs[receiver][1].recvfrom(100)
            self.assertEqual(payload, text)
            self.assertEqual(address[1], pairs[receiver][0].proxy_port)
        for _, game in pairs:
            with self.assertRaises(socket.timeout):
                game.recvfrom(100)
        self.assertEqual(self.server.matches, {})
        self.assertEqual(self.server.waiting, [])
        self.operation(b, "leave")
        self.assertTrue(until(lambda: b.assignment is None))
        self.assertTrue(until(lambda: self.server.native_sessions.relay_peer(a.client_id.hex(),
                                                           session1["session_id"]) is None))
        pairs[0][1].sendto(b"after-leave", ("127.0.0.1", a.proxy_port))
        with self.assertRaises(socket.timeout):
            pairs[1][1].recvfrom(100)
        self.operation(a, "leave")
        self.assertTrue(until(lambda: a.assignment is None))
        self.assertTrue(c.assignment["native"])

    def test_member_update_notifies_peer_and_host_disconnect_revokes_transport(self):
        (host, _), (guest, _) = self.connect("Host"), self.connect("Guest")
        session = self.create(host, "host")
        self.operation(guest, "join", session_id=session["session_id"], native_member=member("guest"))
        self.assertTrue(until(lambda: guest.assignment is not None))
        changed = dict(member("guest"), optional_present=True, optional_value=7)
        response = self.operation(guest, "update", native_member=changed)
        self.assertEqual(response["session"]["native_descriptor"]["members"][1]["optional_value"], 7)
        seen = False
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            event = host.events.get(timeout=4)
            descriptor = (event.get("session") or {}).get("native_descriptor", {})
            if event.get("event") == "native_session_state" and len(descriptor.get("members", [])) == 2:
                if descriptor["members"][1]["optional_value"] == 7:
                    seen = True
                    break
        self.assertTrue(seen)
        host.close()
        self.assertTrue(until(lambda: guest.assignment is None))
        self.assertFalse(self.server.native_sessions.has_membership(guest.client_id.hex()))

    def test_version2_error_keeps_correlation_and_does_not_mutate(self):
        client, _ = self.connect("Rejected settings fixture")
        native = data()
        native["stream"]["read_cursor"] = 99
        client.send("native_session", request=request("create", native_data=native,
                    attributes={"0": -5, "1": 8}))
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            event = client.events.get(timeout=4)
            if event.get("event") == "native_session_error":
                self.assertEqual(event["version"], 2)
                self.assertEqual(event["request_id"], "v2-create")
                break
        else:
            self.fail("missing version2 error")
        self.assertEqual(self.server.native_sessions.sessions, {})
        self.assertIsNone(client.assignment)


if __name__ == "__main__":
    unittest.main()
