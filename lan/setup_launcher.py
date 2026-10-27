"""Native LAN launcher with persistent settings and a standalone-friendly UI."""
import json
import ipaddress
import os
from pathlib import Path
import subprocess
import socket
import sys
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import uuid
import tempfile

from account_client import authenticate, _valid_token

from installer import atomic_write, install, uninstall, installed_runtime, digest
from game_process import game_running
from szero_lan import label, load_config
from launcher_support import (bridge_command, find_game_folder,
    game_arguments, game_command, game_environment, launch_options, preferences_path,
    read_preferences, spawn_game)
from launcher_theme import build_window

ROOT = Path(__file__).resolve().parent


def save_private_preferences(path, value):
    """Publish remembered bearer tokens without a world-readable temporary file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write((json.dumps(value, indent=2) + "\n").encode("utf-8"))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def probe_native_server(cfg):
    """Bounded LAN capability check before launching an experimental client."""
    try:
        with socket.create_connection((cfg["server_host"], cfg["server_port"]), timeout=2) as connection:
            connection.settimeout(2)
            greeting = {"op": "hello", "version": 2, "name": "LAN setup check"}
            if cfg.get("account_mode") == "login":
                greeting["account_token"] = cfg.get("account_token", "")
            connection.sendall((json.dumps(greeting) + "\n").encode("utf-8"))
            with connection.makefile("rb") as stream:
                line = stream.readline(8193)
            if not line.endswith(b"\n") or len(line) > 8192:
                raise ValueError("invalid server greeting")
            welcome = json.loads(line)
            if type(welcome) is not dict:
                raise ValueError("invalid server greeting")
            capabilities = welcome.get("capabilities", {})
            versions = capabilities.get("native_session_versions") if type(capabilities) is dict else None
            transactions = capabilities.get("native_session_transactions") if type(capabilities) is dict else None
            lan_identity = capabilities.get("native_lan_identity") if type(capabilities) is dict else None
            if (welcome.get("event") != "welcome" or type(versions) is not list or
                    not any(type(value) is int and value == 2 for value in versions) or
                    type(transactions) is not int or transactions != 1 or
                    type(lan_identity) is not int or lan_identity != 1):
                raise ValueError("server lacks native LAN identity/session support; update the full server tools folder")
            if cfg.get("account_mode") == "login":
                account = welcome.get("account")
                if (type(account) is not dict or account.get("authenticated") is not True or
                        account.get("ranked") is not True):
                    raise ValueError("server did not authenticate this account; update the server or log in again")
    except (OSError, ValueError) as exc:
        raise ValueError("Native LAN server preflight failed: " + str(exc)) from None


def read_editor_config(game_root):
    """Read without rewriting or requiring all editable fields to be valid yet."""
    path = Path(game_root) / "SzeroLAN.json"
    cfg = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(cfg, dict):
        raise ValueError("SzeroLAN.json must be a JSON object")
    return cfg


def config_with_fields(cfg, host, port, name):
    """Validate destination syntax locally; never resolve or connect here."""
    host = host.strip()
    if not 1 <= len(host) <= 253:
        raise ValueError("Enter the server PC's actual IP or hostname")
    try:
        address = ipaddress.IPv4Address(host)
    except ipaddress.AddressValueError:
        # Reject numeric shorthand/invalid IPs rather than treating them as DNS.
        if re.fullmatch(r"[0-9.]+", host):
            raise ValueError("Enter a complete valid IPv4 address, such as 192.168.1.20") from None
        labels = (host[:-1] if host.endswith(".") else host).split(".")
        if any(not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", part)
               for part in labels):
            raise ValueError("Enter a hostname or IPv4 address only, without a URL or port") from None
    else:
        if address.is_unspecified:
            raise ValueError("Enter the server PC's actual IP, not 0.0.0.0 (server bind only)")
        if address.is_multicast or str(address) == "255.255.255.255":
            raise ValueError("Enter the server PC's unicast IPv4 address")
    port_text = str(port).strip()
    if not re.fullmatch(r"[0-9]{1,5}", port_text) or not 1 <= int(port_text) <= 65535:
        raise ValueError("Server port must be an integer in 1..65535")
    result = dict(cfg)
    result.update(server_host=host, server_port=int(port_text), name=label(name, "Player"))
    native_menu = result.get("native_menu", False)
    if type(native_menu) is not bool:
        raise ValueError("native_menu must be true or false in SzeroLAN.json")
    if type(result.get("native_search", False)) is not bool:
        raise ValueError("native_search must be true or false in SzeroLAN.json")
    if type(result.get("native_session", False)) is not bool:
        raise ValueError("native_session must be true or false in SzeroLAN.json")
    if any(key in result for key in ("secret", "slot", "room")):
        raise ValueError("old config: secret, slot and room have been removed")
    # The normal launcher has exactly one supported path: the native Online
    # adapter. Migrate old absent/false flags without disturbing other options.
    result.update(native_session=True, native_search=True)
    return result


def save_editor_config(game_root, host, port, name, options=None, account=None):
    # Re-read on save to preserve fields another tool added since window open.
    cfg = config_with_fields(read_editor_config(game_root), host, port, name)
    if options is not None:
        existing = launch_options(cfg.get("launch_options"))
        existing.update(options)
        cfg["launch_options"] = launch_options(existing)
    if account is not None:
        cfg.update(account)
    # Tokens live in the private launcher preferences, never in game config.
    cfg.pop("account_token", None)
    cfg.pop("account_password", None)
    cfg.pop("account_url", None)
    atomic_write(Path(game_root) / "SzeroLAN.json",
                 (json.dumps(cfg, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return cfg


def sync_player_name(game_root, name):
    """Change only existing, exact UserName= lines; preserve the INI otherwise."""
    name = label(name, "Player")
    path = Path(game_root) / "SparkingZERO/Binaries/Win64/steam_emu.ini"
    if path.is_symlink():
        raise ValueError("steam_emu.ini must not be a symbolic link")
    if not path.exists():
        return False
    with path.open("rb") as stream:
        original = stream.read(1024 * 1024 + 1)
    if len(original) > 1024 * 1024:
        raise ValueError("steam_emu.ini is unexpectedly large; left unchanged")
    bom, payload, encoding = b"", original, "utf-8"
    for marker, codec in ((b"\xff\xfe\x00\x00", None), (b"\x00\x00\xfe\xff", None),
                          (b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be"),
                          (b"\xef\xbb\xbf", "utf-8")):
        if original.startswith(marker):
            if codec is None:
                raise ValueError("Unsupported steam_emu.ini encoding; left unchanged")
            bom, payload, encoding = marker, original[len(marker):], codec
            break
    try:
        text = payload.decode(encoding)
    except UnicodeDecodeError:
        if bom:
            raise ValueError("Invalid steam_emu.ini encoding; left unchanged") from None
        encoding = "cp1252"
        text = payload.decode(encoding)
    if "\x00" in text:
        raise ValueError("Invalid steam_emu.ini text; left unchanged")
    updated = re.sub(r"(?m)^UserName=[^\r\n]*", lambda match: "UserName=" + name, text)
    result = bom + updated.encode(encoding)
    if result == original:
        return False
    # Never overwrite the first recovery copy, including on subsequent launches.
    backup = path.with_name(path.name + ".szero-name.bak")
    try:
        with backup.open("xb") as stream:
            stream.write(original)
    except FileExistsError:
        pass
    if path.is_symlink() or path.read_bytes() != original:
        raise ValueError("steam_emu.ini changed while saving; launch cancelled")
    atomic_write(path, result)
    return True


class SetupLauncher:
    def __init__(self, root, settings_path=None):
        self.root = root
        self.settings_path = Path(settings_path or preferences_path())
        self.settings = read_preferences(self.settings_path)
        if settings_path is None and not self.settings_path.exists() and (ROOT / "setup.json").exists():
            self.settings = read_preferences(ROOT / "setup.json")
        if self.settings.get("game_directory") and not self.settings.get("adapter_runtime"):
            win64=Path(self.settings["game_directory"]) / "SparkingZERO/Binaries/Win64"
            for loader in (win64 / "ue4ss", win64):
                scripts=loader / "Mods/SzeroLAN/scripts"
                if (scripts / "main.lua").is_file():
                    self.settings["adapter_runtime"] = str(scripts / "lan_runtime.lua")
                    break
        self.bridge = None
        self.runtime = None
        self._bridge_timer = None
        self._loading = True
        self.game_directory = tk.StringVar(value=self.settings.get("game_directory", "No game folder selected"))
        self.host = tk.StringVar(value="192.168.1.20")
        self.port = tk.StringVar(value="27150")
        self.name = tk.StringVar(value="Player")
        self.account_mode = tk.StringVar(value="Quick play")
        self.account_username = tk.StringVar(value="")
        self.account_password = tk.StringVar(value="")
        self.account_status = tk.StringVar(value="Quick play · casual matches only")
        self._account_token = ""
        self._login_scope = None
        self._account_profile = None
        self.mod_action = tk.StringVar(value="INSTALL ARENA MOD")
        self.mod_status = tk.StringVar(value="Select a game folder first")
        self.save_info = tk.StringVar(value="Save unlocks require a closed game and a backup")
        self.wine_binary = tk.StringVar(value="wine")
        self.wine_prefix = tk.StringVar(value="")
        self.mod_logging = tk.BooleanVar(value=False)
        self.argument_preview = tk.StringVar(value="Launch arguments: game defaults")
        self.save_status = tk.StringVar(value="Settings restore automatically · saved when you launch")
        self.status = tk.StringVar(value="Select your game, then use Battle → Online in-game.")
        build_window(self)
        if self.settings.get("game_directory"):
            self.load_fields()
        self._loading = False
        for variable in (self.host, self.port, self.name,
                         self.wine_binary, self.wine_prefix, self.mod_logging,
                         self.account_mode, self.account_username,
                         self.account_password):
            variable.trace_add("write", self.settings_changed)
        for variable in (self.host, self.port, self.account_username, self.account_password):
            variable.trace_add("write", self.invalidate_login)
        self.update_preview()
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<Destroy>", self.cancel_timers, add="+")
        root.bind("<FocusIn>", self.refresh_on_focus, add="+")
        self.refresh_installation()

    def cancel_timers(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        self.stop_bridge()
        for attribute in ("_bridge_timer",):
            token=getattr(self, attribute, None)
            if token:
                try:
                    self.root.after_cancel(token)
                except tk.TclError:
                    pass
                setattr(self, attribute, None)

    def current_options(self):
        # Display overrides have been retired from the launcher. Saving on
        # Launch replaces old stored overrides with game defaults before spawn.
        return launch_options(dict(display="Game default", resolution="Game default",
            wine_binary=self.wine_binary.get(), wine_prefix=self.wine_prefix.get(),
            mod_logging=self.mod_logging.get()))

    def update_preview(self):
        try:
            args = game_arguments(self.current_options())
            self.argument_preview.set("Launch arguments: " + (" ".join(args) or "game defaults"))
        except ValueError:
            self.argument_preview.set("Launch arguments: check settings")

    def settings_changed(self, *_):
        if self._loading:
            return
        self.update_preview()
        self.save_status.set("Unsaved changes · click Launch Game to save")
        self.update_account_controls()

    def update_account_controls(self):
        if not hasattr(self, "account_inputs"):
            return
        enabled = (self.selected_game() and not (self.bridge and self.bridge.poll() is None))
        login = self.account_mode.get() == "Account login"
        for widget in self.account_inputs:
            widget.state(["!disabled"] if enabled and login else ["disabled"])
        self.logging_checkbox.state(["!disabled"] if enabled else ["disabled"])
        self.name_entry.state(["!disabled"] if enabled and not login else ["disabled"])
        desired = 1 if login else 0
        for index in range(2):
            self.player_tabs.tab(index, state="normal" if enabled or index == desired else "disabled")
        selected = self.player_tabs.select()
        if not selected or self.player_tabs.index(selected) != desired:
            self.player_tabs.select(desired)
        self.refresh_account_status()

    def player_tab_changed(self, _event=None):
        selected = self.player_tabs.select()
        if selected:
            mode = "Account login" if self.player_tabs.index(selected) else "Quick play"
            if self.account_mode.get() != mode:
                self.account_mode.set(mode)

    def account_scope(self):
        destination = config_with_fields({}, self.host.get(), self.port.get(), "Player")
        return (destination["server_host"].lower(), destination["server_port"],
                self.account_username.get().strip().lower())

    def remembered_account(self):
        stored = self.settings.get("account", {})
        if type(stored) is not dict:
            return ""
        scope = self.account_scope()
        return (stored.get("token", "") if
                (stored.get("host"), stored.get("port"), str(stored.get("username", "")).lower()) == scope and
                _valid_token(stored.get("token")) else "")

    def invalidate_login(self, *_):
        if self._loading:
            return
        self._account_token = ""
        self._login_scope = None
        self._account_profile = None
        self.refresh_account_status()

    def refresh_account_status(self):
        if self._login_scope is not None and self._account_token:
            name = self._account_profile.get("display_name") if self._account_profile else None
            self.account_status.set("Logged in as " + name if name else "Login remembered · verified when launching")
        else:
            try:
                remembered = bool(self.remembered_account())
            except ValueError:
                remembered = False
            self.account_status.set("Login remembered · verified when launching" if remembered else
                                    "Enter credentials · Launch Game checks your login first")

    def login_account(self):
        try:
            if not self.selected_game() or (self.bridge and self.bridge.poll() is None):
                raise ValueError("Select the game folder and disconnect before logging in")
            scope = self.account_scope()
            self.account_status.set("Connecting to game server…")
            self.root.update_idletasks()
            token, profile = authenticate(scope[0], scope[1], self.account_username.get().strip(),
                                          self.account_password.get(), self.remembered_account())
            name = label(profile["display_name"], "Player")
            record = {"host": scope[0], "port": scope[1], "username": scope[2],
                      "token": token, "mode": "login"}
            # Explicit Login saves only the remembered session. UI drafts and
            # game folder selection still wait for Launch Game.
            stored = read_preferences(self.settings_path)
            stored["account"] = record
            save_private_preferences(self.settings_path, stored)
            self.settings["account"] = record
            previous = self._loading
            self._loading = True
            try:
                self.account_password.set("")
                self.name.set(name)
                self.account_mode.set("Account login")
            finally:
                self._loading = previous
            self._account_token, self._login_scope, self._account_profile = token, scope, profile
            self.update_account_controls()
            self.status.set("Login confirmed. Other settings save when you launch.")
        except (OSError, ValueError) as exc:
            self._account_token, self._login_scope, self._account_profile = "", None, None
            self.refresh_account_status()
            messagebox.showerror("Login failed", str(exc))

    def resolve_account(self):
        if self.account_mode.get() == "Quick play":
            return {"account_mode": "quick",
                    "account_username": self.account_username.get().strip()}
        if self.account_mode.get() != "Account login":
            raise ValueError("Choose Quick play or Account login")
        scope = self.account_scope()
        username = self.account_username.get().strip()
        password = self.account_password.get()
        saved = self._account_token if self._login_scope == scope else self.remembered_account()
        try:
            # Supplied credentials always take priority over a remembered
            # session, even when the previous Login button check succeeded.
            token, profile = authenticate(scope[0], scope[1], username, password, saved)
        except (OSError, ValueError) as exc:
            self._account_token, self._login_scope, self._account_profile = "", None, None
            self.account_status.set("Login failed · check username/password and server")
            raise ValueError("Login failed: " + str(exc)) from None
        previous = self._loading
        self._loading = True
        try:
            self.name.set(label(profile["display_name"], "Player"))
            self.account_password.set("")
        finally:
            self._loading = previous
        self._account_token, self._login_scope, self._account_profile = token, scope, profile
        return {"account_mode": "login", "account_username": username}

    def set_active(self, active):
        selected = self.selected_game()
        for widget in self.editable:
            if active or not selected:
                widget.state(["disabled"])
            else:
                widget.state(["!disabled"])
        self.select_button.state(["disabled"] if active else ["!disabled"])
        try:
            installed = bool(selected and installed_runtime(self.settings["game_directory"]))
        except (OSError, ValueError):
            installed = False
        self.launch_button.state(["!disabled"] if active or installed else ["disabled"])
        self.launch_button.configure(text="DISCONNECT LAN" if active else "LAUNCH GAME  →",
                                     command=self.disconnect if active else self.launch)
        self.update_account_controls()

    def disconnect(self):
        if messagebox.askyesno("Disconnect LAN?", "Disconnect this LAN session? The game will stay open. Close it before launching another session."):
            self.stop_bridge()
            self.launch_button.state(["disabled"])
            self.status.set("Disconnecting the background LAN client…")

    def load_fields(self):
        previous = self._loading
        self._loading = True
        try:
            cfg = read_editor_config(self.settings["game_directory"])
            self.host.set(cfg.get("server_host", "192.168.1.20"))
            self.port.set(cfg.get("server_port", 27150))
            self.name.set(cfg.get("name", "Player"))
            self.account_mode.set("Account login" if cfg.get("account_mode") == "login" else "Quick play")
            self.account_username.set(cfg.get("account_username", ""))
            self.account_password.set("")
            self._account_token, self._login_scope, self._account_profile = "", None, None
            stored = self.settings.get("account", {})
            if type(stored) is dict and (stored.get("host"), stored.get("port")) == (
                    self.host.get().strip().lower(), int(self.port.get())):
                self.account_username.set(stored.get("username", ""))
                self.account_mode.set("Account login" if stored.get("mode") == "login" else "Quick play")
                if self.remembered_account():
                    self._account_token = stored["token"]
                    self._login_scope = self.account_scope()
            options=launch_options(cfg.get("launch_options"))
            for variable, key in ((self.wine_binary,"wine_binary"), (self.wine_prefix,"wine_prefix"),
                (self.mod_logging,"mod_logging")):
                variable.set(options[key])
        except (OSError, ValueError) as exc:
            self.status.set(f"Cannot read SzeroLAN.json: {exc}. File left unchanged.")
        finally:
            self._loading = previous
            self.update_preview()

    def save_fields(self):
        if not self.selected_game():
            folder = self.settings.get("game_directory")
            if folder and (Path(folder) / "SparkingZERO.exe").is_file() and not (
                    Path(folder) / "SparkingZERO/Binaries/Win64/SparkingZERO-Win64-Shipping.exe").is_file():
                raise ValueError("Game executable is missing. Game was not launched.")
            raise ValueError("Select a valid game folder first.")
        if not Path(self.settings["game_directory"]).is_dir():
            raise ValueError("The saved game folder is unavailable. Select it again.")
        # Validate the destination before sending any account credentials.
        config_with_fields({}, self.host.get(), self.port.get(), self.name.get())
        account = self.resolve_account()
        cfg=save_editor_config(self.settings["game_directory"], self.host.get(),
                              self.port.get(), self.name.get(), self.current_options(), account)
        sync_player_name(self.settings["game_directory"], cfg["name"])
        stored=read_preferences(self.settings_path)
        stored.update(self.settings)
        record = dict(stored.get("account", {})) if type(stored.get("account")) is dict else {}
        record.pop("url", None)
        record["mode"] = account["account_mode"]
        if account["account_mode"] == "login":
            record.update(host=self._login_scope[0], port=self._login_scope[1],
                          username=self._login_scope[2], token=self._account_token)
        stored["account"] = record
        save_private_preferences(self.settings_path, stored)
        self.settings=stored
        return cfg

    def selected_game(self):
        folder = self.settings.get("game_directory")
        return bool(folder and (Path(folder) / "SparkingZERO.exe").is_file() and
                    (Path(folder) / "SparkingZERO/Binaries/Win64/SparkingZERO-Win64-Shipping.exe").is_file())

    def refresh_on_focus(self, event=None):
        if event is None or event.widget is self.root:
            self.refresh_installation()

    def refresh_installation(self):
        active = bool(self.bridge and self.bridge.poll() is None)
        if self.selected_game():
            folder = self.settings["game_directory"]
            try:
                runtime = installed_runtime(folder)
                if runtime:
                    self.settings["adapter_runtime"] = runtime
                self.mod_action.set("UNINSTALL ARENA MOD" if runtime else "INSTALL ARENA MOD")
                self.mod_status.set("Arena mod installed" if runtime else "Arena mod not installed")
            except (OSError, ValueError, KeyError) as exc:
                self.mod_status.set("Cannot inspect installation: " + str(exc))
        self.set_active(active)

    def require_idle(self):
        if not self.selected_game():
            raise ValueError("Select the game folder first")
        if (self.bridge and self.bridge.poll() is None) or game_running():
            raise ValueError("Close all copies of Sparking ZERO and disconnect before changing game files or saves")

    def select_game(self):
        if self.bridge and self.bridge.poll() is None:
            messagebox.showinfo("Setup", "Close the game and this window before updating.")
            return
        chosen = filedialog.askdirectory(title="Select DRAGON BALL - Sparking! ZERO game root")
        if not chosen:
            return
        try:
            folder = Path(chosen).resolve()
            if not (folder / "SparkingZERO.exe").is_file():
                raise ValueError("Select the game root containing SparkingZERO.exe")
            if not (folder / "SparkingZERO/Binaries/Win64/SparkingZERO-Win64-Shipping.exe").is_file():
                raise ValueError("The selected game is missing its Win64 shipping executable")
            self.settings.pop("adapter_runtime", None)
            self.settings.update(game_directory=str(folder))
            self.game_directory.set(self.settings["game_directory"])
            self.status.set("Game selected. Install the Arena mod, then Launch Game to save settings.")
            self.load_fields()
            self.save_status.set("Game selected · saved settings restored · selection saves on launch")
            self.refresh_installation()
        except (OSError, ValueError) as exc:
            messagebox.showerror("Setup failed", str(exc))

    def toggle_mod(self):
        try:
            self.require_idle()
            folder = self.settings["game_directory"]
            if installed_runtime(folder):
                if not messagebox.askyesno("Uninstall Arena mod?", "Remove our mod from this game? Shared UE4SS loaders, other mods, saved settings and saves are preserved."):
                    return
                uninstall(folder)
                self.status.set("Arena mod removed from this game.")
            else:
                runtime = install(folder)
                self.settings["adapter_runtime"] = runtime
                self.status.set("Arena mod installed. Configure the server and launch when ready.")
        except (OSError, ValueError, KeyError) as exc:
            messagebox.showerror("Arena mod", str(exc))
        finally:
            self.refresh_installation()

    def unlock_save(self, mode):
        try:
            self.require_idle()
            from savegame import plan_unlock, apply_unlock
            folder = Path(self.settings["game_directory"]) / "SaveGame"
            chosen = filedialog.askopenfilename(title="Select this player's MainGameSaveData", initialdir=str(folder),
                                               filetypes=[("Main game save", "MainGameSaveData"), ("All files", "*")])
            if not chosen:
                return
            plan = plan_unlock(Path(chosen), mode=mode)
            # Plan summary comes from parsed eligible rows, never a filename or
            # string search. The module rechecks process state and fingerprint.
            summary = plan.summary
            if not isinstance(summary, str) or len(summary) > 3000:
                raise ValueError("Invalid save plan summary")
            if not messagebox.askyesno("Confirm save unlock", f"Save: {chosen}\n\n{summary}\n\nCreate a verified backup and apply these changes? DLC ownership, story progress, rank and unrelated fields must remain unchanged. Steam Cloud may replace local changes."):
                return
            result = apply_unlock(plan, confirmed=True, game_running=game_running)
            self.save_info.set("Unlock saved · backup: " + str(result.backup_path) if result.changed_rows else
                               "No changes needed · eligible content is already unlocked")
            self.status.set("Save updated. Real-game load validation is still required; keep the backup.")
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            messagebox.showerror("Save unlock", str(exc))

    def launch(self):
        if self.bridge and self.bridge.poll() is None:
            messagebox.showinfo("Launch", "This window already owns a LAN session. Use another window for another instance.")
            return
        try:
            game_root = Path(self.settings["game_directory"])
            self.save_fields()
            cfg = load_config(game_root / "SzeroLAN.json")
            cfg["account_token"] = self._account_token if cfg.get("account_mode") == "login" else ""
            if not cfg.get("server_host") or cfg["server_host"] == "0.0.0.0":
                raise ValueError("Enter the server PC's actual IP or hostname in SzeroLAN.json")
            label(cfg.get("name"), "Player")
            executable = game_root / "SparkingZERO.exe"
            if not executable.is_file():
                raise ValueError("SparkingZERO.exe not found. Run Set up game first.")
            instance = uuid.uuid4().hex
            self.runtime = Path(self.settings["adapter_runtime"]).with_name(f"lan_runtime_{instance}.lua")
            if not all(self.runtime.with_name(name).is_file()
                                         for name in ("native_search.lua", "native_search.dll")):
                raise ValueError("Native search files are missing. Install the Arena mod first.")
            bundled = ROOT / "ue4ss/SzeroLAN/scripts/native_search.dll"
            if (b"native-session-v3-development" not in bundled.read_bytes() or
                    digest(self.runtime.with_name("native_search.dll")) != digest(bundled)):
                raise ValueError("Native adapter differs from this launcher. Uninstall and reinstall the Arena mod with this launcher to update it.")
            for filename in ("native_search.lua", "backend_adapter.dll"):
                installed = self.runtime.with_name(filename)
                bundled = ROOT / "ue4ss/SzeroLAN/scripts" / filename
                if not installed.is_file() or digest(installed) != digest(bundled):
                    raise ValueError("Account/card adapter is missing or outdated. Close the game, then uninstall and reinstall the Arena mod with this launcher.")
            shipping = game_root / "SparkingZERO/Binaries/Win64/SparkingZERO-Win64-Shipping.exe"
            if not shipping.is_file():
                raise ValueError("Game executable is missing. Game was not launched.")
            options=launch_options(cfg.get("launch_options"))
            trace_enabled = options["mod_logging"]
            if trace_enabled:
                for filename in ("native_search.lua", "service_trace.dll"):
                    installed=self.runtime.with_name(filename)
                    bundled=ROOT / "ue4ss/SzeroLAN/scripts" / filename
                    if not installed.is_file() or digest(installed)!=digest(bundled):
                        raise ValueError("Online trace helper is missing/outdated. Close the game, then uninstall and reinstall the Arena mod with this launcher.")
            probe_native_server(cfg)
            environment = dict(os.environ, SZERO_LAN_INSTANCE=instance,
                               SZERO_LAN_ACCOUNT_MODE="1",
                               SZERO_LAN_NATIVE_MENU="0", SZERO_LAN_NATIVE_SEARCH="1",
                               SZERO_LAN_NATIVE_SESSION3="1",
                               SZERO_LAN_MOD_LOGGING="1" if options["mod_logging"] else "0",
                               SZERO_LAN_SERVICE_TRACE="1" if trace_enabled else "0")
            environment.pop("SZERO_ARENA_ACCOUNT_TOKEN", None)
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            bridge_environment=dict(os.environ)
            bridge_environment["SZERO_LAN_MOD_LOGGING"] = environment["SZERO_LAN_MOD_LOGGING"]
            bridge_environment["SZERO_ARENA_ACCOUNT_TOKEN"] = cfg["account_token"]
            if getattr(sys, "frozen", False):
                bridge_environment["PYINSTALLER_RESET_ENVIRONMENT"]="1"
            self.bridge = subprocess.Popen(bridge_command(game_root, self.runtime, watch_parent=True),
                cwd=str(game_root), env=bridge_environment, creationflags=flags, stdin=subprocess.PIPE,
                close_fds=True)
            try:
                spawn_game(subprocess.Popen, game_command(executable, options), cwd=str(game_root),
                           env=game_environment(environment, options),
                           close_fds=True)
            except OSError:
                self.stop_bridge()
                raise
            self.set_active(True)
            self.save_status.set("✓  Settings saved for next run")
            self.status.set("Game launched. Use Battle → Online. Keep this window open for the LAN connection.")
            if trace_enabled:
                self.status.set("Mod logging enabled. Diagnostic files are written beside the mod scripts for this launch.")
            self._bridge_timer=self.root.after(1500, self.check_bridge)
        except (OSError, ValueError, KeyError) as exc:
            messagebox.showerror("Launch failed", str(exc))

    def check_bridge(self):
        if not self.bridge:
            return
        if self.bridge.poll() is not None:
            self.set_active(False)
            self.status.set("Background client stopped. Check the *.client.log beside the mod's main.lua.")
        else:
            self._bridge_timer=self.root.after(1500, self.check_bridge)

    def stop_bridge(self):
        if self.bridge and self.bridge.poll() is None:
            try:
                if self.runtime:
                    atomic_write(self.runtime.with_suffix(".stop"), b"stop\n")
            except OSError:
                pass  # Pipe EOF independently requests the same cleanup.
            finally:
                if self.bridge.stdin:
                    self.bridge.stdin.close()

    def close(self):
        if self.bridge and self.bridge.poll() is None:
            self.stop_bridge()
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        SetupLauncher(root)
    except (OSError, ValueError) as exc:
        messagebox.showerror("Setup settings", str(exc))
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
