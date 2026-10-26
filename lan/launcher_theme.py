"""Original vector UI: ki-orange, electric-blue and Dragon Ball-inspired orbs."""
import math
import os
import tkinter as tk
from tkinter import ttk
from pathlib import Path

BG, CARD, INK, MUTED = "#090f1e", "#141f33", "#f3f6ff", "#a6b5cb"
ORANGE, BLUE = "#ff9d24", "#42c9ff"


def build_window(ui):
    root = ui.root
    root.title("SPARKING ZERO | ARENA")
    root.geometry("1080x860" if os.name == "nt" else "1080x930")
    root.minsize(1000, 820 if os.name == "nt" else 900)
    root.configure(bg=BG)
    icon = Path(__file__).resolve().parent / "assets/four-star.png"
    if icon.is_file():
        ui._icon = tk.PhotoImage(file=str(icon))
        root.iconphoto(True, ui._icon)
    font = "Segoe UI" if os.name == "nt" else "DejaVu Sans"
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Arena.TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)
    style.configure("Arena.TLabel", background=BG, foreground=INK, font=(font, 10))
    style.configure("Card.TLabel", background=CARD, foreground=INK, font=(font, 10))
    style.configure("Muted.TLabel", background=CARD, foreground=MUTED, font=(font, 9))
    style.configure("Section.TLabel", background=CARD, foreground=BLUE, font=(font, 11, "bold"))
    style.configure("Arena.TEntry", fieldbackground="#0b1426", foreground=INK,
                    insertcolor=ORANGE, padding=9, borderwidth=0)
    style.configure("Arena.TCombobox", fieldbackground="#0b1426", background="#20314c",
                    foreground=INK, arrowcolor=ORANGE, padding=7)
    style.map("Arena.TCombobox", fieldbackground=[("disabled", "#1c2635"), ("readonly", "#0b1426")],
              foreground=[("disabled", "#687485"), ("readonly", INK)])
    style.configure("Arena.TCheckbutton", background=CARD, foreground=INK,
                    indicatorbackground="#0b1426", indicatorforeground=ORANGE, padding=6)
    style.map("Arena.TCheckbutton", background=[("active", CARD)])
    style.map("Arena.TCheckbutton", foreground=[("disabled", "#687485")])
    style.map("Arena.TEntry", foreground=[("disabled", "#687485")], fieldbackground=[("disabled", "#1c2635")])
    style.configure("Arena.TButton", background="#253752", foreground=INK,
                    font=(font, 10, "bold"), padding=10, borderwidth=0)
    style.map("Arena.TButton", background=[("active", "#344e71")])
    style.configure("Arena.TNotebook", background=CARD, borderwidth=0)
    style.configure("Arena.TNotebook.Tab", background="#253752", foreground=INK,
                    width=14, anchor="center", padding=(18, 10), font=(font, 10, "bold"))
    style.map("Arena.TNotebook.Tab", background=[("selected", "#304761"), ("disabled", "#1c2635")],
              foreground=[("selected", ORANGE), ("disabled", "#687485")],
              padding=[("selected", (18, 10)), ("!selected", (18, 10))])
    style.configure("Launch.TButton", background=ORANGE, foreground="#15101b",
                    font=(font, 15, "bold"), padding=16, borderwidth=0)
    style.map("Launch.TButton", background=[("active", "#ffc366"), ("disabled", "#6e5842")])
    root.option_add("*TCombobox*Listbox.background", "#0b1426")
    root.option_add("*TCombobox*Listbox.foreground", INK)
    chrome = ttk.Frame(root, style="Arena.TFrame", padding=(24, 12))
    chrome.pack(side="bottom", fill="x")
    scroll = tk.Canvas(root, bg=BG, highlightthickness=0)
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=scroll.yview)
    scrollbar.pack(side="right", fill="y")
    scroll.pack(side="left", fill="both", expand=True)
    scroll.configure(yscrollcommand=scrollbar.set)
    panel = ttk.Frame(scroll, style="Arena.TFrame", padding=24)
    window = scroll.create_window(0, 0, window=panel, anchor="nw")
    panel.bind("<Configure>", lambda event: scroll.configure(scrollregion=scroll.bbox("all")))
    scroll.bind("<Configure>", lambda event: scroll.itemconfigure(window, width=event.width))
    root.bind("<MouseWheel>", lambda event: scroll.yview_scroll(-int(event.delta / 120), "units"), add="+")
    scroll.bind("<Button-4>", lambda event: scroll.yview_scroll(-1, "units"))
    scroll.bind("<Button-5>", lambda event: scroll.yview_scroll(1, "units"))
    panel.columnconfigure(0, weight=1)
    panel.columnconfigure(1, weight=1)
    hero = tk.Canvas(panel, height=110, bg=BG, highlightthickness=0)
    hero.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 15))
    def draw(event=None):
        hero.delete("all")
        width = max(hero.winfo_width(), 850)
        hero.create_polygon(width-300, 0, width, 0, width, 130, width-430, 130,
                            fill="#102844", outline="")
        for i in range(5):
            hero.create_line(width-420+i*28, 125, width-240+i*28, 10,
                             fill="#174260", width=2)
        hero.create_text(0, 13, text="SPARKING ZERO", fill=INK, anchor="nw", font=(font, 25, "bold"))
        hero.create_text(1, 52, text="A R E N A", fill=ORANGE, anchor="nw", font=(font, 17, "bold"))
        hero.create_text(2, 94, text="YOUR FIGHTERS. YOUR NETWORK. YOUR TOURNAMENT.",
                         fill=MUTED, anchor="nw", font=(font, 9))
        x, y = width-65, 60
        hero.create_oval(x-46, y-46, x+46, y+46, fill="#5b3515", outline="")
        hero.create_oval(x-38, y-38, x+38, y+38, fill=ORANGE, outline="#ffd07b", width=2)
        for sx, sy in ((-11,-11),(11,-11),(-11,11),(11,11)):
            points=[]
            for n in range(10):
                angle=-math.pi/2+n*math.pi/5
                radius=7 if n%2==0 else 3
                points.extend((x+sx+math.cos(angle)*radius,y+sy+math.sin(angle)*radius))
            hero.create_polygon(points, fill="#be3c1b", outline="")
    hero.bind("<Configure>", draw)

    def card(column, title):
        frame = ttk.Frame(panel, style="Card.TFrame", padding=18)
        frame.grid(row=1, column=column, sticky="nsew", padx=(0, 8) if column==0 else (8, 0))
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text=title, style="Section.TLabel").grid(sticky="w", pady=(0, 12))
        return frame
    left, right = card(0, "01  /  PLAYER & CONNECTION"), card(1, "02  /  GAME PREFERENCES")
    ui.editable = []
    def entry(parent, title, variable):
        ttk.Label(parent, text=title, style="Muted.TLabel").grid(sticky="w", pady=(6, 3))
        widget=ttk.Entry(parent, textvariable=variable, style="Arena.TEntry")
        widget.grid(sticky="ew", pady=(0, 3))
        ui.editable.append(widget)
        return widget
    ttk.Label(left, text="GAME INSTALLATION", style="Muted.TLabel").grid(sticky="w", pady=(4, 4))
    ttk.Label(left, textvariable=ui.game_directory, wraplength=370, style="Card.TLabel").grid(sticky="w", pady=(0, 8))
    ui.select_button=ttk.Button(left, text="SELECT GAME FOLDER", command=ui.select_game, style="Arena.TButton")
    ui.select_button.grid(sticky="ew")
    ui.mod_button=ttk.Button(left, textvariable=ui.mod_action, command=ui.toggle_mod, style="Arena.TButton")
    ui.mod_button.grid(sticky="ew", pady=(8, 0))
    ui.editable.append(ui.mod_button)
    ttk.Label(left, textvariable=ui.mod_status, style="Muted.TLabel", wraplength=410).grid(sticky="w", pady=(5, 8))
    entry(left, "SERVER IP / HOSTNAME", ui.host)
    row = ttk.Frame(left, style="Card.TFrame")
    row.grid(sticky="ew")
    row.columnconfigure(0, weight=1)
    entry(row, "PORT", ui.port)
    ttk.Label(left, text="PLAYER", style="Section.TLabel").grid(sticky="w", pady=(14, 6))
    ui.player_tabs = ttk.Notebook(left, style="Arena.TNotebook")
    ui.player_tabs.grid(sticky="ew")
    quick = ttk.Frame(ui.player_tabs, style="Card.TFrame", padding=10)
    login = ttk.Frame(ui.player_tabs, style="Card.TFrame", padding=10)
    quick.columnconfigure(0, weight=1)
    login.columnconfigure(0, weight=1)
    ui.player_tabs.add(quick, text="Quick play")
    ui.player_tabs.add(login, text="Login")
    ui.player_tabs.bind("<<NotebookTabChanged>>", ui.player_tab_changed)
    ui.name_entry = entry(quick, "PLAYER NAME", ui.name)
    ttk.Label(quick, text="Play casual matches without an account.\nRanked games are unavailable.",
              style="Muted.TLabel", wraplength=375).grid(sticky="w", pady=(8, 4))
    ui.account_inputs = [entry(login, "USERNAME", ui.account_username)]
    password = entry(login, "PASSWORD  ·  EMPTY = REMEMBERED LOGIN", ui.account_password)
    password.configure(show="•")
    ui.account_inputs.append(password)
    ui.login_button = ttk.Button(login, text="LOGIN", command=ui.login_account, style="Arena.TButton")
    ui.login_button.grid(sticky="ew", pady=(8, 0))
    ui.account_inputs.append(ui.login_button)
    ui.editable.append(ui.login_button)
    ttk.Label(login, textvariable=ui.account_status, style="Muted.TLabel", wraplength=375).grid(sticky="w", pady=(8, 4))
    if os.name != "nt":
        entry(right, "WINE EXECUTABLE", ui.wine_binary)
        entry(right, "WINE PREFIX  ·  EMPTY = CURRENT / ~/.wine", ui.wine_prefix)
    ttk.Label(right, textvariable=ui.argument_preview, wraplength=375, style="Muted.TLabel").grid(sticky="w", pady=(10, 0))
    trace=ttk.Checkbutton(right, text="Enable mod logging",
                         variable=ui.mod_logging, style="Arena.TCheckbutton")
    trace.grid(sticky="w", pady=(8, 0))
    ui.logging_checkbox = trace
    ttk.Label(right, text="Off by default · saved when you launch.", style="Muted.TLabel").grid(sticky="w")
    ui.editable.append(trace)
    saves=ttk.Frame(panel, style="Card.TFrame", padding=14)
    saves.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(14, 0))
    saves.columnconfigure(0, weight=1)
    ttk.Label(saves, text="03  /  SAVE UNLOCKS", style="Section.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(saves, textvariable=ui.save_info, wraplength=490, style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(5, 0))
    ui.characters_button=ttk.Button(saves, text="UNLOCK CHARACTERS", command=lambda: ui.unlock_save("characters"), style="Arena.TButton")
    ui.characters_button.grid(row=0, column=1, rowspan=2, padx=(10, 8))
    ui.everything_button=ttk.Button(saves, text="UNLOCK EARNED CONTENT", command=lambda: ui.unlock_save("everything"), style="Arena.TButton")
    ui.everything_button.grid(row=0, column=2, rowspan=2)
    ui.editable.extend((ui.characters_button, ui.everything_button))
    footer=ttk.Frame(chrome, style="Arena.TFrame")
    footer.pack(fill="x")
    footer.columnconfigure(0, weight=1)
    ttk.Label(footer, textvariable=ui.save_status, style="Arena.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(footer, textvariable=ui.status, style="Arena.TLabel", wraplength=610).grid(row=1, column=0, sticky="w", pady=(5, 0))
    ui.launch_button=ttk.Button(footer, text="LAUNCH GAME  →", command=ui.launch, style="Launch.TButton")
    ui.launch_button.grid(row=0, column=1, rowspan=2, sticky="e", padx=(15, 0))
    ttk.Label(panel, text="NATIVE ONLINE MENUS   /   NO CLOUD REQUIRED FOR THE LAN SERVER   /   COMMUNITY LAUNCHER",
              style="Arena.TLabel", font=(font, 8)).grid(row=4, column=0, columnspan=2, sticky="w", pady=(15, 0))
