import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
import threading

from ingame_client import GameBridge, lua_value


class BridgeTests(unittest.TestCase):
    def test_lua_encoding_never_interpolates_names_as_code(self):
        value = lua_value(dict(name='"}; os.execute("bad") --\n\\é', ready=True, n=2))
        self.assertNotIn("os.execute", value)
        self.assertNotIn("é", value)
        self.assertIn("true", value)
        with self.assertRaises(ValueError):
            lua_value(1.5)

    def test_commands_bounded_allowlisted_and_not_replayed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "SzeroLAN.json").write_text('{"server_host":"localhost","name":"Tester"}')
            bridge = GameBridge(root, root / "lan_runtime_1.lua")
            sent=[]
            bridge.client=SimpleNamespace(connected=threading.Event(), send=lambda op, **fields: sent.append((op, fields)))
            bridge.client.connected.set()
            for value in ('x'*2049, '[]', '{', json.dumps(dict(serial=1,op="bad")),
                          json.dumps(dict(serial=2,op="join",lobby_id='"bad'))):
                bridge.command_path.write_text(value)
                bridge.command()
            self.assertEqual(sent, [])
            bridge.command_path.write_text(json.dumps(dict(serial=3,op="join",lobby_id="abcdef123456")))
            bridge.command(); bridge.command()
            self.assertEqual(sent, [("join", dict(lobby_id="abcdef123456"))])

    def test_wildcard_is_not_a_client_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "SzeroLAN.json").write_text('{"server_host":"0.0.0.0"}')
            with self.assertRaisesRegex(ValueError, "actual IP"):
                GameBridge(root, root / "lan_runtime_1.lua")
