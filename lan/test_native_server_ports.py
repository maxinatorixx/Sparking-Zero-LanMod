import asyncio
import errno
import unittest
from unittest.mock import AsyncMock, Mock, patch

from szero_lan import GameServer, LobbyClient


class ServerPortTests(unittest.IsolatedAsyncioTestCase):
    async def test_ephemeral_udp_tcp_collision_retries_without_leaking_transport(self):
        transports = [Mock(), Mock()]
        for value, port in zip(transports, (31001, 31002)):
            value.get_extra_info.return_value = ("127.0.0.1", port)
        endpoint = AsyncMock(side_effect=[(transports[0], None), (transports[1], None)])
        listen = AsyncMock(side_effect=[OSError(errno.EADDRINUSE, "fixture collision"), Mock()])
        with patch.object(asyncio.get_running_loop(), "create_datagram_endpoint", endpoint), patch("szero_lan.asyncio.start_server", listen):
            server = await GameServer("127.0.0.1", 0).start()
        self.assertEqual(server.port, 31002)
        self.assertEqual(endpoint.await_count, 2)
        transports[0].close.assert_called_once()
        transports[1].close.assert_not_called()
        self.assertEqual([call.kwargs["local_addr"] for call in endpoint.await_args_list], [("127.0.0.1", 0)]*2)

    async def test_explicit_port_collision_is_reported_without_changing_port(self):
        transport = Mock()
        transport.get_extra_info.return_value = ("127.0.0.1", 27150)
        endpoint = AsyncMock(return_value=(transport, None))
        listen = AsyncMock(side_effect=OSError(errno.EADDRINUSE, "fixture collision"))
        with patch.object(asyncio.get_running_loop(), "create_datagram_endpoint", endpoint), patch("szero_lan.asyncio.start_server", listen):
            server = GameServer("127.0.0.1", 27150)
            with self.assertRaises(OSError):
                await server.start()
        self.assertEqual(server.port, 27150)
        self.assertIsNone(server.transport)
        self.assertEqual(endpoint.await_count, 1)
        transport.close.assert_called_once()

    async def test_native_local_port_validation_precedes_network(self):
        for value in (True, 0, -1, 65536, "30001"):
            for option in ("game_port", "proxy_port"):
                with self.subTest(value=value, option=option), self.assertRaises(ValueError):
                    LobbyClient("127.0.0.1", **{option: value})
