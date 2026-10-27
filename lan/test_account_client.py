"""Game-port authentication and explicit remembered-session UI contracts."""
import asyncio
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import MagicMock, patch

import account_client
import setup_launcher
from account_store import AccountStore
from szero_lan import GameServer
from test_setup_launcher import native_fixture

PROFILE = {"username": "vegeta", "display_name": "Prince Vegeta"}
TOKEN = "t" * 43


class AccountClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_game_server_login_and_remembered_session(self):
        store = AccountStore.for_sqlite(admin_token="setup-secret")
        registration = store.register("vegeta", "aa", "setup-secret")
        store.update_profile(registration["token"], "Prince Vegeta", "four-star", "orange")
        server = await GameServer("127.0.0.1", 0, store).start()
        try:
            token, profile = await asyncio.to_thread(account_client.authenticate, "127.0.0.1", server.port, "vegeta", "aa")
            self.assertEqual(profile["display_name"], "Prince Vegeta")
            self.assertEqual((await asyncio.to_thread(account_client.authenticate, "127.0.0.1", server.port, "vegeta", "", token))[1], profile)
            self.assertFalse(server.peers)
            store.logout(token)
            with self.assertRaisesRegex(ValueError, "expired"):
                await asyncio.to_thread(account_client.authenticate, "127.0.0.1", server.port, "vegeta", "", token)
        finally:
            await server.close()
            store.close()

    async def test_wire_uses_game_account_protocol_and_refuses_wrong_identity(self):
        captured = []
        async def client(reader, writer):
            captured.append(json.loads(await reader.readline()))
            writer.write((json.dumps({"event": "account", "state": "ok", "token": TOKEN, "profile": PROFILE}) + "\n").encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        server = await asyncio.start_server(client, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        try:
            await asyncio.to_thread(account_client.authenticate, "127.0.0.1", port, "vegeta", "aa")
            await asyncio.to_thread(account_client.authenticate, "127.0.0.1", port, "vegeta", "", TOKEN)
            with self.assertRaisesRegex(ValueError, "profile"):
                await asyncio.to_thread(account_client.authenticate, "127.0.0.1", port, "goku", "", TOKEN)
        finally:
            server.close()
            await server.wait_closed()
        self.assertEqual(captured[0], {"op": "account", "version": 2, "action": "login", "username": "vegeta", "password": "aa"})
        self.assertEqual(captured[1], {"op": "account", "version": 2, "action": "me", "token": TOKEN})

    async def test_malformed_refused_and_oversized_replies_fail_closed(self):
        for reply in (b"not-json\n", b"{}\n", b"x" * 65537,
                      b'{"event":"account","state":"error","message":"DO-NOT-ECHO"}\n'):
            connection = MagicMock()
            connection.__enter__.return_value = connection
            connection.makefile.return_value = io.BytesIO(reply)
            with self.subTest(reply=reply[:80]), patch.object(account_client.socket, "create_connection", return_value=connection):
                with self.assertRaises(ValueError) as error:
                    account_client.authenticate("localhost", 27150, "vegeta", "aa")
                self.assertNotIn("DO-NOT-ECHO", str(error.exception))
        for password in ("", "a"):
            with self.subTest(password=password), self.assertRaises(ValueError):
                account_client.authenticate("localhost", 27150, "vegeta", password)

    async def test_account_preflight_requires_server_authentication(self):
        cfg = {"server_host": "localhost", "server_port": 27150, "account_mode": "login", "account_token": TOKEN}
        welcome = {"event": "welcome", "capabilities": {"native_session_versions": [2], "native_session_transactions": 1, "native_lan_identity": 1}}
        for account in (None, {"authenticated": False, "ranked": True}, {"authenticated": True, "ranked": False}, {"authenticated": True, "ranked": True}):
            connection = MagicMock()
            connection.__enter__.return_value = connection
            connection.makefile.return_value = io.BytesIO((json.dumps(dict(welcome, account=account)) + "\n").encode())
            with self.subTest(account=account), patch.object(setup_launcher.socket, "create_connection", return_value=connection):
                if account and account["authenticated"] and account["ranked"]:
                    setup_launcher.probe_native_server(cfg)
                else:
                    with self.assertRaisesRegex(ValueError, "authenticate"):
                        setup_launcher.probe_native_server(cfg)


@unittest.skipUnless(os.name == "nt" or os.getenv("DISPLAY"), "requires display or Xvfb")
class AccountLauncherTests(unittest.TestCase):
    @contextlib.contextmanager
    def launcher(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "SparkingZERO.exe").write_bytes(b"fixture")
            expected = native_fixture(folder)
            (folder / "SzeroLAN.json").write_text('{"server_host":"localhost","name":"Guest","account_url":"http://retired.example"}')
            settings = folder / "launcher.json"
            settings.write_text(json.dumps({"game_directory": str(folder), "adapter_runtime": str(folder / "scripts/lan_runtime.lua")}))
            root = tk.Tk()
            try:
                ui = setup_launcher.SetupLauncher(root, settings)
                yield ui, folder, settings, expected
            finally:
                root.destroy()

    def login(self, ui):
        ui.account_mode.set("Account login")
        ui.account_username.set("vegeta")
        ui.account_password.set("aa")
        with patch.object(setup_launcher, "authenticate", return_value=(TOKEN, PROFILE)) as auth:
            ui.login_button.invoke()
        auth.assert_called_once_with("localhost", 27150, "vegeta", "aa", "")

    def test_explicit_login_remembers_session_only_and_restores_without_password(self):
        with self.launcher() as (ui, folder, settings, expected):
            config = folder / "SzeroLAN.json"
            before = config.read_bytes()
            ui.wine_prefix.set("/tmp/unsaved-draft-prefix")
            self.assertEqual(ui.player_tabs.tab(0, "text"), "Quick play")
            self.assertEqual(ui.player_tabs.tab(1, "text"), "Login")
            self.assertFalse(hasattr(ui, "account_website"))
            self.login(ui)
            self.assertEqual(config.read_bytes(), before)
            private = json.loads(settings.read_text())
            self.assertEqual(private["account"], {"host": "localhost", "port": 27150, "username": "vegeta", "token": TOKEN, "mode": "login"})
            self.assertNotIn("launch_options", private)
            self.assertEqual(ui.account_password.get(), "")
            self.assertEqual(ui.name.get(), "Prince Vegeta")
            if os.name != "nt":
                self.assertEqual(settings.stat().st_mode & 0o777, 0o600)
            second = tk.Toplevel(ui.root)
            restored = setup_launcher.SetupLauncher(second, settings)
            self.assertEqual(restored.account_username.get(), "vegeta")
            self.assertEqual(restored.account_password.get(), "")
            self.assertEqual(restored._account_token, TOKEN)
            self.assertEqual(restored.account_mode.get(), "Account login")
            second.destroy()

    def test_launch_rechecks_confirmed_token_and_saves_everything_before_processes(self):
        with self.launcher() as (ui, folder, settings, expected):
            self.login(ui)
            ui.mod_logging.set(True)
            started = []
            bridge = MagicMock()
            bridge.poll.return_value = None
            def spawn(*args, **kwargs):
                saved = json.loads((folder / "SzeroLAN.json").read_text())
                self.assertEqual(saved["name"], "Prince Vegeta")
                self.assertEqual(saved["account_mode"], "login")
                self.assertNotIn("account_token", saved)
                self.assertNotIn("account_url", saved)
                self.assertNotIn("password", json.dumps(saved))
                self.assertEqual(json.loads(settings.read_text())["account"]["token"], TOKEN)
                started.append(kwargs)
                return bridge if len(started) == 1 else MagicMock()
            with patch.object(setup_launcher, 'authenticate', return_value=(TOKEN, PROFILE)) as auth, patch.object(setup_launcher, 'probe_native_server'), patch.object(setup_launcher.subprocess, 'Popen', side_effect=spawn):
                ui.launch()
            auth.assert_called_once_with("localhost", 27150, "vegeta", "", TOKEN)
            self.assertEqual(started[0]["env"]["SZERO_ARENA_ACCOUNT_TOKEN"], TOKEN)
            self.assertNotIn("SZERO_ARENA_ACCOUNT_TOKEN", started[1]["env"])
            self.assertEqual(started[1]["env"]["SZERO_LAN_SERVICE_TRACE"], "1")
            ui.stop_bridge()

    def test_launch_authenticates_current_password_before_saves_without_login_click(self):
        with self.launcher() as (ui, folder, settings, expected):
            ui.account_mode.set("Account login")
            ui.account_username.set("vegeta")
            ui.account_password.set("current-password")
            config = folder / "SzeroLAN.json"
            config_before, prefs_before = config.read_bytes(), settings.read_bytes()
            ini = folder / "SparkingZERO/Binaries/Win64/steam_emu.ini"
            ini.write_bytes(b"UserName=old\r\n")
            order = []
            def check_credentials(*arguments):
                self.assertEqual(arguments, ("localhost", 27150, "vegeta", "current-password", ""))
                self.assertEqual(config.read_bytes(), config_before)
                self.assertEqual(settings.read_bytes(), prefs_before)
                self.assertEqual(ini.read_bytes(), b"UserName=old\r\n")
                order.append("login")
                return TOKEN, PROFILE
            bridge = MagicMock()
            bridge.poll.return_value = None
            def spawn(*args, **kwargs):
                self.assertEqual(order[0], "login")
                self.assertEqual(json.loads(config.read_text())["account_mode"], "login")
                self.assertEqual(json.loads(settings.read_text())["account"]["token"], TOKEN)
                self.assertEqual(ini.read_bytes(), b"UserName=Prince Vegeta\r\n")
                self.assertEqual(kwargs["env"]["SZERO_LAN_MOD_LOGGING"], "0")
                order.append("spawn")
                return bridge if len(order) == 2 else MagicMock()
            with patch.object(setup_launcher, 'authenticate', side_effect=check_credentials) as auth, patch.object(setup_launcher, 'probe_native_server'), patch.object(setup_launcher.subprocess, 'Popen', side_effect=spawn):
                ui.launch()
            auth.assert_called_once()
            self.assertEqual(order, ["login", "spawn", "spawn"])
            self.assertEqual(ui.account_password.get(), "")
            self.assertNotIn("current-password", settings.read_text())
            self.assertFalse(json.loads(config.read_text())["launch_options"]["mod_logging"])
            ui.stop_bridge()

    def test_credential_edits_are_checked_on_launch_and_fail_before_any_save(self):
        with self.launcher() as (ui, folder, settings, expected):
            self.login(ui)
            for variable, changed, original in ((ui.host, "other-server", "localhost"), (ui.port, "27151", "27150"), (ui.account_username, "goku", "vegeta"), (ui.account_password, "bb", "")):
                variable.set(changed)
                config_before = (folder / "SzeroLAN.json").read_bytes()
                prefs_before = settings.read_bytes()
                ini = folder / "SparkingZERO/Binaries/Win64/steam_emu.ini"
                ini.write_bytes(b"UserName=unchanged\r\n")
                with patch.object(setup_launcher, "authenticate", side_effect=ValueError("Credentials refused")) as auth, \
                     patch.object(setup_launcher, "probe_native_server") as preflight, \
                     patch.object(setup_launcher.subprocess, "Popen") as spawn, \
                     patch.object(setup_launcher.messagebox, "showerror") as error:
                    ui.launch()
                auth.assert_called_once()
                self.assertEqual(auth.call_args.args[3], ui.account_password.get())
                spawn.assert_not_called()
                preflight.assert_not_called()
                self.assertIn("Login failed", error.call_args.args[1])
                self.assertEqual((folder / "SzeroLAN.json").read_bytes(), config_before)
                self.assertEqual(settings.read_bytes(), prefs_before)
                self.assertEqual(ini.read_bytes(), b"UserName=unchanged\r\n")
                self.assertIsNone(ui._login_scope)
                variable.set(original)
            ui.host.set("other-server")
            ui.account_password.set("")
            self.assertEqual(ui.remembered_account(), "")

    def test_quick_play_keeps_remembered_login_private_and_skips_auth(self):
        with self.launcher() as (ui, folder, settings, expected):
            self.login(ui)
            ui.player_tabs.select(0)
            ui.root.update()
            self.assertEqual(ui.account_mode.get(), "Quick play")
            self.assertNotIn("disabled", ui.logging_checkbox.state())
            with patch.object(setup_launcher, "authenticate") as auth:
                saved = ui.save_fields()
            auth.assert_not_called()
            self.assertEqual(saved["account_mode"], "quick")
            self.assertEqual(json.loads(settings.read_text())["account"]["token"], TOKEN)

    def test_missing_or_old_backend_refuses_before_processes_even_without_diagnostics(self):
        with self.launcher() as (ui, folder, settings, expected):
            dll = folder / "scripts/backend_adapter.dll"
            dll.write_bytes(b"outdated backend3")
            with patch.object(setup_launcher, 'probe_native_server') as probe, patch.object(setup_launcher.subprocess, 'Popen') as spawn, patch.object(setup_launcher.messagebox, 'showerror') as error:
                ui.launch()
            self.assertIn("reinstall", error.call_args.args[1])
            probe.assert_not_called()
            spawn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
