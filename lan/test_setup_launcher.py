import json
import hashlib
import io
import os
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch, MagicMock

import setup_launcher


def native_fixture(folder):
    scripts = folder / "scripts"
    scripts.mkdir(exist_ok=True)
    for filename in ("native_search.lua", "native_search.dll", "service_trace.dll", "backend_adapter.dll"):
        (scripts / filename).write_bytes((setup_launcher.ROOT / "ue4ss/SzeroLAN/scripts" / filename).read_bytes())
    shipping = folder / "SparkingZERO/Binaries/Win64/SparkingZERO-Win64-Shipping.exe"
    shipping.parent.mkdir(parents=True, exist_ok=True)
    shipping.write_bytes(b"owned shipping test fixture")
    return hashlib.sha256(shipping.read_bytes()).hexdigest()


class ConnectionConfigTests(unittest.TestCase):
    def test_optional_ini_username_only_and_first_backup_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            self.assertFalse(setup_launcher.sync_player_name(folder,"Vegeta"))
            self.assertEqual(list(folder.iterdir()),[])
            path=folder/"SparkingZERO/Binaries/Win64/steam_emu.ini"
            path.parent.mkdir(parents=True)
            original=b"[Settings]\r\n;UserName=comment\r\nUserName=Old\r\n UserName=indented\nOther=keep\nUserName=duplicate"
            path.write_bytes(original)
            self.assertTrue(setup_launcher.sync_player_name(folder," Vegeta "))
            self.assertEqual(path.read_bytes(),original.replace(b"UserName=Old",b"UserName=Vegeta").replace(b"UserName=duplicate",b"UserName=Vegeta"))
            backup=path.with_name(path.name+".szero-name.bak")
            self.assertEqual(backup.read_bytes(),original)
            self.assertFalse(setup_launcher.sync_player_name(folder,"Vegeta"))
            self.assertTrue(setup_launcher.sync_player_name(folder,"Goku"))
            self.assertEqual(backup.read_bytes(),original)

    def test_ini_encodings_and_missing_key_preserve_unrelated_bytes(self):
        for bom,encoding in ((b"","utf-8"),(b"\xef\xbb\xbf","utf-8"),
                             (b"\xff\xfe","utf-16-le"),(b"\xfe\xff","utf-16-be"),
                             (b"","cp1252")):
            with self.subTest(encoding=encoding,bom=bom), tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/"SparkingZERO/Binaries/Win64/steam_emu.ini"
                path.parent.mkdir(parents=True)
                text="UserName=Old\r\nComment=café\r\n"
                path.write_bytes(bom+text.encode(encoding))
                setup_launcher.sync_player_name(temp,"Végéta")
                self.assertEqual(path.read_bytes(),bom+text.replace("UserName=Old","UserName=Végéta").encode(encoding))
                original=bom+";UserName=comment\r\nOther=keep".encode(encoding)
                path.write_bytes(original)
                self.assertFalse(setup_launcher.sync_player_name(temp,"Goku"))
                self.assertEqual(path.read_bytes(),original)

    def test_ini_invalid_input_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"SparkingZERO/Binaries/Win64/steam_emu.ini"
            path.parent.mkdir(parents=True)
            for original,name in ((b"UserName=old\n","bad\nname"),
                                  (b"UserName=old\nOther=caf\xe9", "悟空"),
                                  (b"\xff\xfeX","Goku"),(b"\x00text","Goku"),
                                  (b"x"*(1024*1024+1),"Goku")):
                path.write_bytes(original)
                with self.subTest(name=name,size=len(original)),self.assertRaises(ValueError):
                    setup_launcher.sync_player_name(temp,name)
                self.assertEqual(path.read_bytes(),original)
                self.assertFalse(path.with_name(path.name+".szero-name.bak").exists())

    def test_valid_hosts_ports_and_trimmed_name(self):
        for host in ("192.168.1.20", "127.0.0.1", "localhost", "TOURNAMENT-PC", "lan.example."):
            with self.subTest(host=host):
                cfg = setup_launcher.config_with_fields({"native_menu": True, "extra": [1]},
                                                        " " + host + " ", "65535", " Player 1 ")
                self.assertEqual(cfg, dict(native_menu=True, extra=[1], server_host=host,
                                           server_port=65535, name="Player 1", native_session=True, native_search=True))

    def test_invalid_destination_port_and_name(self):
        for host in ("", "0.0.0.0", "0", "127.1", "999.1.2.3", "192.168.01.1",
                     "http://server", "server:27150", "bad name", "-bad", "bad..host", "host..",
                     "::1", "255.255.255.255", "224.1.2.3", "x" * 64):
            with self.subTest(host=host), self.assertRaises(ValueError):
                setup_launcher.config_with_fields({}, host, "27150", "Player")
        for port in ("0", "65536", "1.0", "True", "-1", "999999999999999"):
            with self.subTest(port=port), self.assertRaises(ValueError):
                setup_launcher.config_with_fields({}, "localhost", port, "Player")
        for name in ("", "\n", "x" * 49, "a\nb"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                setup_launcher.config_with_fields({}, "localhost", "1", name)

    def test_read_does_not_create_or_modify_and_save_preserves_unknown_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            path = folder / "SzeroLAN.json"
            self.assertEqual(setup_launcher.read_editor_config(folder), {})
            self.assertFalse(path.exists())
            original = b'{"native_menu":true,"extra":{"keep":123},"server_port":"broken"}'
            path.write_bytes(original)
            self.assertEqual(setup_launcher.read_editor_config(folder)["server_port"], "broken")
            self.assertEqual(path.read_bytes(), original)
            cfg = setup_launcher.save_editor_config(folder, "new-host", "12345", "New player")
            self.assertEqual(json.loads(path.read_text()), cfg)
            self.assertTrue(cfg["native_menu"])
            self.assertEqual(cfg["extra"], {"keep": 123})
            self.assertEqual(cfg["server_port"], 12345)
            self.assertEqual(list(folder.glob("*.tmp")), [])

    def test_invalid_config_or_fields_never_overwrites_file(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            path = folder / "SzeroLAN.json"
            for original in (b"[]", b"broken", b'{"native_menu":"yes"}',
                             b'{"native_search":"yes"}', b'{"native_search":1}',
                             b'{"native_session":"yes"}'):
                path.write_bytes(original)
                with self.assertRaises(ValueError):
                    setup_launcher.save_editor_config(folder, "localhost", "27150", "Player")
                self.assertEqual(path.read_bytes(), original)
            original = b'{"extra":true}'
            path.write_bytes(original)
            with self.assertRaises(ValueError):
                setup_launcher.save_editor_config(folder, "0.0.0.0", "27150", "Player")
            self.assertEqual(path.read_bytes(), original)

    def test_old_mode_flags_migrate_to_only_supported_native_path(self):
        for original in ({}, {"native_search": False}, {"native_search": False, "native_session": False},
                         {"native_search": True, "native_session": False}):
            cfg = setup_launcher.config_with_fields(
                dict(original, unrelated={"keep": 123}), "localhost", "27150", "Player")
            self.assertTrue(cfg["native_search"])
            self.assertTrue(cfg["native_session"])
            self.assertEqual(cfg["unrelated"], {"keep": 123})

    def test_native_preflight_rejects_absent_old_and_malformed_servers(self):
        cfg = {"server_host": "localhost", "server_port": 27150}
        with patch.object(setup_launcher.socket, "create_connection", side_effect=OSError("offline")):
            with self.assertRaisesRegex(ValueError, "preflight failed"):
                setup_launcher.probe_native_server(cfg)
        for frame in (b"[]\n", b"not-json\n", b"x"*8193,
                      b'{"event":"welcome","capabilities":{"native_session_versions":[2],"native_session_transactions":1}}\n',
                      b'{"event":"welcome","capabilities":{"native_session_versions":[2],"native_session_transactions":1,"native_lan_identity":true}}\n',
                      b'{"event":"welcome","capabilities":{"native_session_versions":[2],"native_session_transactions":true}}\n',
                      b'{"event":"welcome","capabilities":{"native_session_versions":[1],"native_session_transactions":1}}\n'):
            connection = MagicMock()
            connection.__enter__.return_value = connection
            connection.makefile.return_value = io.BytesIO(frame)
            with self.subTest(frame=frame[:40]), patch.object(setup_launcher.socket, "create_connection", return_value=connection):
                with self.assertRaises(ValueError):
                    setup_launcher.probe_native_server(cfg)


@unittest.skipUnless(os.name == "nt" or os.getenv("DISPLAY"), "requires display or Xvfb")
class SetupWindowTests(unittest.TestCase):
    def test_select_game_accepts_unrelated_executable_without_hashing(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "SparkingZERO.exe").write_bytes(b"launcher fixture")
            shipping = folder / "SparkingZERO/Binaries/Win64/SparkingZERO-Win64-Shipping.exe"
            shipping.parent.mkdir(parents=True)
            shipping.write_bytes(b"unrelated executable bytes")
            root = tk.Tk()
            try:
                ui = setup_launcher.SetupLauncher(root, folder / "prefs.json")
                with patch.object(setup_launcher.filedialog, "askdirectory", return_value=str(folder)), \
                     patch.object(setup_launcher, "digest", side_effect=AssertionError("Selection must not hash EXE")), \
                     patch.object(setup_launcher.messagebox, "showerror") as error:
                    ui.select_game()
                error.assert_not_called()
                self.assertEqual(ui.selected_game(), True)
                self.assertEqual(ui.settings["game_directory"], str(folder.resolve()))
            finally:
                root.destroy()

    def test_player_tabs_keep_equal_geometry_and_display_fields_are_absent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = tk.Tk()
            try:
                ui = setup_launcher.SetupLauncher(root, Path(temporary) / "prefs.json")
                root.update()
                notebook = ui.player_tabs
                for selected in (0, 1):
                    for tab in (0, 1):
                        notebook.tab(tab, state="normal")
                    notebook.select(selected)
                    root.update()
                    spans = {0: [], 1: []}
                    for x in range(notebook.winfo_width()):
                        try:
                            tab = notebook.index(f"@{x},20")
                        except tk.TclError:
                            continue
                        spans[tab].append(x)
                    self.assertTrue(spans[0])
                    self.assertEqual(len(spans[0]), len(spans[1]))
                labels = []
                def inspect(widget):
                    if "text" in widget.keys():
                        labels.append(str(widget.cget("text")))
                    for child in widget.winfo_children():
                        inspect(child)
                inspect(root)
                self.assertNotIn("DISPLAY MODE", labels)
                self.assertNotIn("RESOLUTION", labels)
                self.assertEqual(ui.current_options()["display"], "Game default")
                self.assertEqual(ui.current_options()["resolution"], "Game default")
                self.assertIn("Enable mod logging", labels)
                self.assertFalse(ui.mod_logging.get())
            finally:
                root.destroy()

    def test_unselected_controls_and_save_confirmation(self):
        import savegame
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            root = tk.Tk()
            try:
                ui = setup_launcher.SetupLauncher(root, folder / 'setup.json')
                self.assertNotIn('disabled', ui.select_button.state())
                self.assertIn('disabled', ui.mod_button.state())
                self.assertIn('disabled', ui.launch_button.state())
                self.assertFalse(hasattr(ui, 'dx11'))
                self.assertFalse(hasattr(ui, 'skip_splash'))
                self.assertFalse(hasattr(ui, 'display_mode'))
                self.assertFalse(hasattr(ui, 'resolution'))
                self.assertFalse(hasattr(ui, 'stutter_button'))
                self.assertFalse(hasattr(ui, 'toggle_stutter'))
                plan = MagicMock(summary='Characters: 3 to unlock')
                with patch.object(ui, 'require_idle'), \
                     patch.object(setup_launcher.filedialog, 'askopenfilename', return_value=str(folder/'MainGameSaveData')), \
                     patch.object(savegame, 'plan_unlock', return_value=plan), \
                     patch.object(savegame, 'apply_unlock') as apply, \
                     patch.object(setup_launcher.messagebox, 'askyesno', return_value=False), \
                     patch.object(setup_launcher.messagebox, 'showerror') as error:
                    ui.settings['game_directory'] = str(folder)
                    ui.unlock_save('characters')
                    apply.assert_not_called()
                    error.assert_not_called()
                with patch.object(ui, 'require_idle'), \
                     patch.object(setup_launcher.filedialog, 'askopenfilename', return_value=str(folder/'MainGameSaveData')), \
                     patch.object(savegame, 'plan_unlock', return_value=plan), \
                     patch.object(savegame, 'apply_unlock', return_value=MagicMock(changed_rows=3,backup_path=folder/'backup')) as apply, \
                     patch.object(setup_launcher.messagebox, 'askyesno', return_value=True):
                    ui.unlock_save('characters')
                    apply.assert_called_once_with(plan, confirmed=True, game_running=setup_launcher.game_running)
            finally:
                root.destroy()

    def test_setup_save_launch_actions_and_unique_instance_environment(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "SparkingZERO.exe").write_bytes(b"fixture")
            (folder / "SzeroLAN.json").write_text('{"server_host":"localhost","name":"Tester","launch_options":{"display":"Windowed","resolution":"1920x1080"}}')
            scripts = folder / "scripts"
            scripts.mkdir()
            (scripts / "panel.lua").write_text("fixture")
            expected = native_fixture(folder)
            settings = folder / "setup.json"
            settings.write_text(json.dumps(dict(game_directory=str(folder),
                                                adapter_runtime=str(scripts / "lan_runtime.lua"))))
            root = tk.Tk()
            try:
                ui = setup_launcher.SetupLauncher(root, settings)
                self.assertIn("SELECT", ui.select_button.cget("text"))
                self.assertIn("LAUNCH", ui.launch_button.cget("text"))
                self.assertFalse(hasattr(ui, "dx11"))
                self.assertFalse(hasattr(ui, "native_session"))  # No unsupported mode selector.
                self.assertEqual(ui.host.get(), "localhost")
                self.assertEqual(ui.name.get(), "Tester")
                self.assertEqual(ui.port.get(), "27150")
                ui.host.set("tournament-pc")
                ui.port.set("27200")
                ui.name.set("Vegeta")
                ui.mod_logging.set(True)
                self.assertFalse(hasattr(ui, "display_mode"))
                self.assertFalse(hasattr(ui, "resolution"))
                ini=folder/"SparkingZERO/Binaries/Win64/steam_emu.ini"
                ini.write_bytes(b"UserName=old\r\nOther=unchanged\r\n")
                bridge = MagicMock()
                bridge.poll.return_value = None
                started=[]
                def start_process(*args, **kwargs):
                    # Both writes must be complete before even the bridge starts.
                    saved=json.loads((folder/"SzeroLAN.json").read_text())
                    self.assertEqual(saved["name"],"Vegeta")
                    self.assertEqual(saved["server_host"],"tournament-pc")
                    self.assertEqual(saved["launch_options"]["display"],"Game default")
                    self.assertEqual(saved["launch_options"]["resolution"],"Game default")
                    self.assertEqual(ini.read_bytes(),b"UserName=Vegeta\r\nOther=unchanged\r\n")
                    self.assertEqual(json.loads(settings.read_text())["game_directory"],str(folder))
                    started.append(args)
                    return bridge if len(started)==1 else MagicMock()
                with patch.dict(os.environ, {'SZERO_LAN_NATIVE_TRACE': '1'}), patch.object(setup_launcher, 'probe_native_server'), patch.object(setup_launcher.subprocess, 'Popen', side_effect=start_process) as popen:
                    ui.launch()
                self.assertEqual(popen.call_count, 2)
                headless, game = popen.call_args_list
                self.assertIn("ingame_client.py", headless.args[0][1])
                instance = game.kwargs["env"]["SZERO_LAN_INSTANCE"]
                self.assertEqual(ui.runtime.name, f"lan_runtime_{instance}.lua")
                self.assertEqual(len(instance), 32)
                self.assertEqual(game.kwargs["env"]["SZERO_LAN_NATIVE_MENU"], "0")
                self.assertEqual(game.kwargs["env"]["SZERO_LAN_NATIVE_SEARCH"], "1")
                self.assertEqual(game.kwargs["env"]["SZERO_LAN_NATIVE_SESSION3"], "1")
                self.assertEqual(game.kwargs["env"]["SZERO_LAN_SERVICE_TRACE"], "1")
                self.assertEqual(game.kwargs["env"]["SZERO_LAN_MOD_LOGGING"], "1")
                self.assertEqual(headless.kwargs["env"]["SZERO_LAN_MOD_LOGGING"], "1")
                self.assertEqual(game.kwargs["env"]["SZERO_LAN_NATIVE_TRACE"], "1")
                config = json.loads((folder / "SzeroLAN.json").read_text())
                self.assertEqual(config["server_host"], "tournament-pc")
                self.assertEqual(config["server_port"], 27200)
                self.assertEqual(config["name"], "Vegeta")
                self.assertEqual(config["launch_options"]["display"], "Game default")
                self.assertEqual(config["launch_options"]["resolution"], "Game default")
                self.assertNotIn("-windowed", game.args[0])
                self.assertNotIn("-ResX=1920", game.args[0])
                self.assertTrue(config["launch_options"]["service_trace"])
                self.assertTrue(config["launch_options"]["mod_logging"])
                self.assertEqual(ini.read_bytes(),b"UserName=Vegeta\r\nOther=unchanged\r\n")
                self.assertEqual(json.loads(settings.read_text())["game_directory"],str(folder))
                self.assertFalse((scripts / "lan_runtime.lua").exists())
                ui.stop_bridge()
                self.assertTrue(ui.runtime.with_suffix(".stop").exists())
            finally:
                root.destroy()

    def test_ini_save_failure_prevents_preflight_and_every_process_start(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            (folder/"SparkingZERO.exe").write_bytes(b"fixture")
            native_fixture(folder)
            settings=folder/"setup.json"
            settings.write_text(json.dumps({"game_directory":str(folder)}))
            ini=folder/"SparkingZERO/Binaries/Win64/steam_emu.ini"
            ini.write_bytes(b"\xff\xfeX")  # Invalid UTF16, must not silently skip.
            root=tk.Tk()
            try:
                ui=setup_launcher.SetupLauncher(root,settings)
                with patch.object(setup_launcher,"probe_native_server") as preflight, \
                     patch.object(setup_launcher.subprocess,"Popen") as process, \
                     patch.object(setup_launcher.messagebox,"showerror") as error:
                    ui.launch()
                error.assert_called_once()
                preflight.assert_not_called()
                process.assert_not_called()
                self.assertEqual(ini.read_bytes(),b"\xff\xfeX")
            finally:
                root.destroy()

    def test_open_preserves_file_and_active_bridge_blocks_launch_save(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            original = b'{"server_host":"old-server","name":"Tester","native_menu":true,"extra":7}'
            (folder / "SparkingZERO.exe").write_bytes(b"fixture")
            native_fixture(folder)
            config = folder / "SzeroLAN.json"
            config.write_bytes(original)
            settings = folder / "setup.json"
            settings.write_text(json.dumps(dict(game_directory=str(folder))))
            root = tk.Tk()
            try:
                ui = setup_launcher.SetupLauncher(root, settings)
                self.assertEqual(config.read_bytes(), original)
                ui.host.set("new-server")
                ui.bridge = MagicMock()
                ui.bridge.poll.return_value = None
                with patch.object(setup_launcher.messagebox, "showinfo") as info:
                    ui.launch()
                self.assertIn("already owns", info.call_args.args[1])
                self.assertEqual(config.read_bytes(), original)
                ui.bridge = None
                # Launch saves before preflight, even when the server is offline.
                with patch.object(setup_launcher, 'probe_native_server', side_effect=ValueError('offline')), patch.object(setup_launcher.messagebox, 'showerror'):
                    ui.launch()
                self.assertEqual(json.loads(config.read_text())["server_host"], "new-server")
                self.assertEqual(json.loads(config.read_text())["extra"], 7)
            finally:
                root.destroy()

    def test_setup_selected_folder_loads_its_config_without_rewriting(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            original = b'{"server_host":"selected-pc","server_port":1234,"name":"Goku"}'
            (folder / "SparkingZERO.exe").write_bytes(b"fixture")
            expected = native_fixture(folder)
            config = folder / "SzeroLAN.json"
            config.write_bytes(original)
            settings = folder / "setup.json"
            root = tk.Tk()
            try:
                ui = setup_launcher.SetupLauncher(root, settings)
                with patch.object(setup_launcher.filedialog, 'askdirectory', return_value=str(folder)), patch.object(setup_launcher, 'install') as install:
                    ui.select_game()
                    install.assert_not_called()
                self.assertEqual(ui.host.get(), "selected-pc")
                self.assertEqual(ui.port.get(), "1234")
                self.assertEqual(ui.name.get(), "Goku")
                self.assertEqual(config.read_bytes(), original)
                self.assertFalse(settings.exists())  # Folder selection also waits for Launch.
            finally:
                root.destroy()

    def test_legacy_native_menu_is_not_started_and_invalid_type_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "SparkingZERO.exe").write_bytes(b"fixture")
            scripts = folder / "scripts"
            scripts.mkdir()
            for name in ("panel.lua", "native_menu.lua", "menu_bridge.dll"):
                (scripts / name).write_bytes(b"fixture")
            expected = native_fixture(folder)
            settings = folder / "setup.json"
            settings.write_text(json.dumps(dict(game_directory=str(folder),
                                                adapter_runtime=str(scripts / "lan_runtime.lua"))))
            root = tk.Tk()
            try:
                ui = setup_launcher.SetupLauncher(root, settings)
                (folder / "SzeroLAN.json").write_text('{"server_host":"localhost","native_menu":true}')
                with patch.object(setup_launcher.subprocess, 'Popen') as popen, patch.object(setup_launcher, 'probe_native_server'):
                    ui.launch()
                self.assertEqual(popen.call_count, 2)
                self.assertEqual(popen.call_args.kwargs["env"]["SZERO_LAN_NATIVE_MENU"], "0")
                ui.bridge = None
                (folder / "SzeroLAN.json").write_text('{"server_host":"localhost","native_menu":"yes"}')
                with patch.object(setup_launcher.subprocess, "Popen") as popen, \
                     patch.object(setup_launcher.messagebox, "showerror") as error:
                    ui.launch()
                popen.assert_not_called()
                self.assertIn("true or false", error.call_args.args[1])
            finally:
                root.destroy()

    def test_bad_destination_does_not_launch_processes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "SparkingZERO.exe").write_bytes(b"fixture")
            native_fixture(folder)
            (folder / "SzeroLAN.json").write_text('{"server_host":"0.0.0.0"}')
            settings = folder / "setup.json"
            settings.write_text(json.dumps(dict(game_directory=str(folder))))
            root = tk.Tk()
            try:
                ui = setup_launcher.SetupLauncher(root, settings)
                with patch.object(setup_launcher.subprocess, "Popen") as popen, \
                     patch.object(setup_launcher.messagebox, "showerror") as error:
                    ui.launch()
                popen.assert_not_called()
                self.assertIn("actual IP", error.call_args.args[1])
            finally:
                root.destroy()

    def test_native_search_preflight_and_explicit_environment_without_panel(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "SparkingZERO.exe").write_bytes(b"fixture")
            (folder / "SzeroLAN.json").write_text(
                '{"server_host":"localhost","native_search":true,"native_menu":true}')
            scripts = folder / "scripts"
            scripts.mkdir()
            shipping = folder / "SparkingZERO/Binaries/Win64/SparkingZERO-Win64-Shipping.exe"
            shipping.parent.mkdir(parents=True)
            shipping.write_bytes(b"owned shipping test fixture")
            settings = folder / "setup.json"
            settings.write_text(json.dumps(dict(game_directory=str(folder),
                                                adapter_runtime=str(scripts / "lan_runtime.lua"))))
            root = tk.Tk()
            try:
                ui = setup_launcher.SetupLauncher(root, settings)
                for missing in ("native_search.lua", "native_search.dll"):
                    with patch.object(setup_launcher.subprocess, "Popen") as popen, \
                         patch.object(setup_launcher.messagebox, "showerror") as error:
                        ui.launch()
                    popen.assert_not_called()
                    self.assertIn("Native search files", error.call_args.args[1])
                    (scripts / missing).write_bytes((setup_launcher.ROOT / "ue4ss/SzeroLAN/scripts" / missing).read_bytes())
                expected = native_fixture(folder)
                # No panel/native-menu files are required: this path uses the original menu.
                with patch.object(setup_launcher.subprocess, 'Popen') as popen, patch.object(setup_launcher, 'probe_native_server'):
                    ui.launch()
                self.assertEqual(popen.call_count, 2)
                self.assertEqual(popen.call_args.kwargs["env"]["SZERO_LAN_NATIVE_SEARCH"], "1")
                self.assertEqual(popen.call_args.kwargs["env"]["SZERO_LAN_NATIVE_MENU"], "0")
                self.assertEqual(popen.call_args.kwargs["env"]["SZERO_LAN_NATIVE_SESSION3"], "1")
                self.assertIn("Battle → Online", ui.status.get())
            finally:
                root.destroy()

    def test_native_mode_migrates_false_flags_and_preflights_every_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "SparkingZERO.exe").write_bytes(b"fixture")
            (folder / "SzeroLAN.json").write_text('{"server_host":"localhost","extra":7,"native_session":false,"native_search":false}')
            scripts = folder / "scripts"
            scripts.mkdir()
            shipping = folder / "SparkingZERO/Binaries/Win64/SparkingZERO-Win64-Shipping.exe"
            shipping.parent.mkdir(parents=True)
            shipping.write_bytes(b"owned shipping test fixture")
            for filename in ("native_search.lua", "native_search.dll", "backend_adapter.dll"):
                (scripts / filename).write_bytes((setup_launcher.ROOT / "ue4ss/SzeroLAN/scripts" / filename).read_bytes())
            settings = folder / "setup.json"
            settings.write_text(json.dumps(dict(game_directory=str(folder),
                                                adapter_runtime=str(scripts / "lan_runtime.lua"))))
            root = tk.Tk()
            try:
                ui = setup_launcher.SetupLauncher(root, settings)
                self.assertFalse(hasattr(ui, "native_session"))
                current = (scripts / "native_search.dll").read_bytes()
                (scripts / "native_search.dll").write_bytes(b"outdated helper fixture")
                with patch.object(setup_launcher.subprocess, "Popen") as popen, \
                     patch.object(setup_launcher.messagebox, "showerror") as error:
                    ui.launch()
                popen.assert_not_called()
                self.assertIn("differs", error.call_args.args[1])
                (scripts / "native_search.dll").write_bytes(current)
                shipping = folder / "SparkingZERO/Binaries/Win64/SparkingZERO-Win64-Shipping.exe"
                shipping.parent.mkdir(parents=True, exist_ok=True)
                shipping.unlink()
                with patch.object(setup_launcher.subprocess, "Popen") as popen, \
                     patch.object(setup_launcher, "probe_native_server") as probe, \
                     patch.object(setup_launcher.messagebox, "showerror") as error:
                    ui.launch()
                popen.assert_not_called()
                probe.assert_not_called()
                self.assertIn("executable is missing", error.call_args.args[1])
                shipping.write_bytes(b"different executable bytes accepted at launch")
                with patch.object(setup_launcher.subprocess, 'Popen') as popen, patch.object(setup_launcher, 'probe_native_server', side_effect=ValueError('server unavailable')), patch.object(setup_launcher.messagebox, 'showerror') as error:
                    ui.launch()
                popen.assert_not_called()
                self.assertIn("server unavailable", error.call_args.args[1])
                with patch.object(setup_launcher.subprocess, 'Popen') as popen, patch.object(setup_launcher, 'probe_native_server') as probe:
                    ui.launch()
                probe.assert_called_once()
                self.assertEqual(popen.call_count, 2)
                environment = popen.call_args.kwargs["env"]
                self.assertEqual(environment["SZERO_LAN_NATIVE_SESSION3"], "1")
                self.assertEqual(environment["SZERO_LAN_NATIVE_SEARCH"], "1")
                config = json.loads((folder / "SzeroLAN.json").read_text())
                self.assertTrue(config["native_session"])
                self.assertTrue(config["native_search"])
                self.assertEqual(config["extra"], 7)
                self.assertIn("Battle → Online", ui.status.get())
            finally:
                root.destroy()
