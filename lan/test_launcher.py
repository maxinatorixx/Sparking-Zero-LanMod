import hashlib
import json
import os
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

import launcher
import installer


class InstallerTests(unittest.TestCase):
    def fixture(self, root):
        win64 = Path(root) / "SparkingZERO/Binaries/Win64"
        win64.mkdir(parents=True)
        original = b"test fixture, never a game executable"
        (win64 / "SparkingZERO-Win64-Shipping.exe").write_bytes(original)
        return win64, hashlib.sha256(original).hexdigest()

    def test_fresh_setup_installs_bundled_loader_and_only_lan_mod(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            win64, expected = self.fixture(root)
            runtime = Path(installer.install(root, expected))
            self.assertEqual(runtime, win64 / "Mods/SzeroLAN/scripts/lan_runtime.lua")
            for name in ("UE4SS.dll", "dwmapi.dll"):
                self.assertEqual((win64 / name).read_bytes()[:2], b"MZ")
            self.assertTrue((win64 / installer.SHARED_HELPER).is_file())
            self.assertEqual((win64 / "Mods/mods.txt").read_text(), "SzeroLAN : 1\n")
            self.assertFalse((win64 / "Mods/CheatManagerEnablerMod").exists())
            receipt = json.loads((win64 / "SzeroLAN-install.json").read_text())
            transaction = receipt["transactions"][0]
            self.assertEqual(transaction["loader"], "bundled 3.0.1")
            self.assertEqual(len(transaction["changes"]), 20)
            self.assertTrue((runtime.parent / "backend_adapter.dll").is_file())
            self.assertTrue(runtime.with_name("service_trace.dll").is_file())
            self.assertTrue(runtime.with_name("panel.lua").is_file())
            for name in ("audit.lua", "console_probe.dll", "native_menu.lua", "menu_bridge.dll",
                         "session_trace.lua", "session_probe.dll", "native_search.lua",
                         "native_search.dll"):
                self.assertTrue(runtime.with_name(name).is_file(), name)
            self.assertEqual(json.loads((root / "SzeroLAN.json").read_text())["name"], "Player")
            for record in transaction["changes"]:
                self.assertIsNone(record["before_sha256"])
                self.assertEqual(installer.digest(root / record["path"]), record["after_sha256"])
            (root / "SzeroLAN.json").write_text('{"server_host":"lan-host","name":"Keep me"}')
            installer.install(root, expected)
            receipt = json.loads((win64 / "SzeroLAN-install.json").read_text())
            self.assertEqual(receipt["transactions"][-1]["changes"], [])
            self.assertEqual(json.loads((root / "SzeroLAN.json").read_text())["name"], "Keep me")

    def test_existing_loader_settings_helpers_and_other_mods_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            win64, expected = self.fixture(root)
            helper = win64 / installer.SHARED_HELPER
            helper.parent.mkdir(parents=True)
            original = {win64 / "UE4SS.dll": b"existing loader version",
                        win64 / "UE4SS-settings.ini": b"[Custom]\nKeepMe=1\n",
                        helper: b"existing shared helper"}
            for path, content in original.items():
                path.write_bytes(content)
            mods = win64 / "Mods/mods.txt"
            mods.write_bytes(b"\xef\xbb\xbfOtherMod : 1\r\nSzeroLAN : 0\r\nKeybinds : 1\r\n")
            installer.install(root, expected)
            for path, content in original.items():
                self.assertEqual(path.read_bytes(), content)
            self.assertEqual(mods.read_bytes(), b"\xef\xbb\xbfOtherMod : 1\r\nSzeroLAN : 1\r\nKeybinds : 1\r\n")
            self.assertEqual(len(list(mods.parent.glob("mods.txt.*.bak"))), 1)
            self.assertFalse((win64 / "dwmapi.dll").exists())

    def test_unknown_proxy_conflict_leaves_files_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            win64, expected = self.fixture(root)
            proxy = win64 / "dwmapi.dll"
            proxy.write_bytes(b"another unrelated proxy loader")
            with self.assertRaisesRegex(ValueError, "unrelated dwmapi"):
                installer.install(root, expected)
            self.assertEqual(proxy.read_bytes(), b"another unrelated proxy loader")
            self.assertFalse((win64 / "UE4SS.dll").exists())
            self.assertFalse((win64 / "SzeroLAN-install.json").exists())

    def test_archive_hash_failure_makes_no_game_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            win64, expected = self.fixture(root)
            with patch.object(installer, "ARCHIVE_SHA256", "0" * 64):
                with self.assertRaisesRegex(ValueError, "checksum"):
                    installer.install(root, expected)
            self.assertEqual(len(list(win64.iterdir())), 1)

    def test_write_failure_rolls_back_loader_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            win64, expected = self.fixture(root)
            write = installer.atomic_write
            def fail_on_mod(path, data):
                if Path(path).name == "main.lua":
                    raise OSError("simulated write failure")
                return write(path, data)
            with patch.object(installer, "atomic_write", side_effect=fail_on_mod):
                with self.assertRaisesRegex(OSError, "simulated write"):
                    installer.install(root, expected)
            self.assertFalse((win64 / "UE4SS.dll").exists())
            self.assertFalse((win64 / "dwmapi.dll").exists())
            self.assertFalse((win64 / "SzeroLAN-install.json").exists())

    def test_install_paths_backup_and_hash_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            win64 = root / "SparkingZERO/Binaries/Win64"
            mods = win64 / "ue4ss/Mods"
            mods.mkdir(parents=True)
            exe = win64 / "SparkingZERO-Win64-Shipping.exe"
            original = b"test fixture, never a game executable"
            exe.write_bytes(original)
            (win64 / "ue4ss/UE4SS.dll").write_bytes(b"loader fixture")
            with self.assertRaises(ValueError):
                launcher.install_adapter(root)
            self.assertFalse((mods / "SzeroLAN").exists())
            with patch.object(launcher, "EXPECTED_EXE", hashlib.sha256(original).hexdigest()):
                runtime = Path(launcher.install_adapter(root))
                self.assertEqual(runtime, mods / "SzeroLAN/scripts/lan_runtime.lua")
                main = runtime.with_name("main.lua")
                self.assertIn("LoopAsync", main.read_text())
                main.write_text("previous adapter", encoding="utf-8")
                launcher.install_adapter(root)
                backups = list(main.parent.glob("main.lua.*.bak"))
                self.assertEqual(len(backups), 1)
                self.assertEqual(backups[0].read_text(), "previous adapter")
            self.assertEqual(exe.read_bytes(), original)


@unittest.skipUnless(os.name == "nt" or os.getenv("DISPLAY"), "requires display or Xvfb")
class WindowTests(unittest.TestCase):
    def test_lobby_window_renders_waiting_and_playing_members(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(launcher, "configure_logging"):
            config = Path(temp) / "client.json"
            config.write_text(json.dumps(dict(server_host="localhost", name="Alice")))
            root = tk.Tk()
            try:
                ui = launcher.Launcher(root, config)
                ui.state(dict(you="alice", lobby="finals", match=None, queued=False,
                              connected=4, queued_count=0, lobbies=[
                    dict(id="finals", name="Finals", in_match=True, players=[
                        dict(id="alice", name="Alice", ready=True, playing=False),
                        dict(id="bob", name="Bob", ready=False, playing=True)])]))
                root.update()
                self.assertIn("Alice (ready)", ui.members.get())
                self.assertIn("Bob (playing)", ui.members.get())
                self.assertEqual(ui.ready_button.cget("text"), "Not ready")
                self.assertEqual(ui.lobbies.item("finals")["values"][0], "Finals")
                self.assertIn("4 players", ui.status.get())
                from types import SimpleNamespace
                import queue
                import threading
                ui.client = SimpleNamespace(
                    udp_ready=threading.Event(), assignment={"match_id": "a" * 32},
                    adapter_status=dict(stage="commands_issued", detail="Waiting for battle entry"),
                    game_packets_sent=3, game_packets_received=2, events=queue.Queue())
                ui.client.udp_ready.set()
                ui.poll()
                self.assertIn("commands_issued", ui.adapter_status.get())
                self.assertIn("3 sent / 2 received", ui.data_status.get())
                self.assertNotIn("battle started", ui.adapter_status.get().lower())
            finally:
                root.destroy()


if __name__ == "__main__":
    unittest.main()
