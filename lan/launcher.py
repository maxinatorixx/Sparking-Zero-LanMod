"""Small desktop lobby client. Each game instance connects to the same server."""
import json
import os
from pathlib import Path
import queue
import socket
import subprocess
import threading
import uuid
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from szero_lan import LobbyClient, configure_logging, load_config
from installer import install as install_game_files

ROOT = Path(__file__).resolve().parent


def install_adapter(game_root):
    return install_game_files(game_root)


class Launcher:
    def __init__(self, root, config_path):
        self.root, self.config_path = root, Path(config_path)
        cfg = load_config(self.config_path)
        self.cfg = cfg
        self.client = None
        self.pending = queue.Queue()
        self.connecting = False
        self.snapshot = None
        self.instance_id = uuid.uuid4().hex
        configure_logging(ROOT / f"client-{self.instance_id}.log")
        self.launched_game = False
        self.lobby_ids = []
        root.title("Sparking ZERO — LAN Lobbies")
        root.geometry("760x550")
        root.minsize(650, 450)
        panel = ttk.Frame(root, padding=12)
        panel.pack(fill="both", expand=True)
        self.host = tk.StringVar(value=cfg.get("server_host", "192.168.1.20"))
        self.port = tk.StringVar(value=str(cfg["server_port"]))
        self.name = tk.StringVar(value=cfg.get("name", socket.gethostname()))
        top = ttk.Frame(panel)
        top.pack(fill="x")
        for title, value, width in (("Server", self.host, 24), ("Port", self.port, 7), ("Name", self.name, 16)):
            ttk.Label(top, text=title).pack(side="left", padx=(0, 5))
            ttk.Entry(top, textvariable=value, width=width).pack(side="left", padx=(0, 8))
        self.connect_button = ttk.Button(top, text="Connect", command=self.connect)
        self.connect_button.pack(side="left")
        toolbar = ttk.Frame(panel)
        toolbar.pack(fill="x", pady=12)
        for text, callback in (("Quick match", lambda: self.command("queue")),
                               ("Leave / cancel", lambda: self.command("leave")),
                               ("Set up game…", self.install),
                               ("Start game", self.start_game)):
            ttk.Button(toolbar, text=text, command=callback).pack(side="left", padx=(0, 8))
        ttk.Label(panel, text="Lobbies — select one to join").pack(anchor="w")
        self.lobbies = ttk.Treeview(panel, columns=("name", "players", "status"),
                                   show="headings", height=9, selectmode="browse")
        for key, title, width in (("name", "Lobby", 330), ("players", "Players", 80), ("status", "Status", 150)):
            self.lobbies.heading(key, text=title)
            self.lobbies.column(key, width=width)
        self.lobbies.pack(fill="both", expand=True)
        row = ttk.Frame(panel)
        row.pack(fill="x", pady=10)
        self.new_name = tk.StringVar(value="Tournament table")
        ttk.Entry(row, textvariable=self.new_name, width=28).pack(side="left", padx=(0, 6))
        ttk.Button(row, text="Create lobby", command=lambda: self.command("create", name=self.new_name.get())).pack(side="left", padx=(0, 6))
        ttk.Button(row, text="Join selected", command=self.join).pack(side="left", padx=(0, 6))
        self.ready_button = ttk.Button(row, text="Ready", command=self.ready)
        self.ready_button.pack(side="left", padx=(0, 6))
        ttk.Button(row, text="Return to lobby", command=lambda: self.command("finish")).pack(side="left")
        self.members = tk.StringVar(value="Join a lobby or select Quick match.")
        ttk.Label(panel, textvariable=self.members, wraplength=700).pack(anchor="w", pady=6)
        self.status = tk.StringVar(value="Disconnected")
        ttk.Label(panel, textvariable=self.status, wraplength=700).pack(anchor="w")
        self.data_status = tk.StringVar(value="")
        ttk.Label(panel, textvariable=self.data_status, wraplength=700).pack(anchor="w")
        self.adapter_status = tk.StringVar(value="")
        ttk.Label(panel, textvariable=self.adapter_status, wraplength=700).pack(anchor="w")
        ttk.Label(panel, text="Experimental game adapter: battle entry still needs testing.").pack(anchor="w", pady=(10, 0))
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(100, self.poll)

    def save(self):
        number = int(self.port.get())
        if not 1 <= number <= 65535:
            raise ValueError("Port must be in 1..65535")
        if not self.host.get().strip():
            raise ValueError("Enter the server IP or hostname")
        self.cfg.update(server_host=self.host.get().strip(), server_port=number,
                        name=self.name.get().strip() or socket.gethostname())
        self.config_path.write_text(json.dumps(self.cfg, indent=2) + "\n", encoding="utf-8")

    def connect(self):
        if self.connecting:
            return
        if self.client:
            self.client.close()
            self.client = None
            self.snapshot = None
            self.connect_button.config(text="Connect")
            self.status.set("Disconnected")
            self.members.set("Join a lobby or select Quick match.")
            self.lobbies.delete(*self.lobbies.get_children())
            return
        try:
            self.save()
            if not 1 <= self.cfg["server_port"] <= 65535:
                raise ValueError("Port must be in 1..65535")
        except (ValueError, OSError) as exc:
            messagebox.showerror("Connection settings", str(exc))
            return
        cfg = dict(self.cfg)
        if self.launched_game and cfg.get("adapter_runtime"):
            base = Path(cfg["adapter_runtime"])
            cfg["adapter_runtime"] = str(base.with_name(f"lan_runtime_{self.instance_id}.lua"))
        self.connecting = True
        self.status.set("Connecting…")
        def worker():
            try:
                result = LobbyClient(cfg["server_host"], cfg["server_port"], cfg["name"],
                                     cfg.get("adapter_runtime"))
                self.pending.put((result, None))
            except (OSError, ValueError) as exc:
                self.pending.put((None, str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def install(self):
        if self.client or self.connecting:
            messagebox.showinfo("Adapter", "Disconnect before installing the adapter.")
            return
        chosen = filedialog.askdirectory(title="Select DRAGON BALL - Sparking! ZERO game folder")
        if not chosen:
            return
        try:
            self.cfg["adapter_runtime"] = install_adapter(chosen)
            self.cfg["game_directory"] = chosen
            self.save()
            messagebox.showinfo("Game setup complete", "The loader and LAN adapter are ready.\nClick Start game, then Connect.")
        except (OSError, ValueError) as exc:
            messagebox.showerror("Adapter installation", str(exc))

    def start_game(self):
        if self.client or self.connecting:
            messagebox.showinfo("Start game", "Disconnect here before starting another game instance.")
            return
        game_root = self.cfg.get("game_directory")
        if not game_root:
            messagebox.showinfo("Start game", "Select the game folder with Set up game first.")
            return
        executable = Path(game_root) / "SparkingZERO.exe"
        if not executable.is_file():
            messagebox.showerror("Start game", "SparkingZERO.exe was not found in the configured game folder.")
            return
        try:
            environment = dict(os.environ, SZERO_LAN_INSTANCE=self.instance_id)
            subprocess.Popen([str(executable.resolve())], cwd=str(executable.parent), env=environment)
            self.launched_game = True
            self.status.set("Game started. Connect to the lobby server here.")
        except OSError as exc:
            messagebox.showerror("Start game", str(exc))

    def command(self, op, **fields):
        if not self.client or not self.client.connected.is_set():
            self.status.set("Connect to the server first.")
            return
        try:
            self.client.send(op, **fields)
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def join(self):
        selection = self.lobbies.selection()
        if selection:
            self.command("join", lobby_id=selection[0])

    def ready(self):
        if not self.snapshot:
            return
        me = self.snapshot["you"]
        current = next((p for lobby in self.snapshot["lobbies"] for p in lobby["players"]
                        if p["id"] == me), None)
        self.command("ready", value=not (current and current["ready"]))

    def state(self, event):
        self.snapshot = event
        selected = self.lobbies.selection()
        self.lobbies.delete(*self.lobbies.get_children())
        for lobby in event["lobbies"]:
            self.lobbies.insert("", "end", iid=lobby["id"], values=(lobby["name"],
                               len(lobby["players"]), "Fight in progress" if lobby["in_match"] else "Waiting"))
            if selected and selected[0] == lobby["id"]:
                self.lobbies.selection_set(lobby["id"])
        mine = next((l for l in event["lobbies"] if l["id"] == event["lobby"]), None)
        if mine:
            self.members.set(mine["name"] + ": " + ", ".join(p["name"] +
                (" (playing)" if p["playing"] else " (ready)" if p["ready"] else " (waiting)")
                for p in mine["players"]))
            me = next(p for p in mine["players"] if p["id"] == event["you"])
            self.ready_button.config(text="Not ready" if me["ready"] else "Ready")
        else:
            self.members.set("Matchmaking queue" if event["queued"] else "Join a lobby or select Quick match.")
        self.status.set(f"Connected: {event['connected']} players · Queue: {event['queued_count']}" +
                        (" · Your match is assigned" if event["match"] else ""))

    def poll(self):
        try:
            client, error = self.pending.get_nowait()
            self.connecting = False
            self.client = client
            self.connect_button.config(text="Disconnect" if client else "Connect")
            if error:
                self.status.set(error)
        except queue.Empty:
            pass
        if self.client:
            self.data_status.set("Server data connection ready" if self.client.udp_ready.is_set()
                                 else "Waiting for server data connection — check its UDP port")
            report = self.client.adapter_status
            self.adapter_status.set(
                "Game: " + report["stage"] + " — " + report["detail"] if report else
                "Game: waiting for adapter report (check Set up game and restart the game)")
            if self.client.assignment:
                self.data_status.set(self.data_status.get() +
                    f" · Game packets: {self.client.game_packets_sent} sent / {self.client.game_packets_received} received")
            try:
                while True:
                    event = self.client.events.get_nowait()
                    if event["event"] == "state":
                        self.state(event)
                    elif event["event"] == "error":
                        self.status.set(event["message"])
                    elif event["event"] == "match_start":
                        self.status.set("Match assigned: " + event["opponent"])
                    elif event["event"] == "disconnected":
                        self.status.set("Server disconnected — press Connect to reconnect.")
                        self.client.close()
                        self.client = None
                        self.connect_button.config(text="Connect")
                        break
            except queue.Empty:
                pass
        else:
            self.data_status.set("")
            self.adapter_status.set("")
        self.root.after(100, self.poll)

    def close(self):
        if self.client:
            self.client.close()
        # A connect attempt may still be pending; process exits after its daemon thread.
        self.root.destroy()


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(ROOT / "client.example.json"))
    args = parser.parse_args()
    root = tk.Tk()
    try:
        Launcher(root, args.config)
    except (ValueError, KeyError, OSError) as exc:
        root.withdraw()
        messagebox.showerror("Client configuration", str(exc))
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
