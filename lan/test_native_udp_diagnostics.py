"""First-event UDP metadata is bounded and never proves native battle readiness."""
import time
import unittest
from unittest.mock import Mock

from szero_lan import GameServer, Peer, REGISTER, DATA, ZERO, packet, unpack


class NativeUDPDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.server = GameServer("127.0.0.1", 27150)
        self.server.transport = Mock()
        self.a = Peer("a" * 32, "A", None, "127.0.0.1")
        self.b = Peer("b" * 32, "B", None, "127.0.0.1")
        self.server.peers = {self.a.id: self.a, self.b.id: self.b}
        self.source = ("127.0.0.1", 32001)

    def test_registration_is_not_game_data_and_only_logs_first(self):
        with self.assertLogs("szero_lan", level="INFO") as logged:
            for _ in range(20):
                self.server.datagram_received(packet(REGISTER, bytes.fromhex(self.a.id)), self.source)
        self.assertEqual(len(logged.output), 1)
        self.assertIn("result=registered bytes=0", logged.output[0])
        self.assertEqual(self.server.transport.sendto.call_count, 20)
        self.assertEqual(self.a.udp_diagnostics, {"registered"})

    def test_no_route_logs_size_not_payload_and_never_forwards(self):
        self.a.udp = self.source
        body = b"PRIVATE-GAME-BYTES"
        with self.assertLogs("szero_lan", level="INFO") as logged:
            for number in range(20):
                frame = packet(DATA, bytes.fromhex(self.a.id), number.to_bytes(16, "big"), body)
                self.server.datagram_received(frame, self.source)
        self.assertEqual(len(logged.output), 1)
        self.assertIn("result=no_route bytes=18", logged.output[0])
        self.assertNotIn(body.decode(), logged.output[0])
        self.assertNotIn(str(self.source), logged.output[0])
        self.server.transport.sendto.assert_not_called()

    def test_forwarding_and_peer_unavailable_are_distinct_bounded_events(self):
        sid = "c" * 32
        self.a.udp, self.a.match = self.source, sid
        self.server.matches[sid] = {"players": [self.a.id, self.b.id]}
        body = b"private"
        frame = packet(DATA, bytes.fromhex(self.a.id), bytes.fromhex(sid), body)
        with self.assertLogs("szero_lan", level="INFO") as logged:
            self.server.datagram_received(frame, self.source)
            self.b.udp, self.b.udp_seen = ("127.0.0.1", 32002), time.monotonic()
            for _ in range(20):
                self.server.datagram_received(frame, self.source)
        self.assertEqual(len(logged.output), 2)
        self.assertIn("result=peer_unavailable", logged.output[0])
        self.assertIn("result=forwarded bytes=7", logged.output[1])
        self.assertEqual(self.server.transport.sendto.call_count, 20)
        forwarded, address = self.server.transport.sendto.call_args.args
        self.assertEqual(unpack(forwarded), (DATA, self.b.id, sid, body))
        self.assertEqual(address, self.b.udp)
        self.assertNotIn("private", "\n".join(logged.output))
        self.assertLessEqual(len(self.a.udp_diagnostics), 4)

    def test_wrong_udp_source_is_still_rejected(self):
        self.a.udp = self.source
        self.server.datagram_received(packet(DATA, bytes.fromhex(self.a.id), ZERO, b"x"),
                                      ("127.0.0.1", 32003))
        self.assertFalse(self.a.udp_diagnostics)
        self.server.transport.sendto.assert_not_called()

    def test_end_summary_counts_all_forwarded_sizes_without_packet_contents(self):
        sid = "c"*32
        self.a.udp, self.a.match = self.source, sid
        self.b.udp, self.b.udp_seen = ("127.0.0.1", 32002), time.monotonic()
        self.server.matches[sid] = {"players": [self.a.id,self.b.id]}
        with self.assertLogs("szero_lan", level="INFO") as logged:
            for body in (b"xx",b"PRIVATE-GAME-BYTES",b"xx"):
                self.server.datagram_received(packet(DATA, bytes.fromhex(self.a.id), bytes.fromhex(sid),body),self.source)
            self.server.trace_udp_summary(self.a)
            self.server.trace_udp_summary(self.a)
        self.assertEqual(len(logged.output),2)
        self.assertIn("forwarded_packets=3 forwarded_bytes=22 smallest=2 largest=18", logged.output[1])
        self.assertNotIn("PRIVATE", "\n".join(logged.output))
        self.assertEqual(self.a.udp_packets,0)
