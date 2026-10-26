"""Standalone launch argv, frozen dispatch and durable options contracts."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch, MagicMock

import launcher_support as support
import setup_launcher


class LaunchOptionTests(unittest.TestCase):
    def test_native_preferences_migrate_old_wine_z_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"launcher.json"
            path.write_text(json.dumps({"game_directory":"Z:\\games\\Szero", "future":1}))
            value=support.read_preferences(path)
            self.assertEqual(value["game_directory"],"Z:\\games\\Szero" if os.name=="nt" else "/games/Szero")
            self.assertEqual(value["future"],1)
    def test_options_are_strict_and_unknown_fields_survive(self):
        options=support.launch_options({"future": {"keep": 1}})
        self.assertEqual(options["future"], {"keep": 1})
        self.assertEqual(support.game_arguments(options), [])
        for value in ([], {"display": "bad"},
                      {"resolution": "1x99999"}, {"wine_binary": ""}, {"wine_prefix": "x\0"},
                      {"service_trace":1}, {"service_trace":"yes"},
                      {"mod_logging":1}, {"mod_logging":"yes"}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                support.launch_options(value)

    def test_mod_logging_is_an_explicit_single_opt_in(self):
        self.assertFalse(support.launch_options()["mod_logging"])
        self.assertFalse(support.launch_options({"service_trace": True})["service_trace"])
        for enabled in (False, True):
            options = support.launch_options({"mod_logging": enabled})
            self.assertEqual(options["mod_logging"], enabled)
            self.assertEqual(options["service_trace"], enabled)

    def test_argv_has_no_shell_and_retired_renderer_splash_flags_never_return(self):
        options={"dx11": True, "display": "Borderless", "resolution": "1920x1080", "skip_splash": True,
                 "wine_binary": "/some path/wine"}
        exe=Path("Game with spaces/SparkingZERO.exe").resolve()
        args=["-windowed", "-noborder", "-ResX=1920", "-ResY=1080"]
        self.assertEqual(support.game_command(exe, options, "win32"), [str(exe), *args])
        self.assertEqual(support.game_command(exe, options, "linux"), ["/some path/wine", str(exe), *args])
        self.assertNotIn("-dx11", support.game_arguments(dict(options, dx11=False)))
        self.assertNotIn("dx11", support.launch_options(options))
        self.assertNotIn("skip_splash", support.launch_options(options))

    def test_wine_prefix_and_frozen_library_environment_preserve_other_values(self):
        env={"WINEPREFIX": "/existing", "LD_LIBRARY_PATH": "/bundled", "LD_LIBRARY_PATH_ORIG": "/system",
             "WINEDLLOVERRIDES": "dxgi=n;dwmapi,version=b", "SZERO_LAN_INSTANCE": "test"}
        result=support.game_environment(env, {}, "linux")
        self.assertEqual(result["WINEPREFIX"], "/existing")
        self.assertEqual(result["LD_LIBRARY_PATH"], "/system")
        self.assertEqual(result["WINEDLLOVERRIDES"], "dxgi=n;version=b;dwmapi=n,b")
        self.assertEqual(env["LD_LIBRARY_PATH"], "/bundled")
        self.assertEqual(support.game_environment(env, {}, "win32"), env)
        with patch.object(sys, "frozen", True, create=True):
            self.assertNotIn("LD_LIBRARY_PATH", support.game_environment({"LD_LIBRARY_PATH": "/bundled"}, {}, "linux"))

    def test_frozen_child_uses_entry_mode_not_python_script(self):
        with patch.object(sys, "frozen", True, create=True):
            self.assertEqual(support.bridge_command("root", "runtime"),
                             [sys.executable, "--bridge", "--game-root", "root", "--runtime", "runtime"])
        self.assertIn("ingame_client.py", support.bridge_command("root", "runtime")[1])

    def test_options_save_preserves_unknown_config_and_invalid_original(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder) / "SzeroLAN.json"
            path.write_text('{"unknown":123,"launch_options":{"future":7}}')
            saved=setup_launcher.save_editor_config(folder, "localhost", "27150", "Player", {"dx11":True})
            self.assertEqual(saved["launch_options"]["future"], 7)
            self.assertNotIn("dx11", saved["launch_options"])
            self.assertEqual(saved["unknown"], 123)
            broken=b'{"launch_options":{"dx11":"broken"}}'
            path.write_bytes(broken)
            migrated=setup_launcher.save_editor_config(folder, "localhost", "27150", "Player", {"dx11":True})
            self.assertNotIn("dx11", migrated["launch_options"])


@unittest.skipUnless(os.name == "nt" or os.getenv("DISPLAY"), "requires display or Xvfb")
class LaunchSaveTests(unittest.TestCase):
    def game(self, folder):
        (Path(folder)/"SparkingZERO.exe").write_bytes(b"test launcher")
        path=Path(folder)/"SparkingZERO/Binaries/Win64/SparkingZERO-Win64-Shipping.exe"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"test shipping")

    def test_active_session_locks_options_and_has_explicit_disconnect(self):
        with tempfile.TemporaryDirectory() as folder:
            root=tk.Tk()
            try:
                ui=setup_launcher.SetupLauncher(root,Path(folder)/"prefs.json")
                self.assertTrue(all("disabled" in widget.state() for widget in ui.editable))
                self.assertNotIn("disabled",ui.select_button.state())
                self.game(folder)
                ui.settings["game_directory"]=folder
                ui.runtime=Path(folder)/"lan_runtime_test.lua"
                ui.bridge=MagicMock()
                ui.bridge.poll.return_value=None
                ui.set_active(True)
                self.assertIn("DISCONNECT",ui.launch_button.cget("text"))
                self.assertTrue(all("disabled" in widget.state() for widget in ui.editable))
                with patch.object(setup_launcher.messagebox,"askyesno",return_value=True):
                    ui.disconnect()
                self.assertTrue(ui.runtime.with_suffix(".stop").exists())
                ui.bridge.poll.return_value=0
                ui.check_bridge()
                self.assertIn("LAUNCH",ui.launch_button.cget("text"))
                self.assertTrue(all("disabled" not in widget.state() for widget in ui.editable
                                    if widget not in ui.account_inputs))
                self.assertTrue(all("disabled" in widget.state() for widget in ui.account_inputs))
            finally:
                root.destroy()

    def test_edits_and_close_never_save_drafts(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            self.game(folder)
            config=folder / "SzeroLAN.json"
            config.write_text('{"server_host":"old-host","name":"Goku","unknown":7}')
            prefs=folder / "prefs.json"
            prefs.write_text(json.dumps({"game_directory":str(folder), "future":42}))
            root=tk.Tk()
            try:
                ui=setup_launcher.SetupLauncher(root,prefs)
                self.assertEqual(ui.host.get(), "old-host")
                ui.host.set("new-host")
                ui.name.set("Vegeta")
                ui.wine_prefix.set("/tmp/unsaved-prefix")
                ui.mod_logging.set(True)
                original=config.read_bytes()
                original_prefs=prefs.read_bytes()
                # Wait beyond the former debounce interval: no settings writes.
                deadline=time.monotonic()+1.2
                while time.monotonic()<deadline:
                    root.update()
                    time.sleep(.01)
                self.assertEqual(config.read_bytes(),original)
                self.assertEqual(prefs.read_bytes(),original_prefs)
                ui.port.set("invalid")
                self.assertIn("Launch Game",ui.save_status.get())
                ui.close()
                root=None
                self.assertEqual(config.read_bytes(),original)
                self.assertEqual(prefs.read_bytes(),original_prefs)
            finally:
                if root is not None:
                    root.destroy()
            root=tk.Tk()
            try:
                restored=setup_launcher.SetupLauncher(root,prefs)
                self.assertEqual(restored.host.get(),"old-host")
                self.assertEqual(restored.name.get(),"Goku")
                self.assertFalse(hasattr(restored,"dx11"))
                self.assertFalse(hasattr(restored,"display_mode"))
                self.assertFalse(restored.mod_logging.get())
                self.assertEqual(config.read_bytes(),original)
            finally:
                root.destroy()
