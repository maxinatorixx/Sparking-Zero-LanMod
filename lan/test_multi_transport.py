"""Real eight-client targeted LAN routing, without launching the game."""
import socket
import time
import unittest

from lan_identity import translate_request
from szero_lan import DATA, TARGET_DATA, packet
import test_native_session_transport as fixtures
from test_native_sessions_v2 import data, member, request, PARTITION


until = fixtures.until


class MultiTransportTests(unittest.TestCase):
    setUp = fixtures.NativeSessionTransportTests.setUp
    tearDown = fixtures.NativeSessionTransportTests.tearDown
    connect = fixtures.NativeSessionTransportTests.connect
    def multi_operation(self, client, op, **fields):
        payload = request(op, **fields)
        if "partition" in payload:
            payload["partition"] = dict(PARTITION, protocol=5)
        payload = translate_request(payload, client.client_id.hex(), protocol=5)
        client.send("native_session", request=payload)
        deadline = time.monotonic()+5
        while time.monotonic()<deadline:
            event = client.events.get(timeout=5)
            if event.get("event") in ("native_session_result", "native_session_error"):
                self.assertEqual(event["event"], "native_session_result", event)
                return event
        self.fail("No native multi response")

    def test_eight_members_target_every_pair_and_preserve_source_proxy(self):
        pairs = [self.connect(chr(97+i)) for i in range(8)]
        host = pairs[0][0]
        native = data("a", b"x"*4096);native["capacity"] = 8
        room = self.multi_operation(host, "create", native_data=native, attributes={"0":-5,"1":8})["session"]
        sid = room["session_id"]
        for i,(client,_) in enumerate(pairs[1:],1):
            self.multi_operation(client,"join", session_id=sid, native_member=member(chr(97+i)))
        self.assertTrue(until(lambda: all(c.assignment and c.assignment.get("multi") and len(c.assignment.get("peers",()))==8 for c,_ in pairs)))
        self.assertEqual(len(self.server.native_sessions.sessions[sid].members),8)
        for i,(sender,game) in enumerate(pairs):
            for j,(recipient,other_game) in enumerate(pairs):
                if i==j:
                    continue
                port = sender.remote_proxy(recipient.client_id.hex())
                self.assertEqual(port,sender.remote_proxy(recipient.client_id.hex()))
                body = f"target-{i}-{j}".encode()
                game.sendto(body,("127.0.0.1",port))
                other_game.settimeout(3)
                actual,source = other_game.recvfrom(65535)
                self.assertEqual(actual,body)
                self.assertEqual(source,("127.0.0.1",recipient.remote_proxy(sender.client_id.hex())))
        self.assertEqual(sum(c.game_packets_sent for c,_ in pairs),56)
        self.assertEqual(sum(c.game_packets_received for c,_ in pairs),56)
        for _,game in pairs:
            game.settimeout(.05)
            with self.assertRaises(socket.timeout):
                game.recvfrom(65535)

    def test_target_outside_room_and_stale_membership_never_receive(self):
        a,ga = self.connect("a");b,gb = self.connect("b");outsider,go = self.connect("outside")
        native=data("a");native["capacity"]=8
        sid=self.multi_operation(a,"create",native_data=native,attributes={"0":-5,"1":8})["session"]["session_id"]
        self.multi_operation(b,"join",session_id=sid,native_member=member("b"))
        self.assertTrue(until(lambda: b.assignment and len(b.assignment.get("peers",()))==2))
        # A two-member multi room still requires an explicit destination.
        a.udp.send(packet(DATA,a.client_id,bytes.fromhex(sid),b"legacy-no-target"))
        gb.settimeout(.2)
        with self.assertRaises(socket.timeout): gb.recvfrom(65535)
        a.udp.send(packet(TARGET_DATA,a.client_id,bytes.fromhex(sid),outsider.client_id+b"not-public"))
        go.settimeout(.2)
        with self.assertRaises(socket.timeout): go.recvfrom(65535)
        self.multi_operation(b,"leave")
        a.udp.send(packet(TARGET_DATA,a.client_id,bytes.fromhex(sid),b.client_id+b"stale"))
        gb.settimeout(.2)
        with self.assertRaises(socket.timeout): gb.recvfrom(65535)
        old_port=a.remote_proxy(b.client_id.hex())
        self.assertNotEqual(old_port,a.remote_proxy(outsider.client_id.hex()))
        self.assertEqual(old_port,a.remote_proxy(b.client_id.hex()))
