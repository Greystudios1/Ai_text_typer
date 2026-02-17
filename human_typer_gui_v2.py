import json
import random
import subprocess
import sys
import threading
import time
import tkinter as tk
from dataclasses import asdict, dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pyautogui

try:
    from pynput import keyboard as pynput_keyboard
except Exception:
    pynput_keyboard = None


pyautogui.FAILSAFE = True

COMMON_DIGRAPHS = {
    "th": 0.75,
    "he": 0.75,
    "in": 0.82,
    "er": 0.85,
    "an": 0.88,
    "re": 0.9,
    "on": 0.92,
    "at": 0.93,
    "nd": 0.93,
    "st": 0.95,
}

NEIGHBOR_KEYS = {
    "q": "wa", "w": "qase", "e": "wsdr", "r": "edft", "t": "rfgy", "y": "tghu",
    "u": "yhji", "i": "ujko", "o": "iklp", "p": "ol",
    "a": "qwsz", "s": "awedxz", "d": "serfcx", "f": "drtgvc", "g": "ftyhbv",
    "h": "gyujnb", "j": "huikmn", "k": "jiolm", "l": "kop",
    "z": "asx", "x": "zsdc", "c": "xdfv", "v": "cfgb", "b": "vghn",
    "n": "bhjm", "m": "njk",
}

SHIFT_CHAR_MAP = {
    "~": "`", "!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6", "&": "7", "*": "8", "(": "9", ")": "0",
    "_": "-", "+": "=", "{": "[", "}": "]", "|": "\\", ":": ";", '"': "'", "<": ",", ">": ".", "?": "/",
}


@dataclass
class TyperConfig:
    base_wpm: float
    variation_pct: float
    burst_min: int
    burst_max: int
    micro_pause_chance: float
    think_pause_chance: float
    typo_chance: float
    correction_chance: float
    warmup_chars: int
    fatigue_per_100_chars: float


PRESETS = {
    "Careful": TyperConfig(45, 20, 4, 12, 0.35, 0.2, 0.3, 0.95, 60, 6),
    "Fast": TyperConfig(110, 20, 8, 28, 0.12, 0.08, 1.5, 0.75, 20, 2),
    "Fatigued": TyperConfig(55, 30, 3, 14, 0.45, 0.3, 1.8, 0.85, 30, 12),
    "No typos": TyperConfig(80, 18, 6, 20, 0.22, 0.12, 0, 1.0, 30, 3),
}


class EventLogger:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.events = []

    def log(self, kind: str, detail: str = ""):
        ts = time.time()
        if self.enabled:
            self.events.append((ts, kind, detail))


@dataclass
class RunStats:
    start_ts: float
    end_ts: float = 0.0
    chars_typed: int = 0
    typo_count: int = 0
    correction_count: int = 0
    micro_pause_total: float = 0.0
    think_pause_total: float = 0.0

    def effective_wpm(self) -> float:
        dur = max(0.001, self.end_ts - self.start_ts)
        return (self.chars_typed / 5.0) / (dur / 60.0)


class HumanTyper:
    def __init__(
        self,
        config: TyperConfig,
        stop_event: threading.Event,
        pause_event: threading.Event,
        logger: EventLogger,
        stats: RunStats,
        progress_cb,
        dry_run: bool,
    ):
        self.config = config
        self.stop_event = stop_event
        self.pause_event = pause_event
        self.logger = logger
        self.stats = stats
        self.progress_cb = progress_cb
        self.dry_run = dry_run
        self.typed_chars = 0
        self.recent_error = False
        self.state = "flow"

    def run_formatted(self, text: str, rich_shortcuts: bool = True):
        lines = text.splitlines()
        for line_idx, line in enumerate(lines):
            if self.stop_event.is_set():
                return
            self._wait_if_paused()
            stripped = line.lstrip()
            if stripped.startswith("- ") or stripped.startswith("* "):
                self._type_bullet(rich_shortcuts)
                content = stripped[2:]
            else:
                content = line

            self._type_inline_markdown(content, rich_shortcuts)
            if line_idx < len(lines) - 1:
                self._type_char("\n")

    def _type_inline_markdown(self, text: str, rich_shortcuts: bool):
        i = 0
        while i < len(text) and not self.stop_event.is_set():
            self._wait_if_paused()
            if text.startswith("**", i):
                end = text.find("**", i + 2)
                if end != -1 and end > i + 2:
                    self._toggle_bold(rich_shortcuts)
                    self._run_text(text[i + 2:end])
                    self._toggle_bold(rich_shortcuts)
                    i = end + 2
                    continue
            if text[i] in "*_":
                marker = text[i]
                end = text.find(marker, i + 1)
                if end != -1 and end > i + 1:
                    self._toggle_italic(rich_shortcuts)
                    self._run_text(text[i + 1:end])
                    self._toggle_italic(rich_shortcuts)
                    i = end + 1
                    continue

            self._type_char(text[i])
            prev = text[i - 1] if i > 0 else ""
            self._flight_delay(prev, text[i])
            self._boundary_pause(text[i])
            i += 1

    def _run_text(self, text: str):
        idx = 0
        while idx < len(text) and not self.stop_event.is_set():
            self._wait_if_paused()
            burst_len = random.randint(self.config.burst_min, self.config.burst_max)
            burst_end = min(idx + burst_len, len(text))
            while idx < burst_end and not self.stop_event.is_set():
                self._wait_if_paused()
                char = text[idx]
                prev = text[idx - 1] if idx > 0 else ""

                if self._should_enter_hesitation(char):
                    self.state = "hesitation"
                    pause = random.uniform(0.25, 1.2)
                    self.stats.think_pause_total += pause
                    self.logger.log("hesitation", f"{pause:.3f}s")
                    time.sleep(pause)
                else:
                    self.state = "flow"

                if self._should_make_typo(char):
                    wrong_char = self._make_adjacent_typo(char)
                    if wrong_char:
                        self.stats.typo_count += 1
                        self._type_char(wrong_char)
                        self.recent_error = True
                        self.logger.log("typo", f"{wrong_char}->{char}")
                        if random.random() < self.config.correction_chance:
                            self.stats.correction_count += 1
                            self._pause_after_error()
                            self._press("backspace")
                            self._short_delay()
                            self._type_char(char)
                            self.recent_error = False
                        else:
                            idx += 1
                            continue

                self._type_char(char)
                self._flight_delay(prev, char)
                self._boundary_pause(char)
                if char == " " and random.random() < 0.03:
                    self._chunk_retype()
                idx += 1

            if idx < len(text) and random.random() < self.config.think_pause_chance:
                pause = random.uniform(0.6, 2.8)
                self.stats.think_pause_total += pause
                self.logger.log("think_pause", f"{pause:.3f}s")
                time.sleep(pause)

    def _wait_if_paused(self):
        while self.pause_event.is_set() and not self.stop_event.is_set():
            time.sleep(0.05)

    def _toggle_bold(self, rich_shortcuts: bool):
        if rich_shortcuts:
            self._hotkey("ctrl", "b")
            self._short_delay()

    def _toggle_italic(self, rich_shortcuts: bool):
        if rich_shortcuts:
            self._hotkey("ctrl", "i")
            self._short_delay()

    def _type_bullet(self, rich_shortcuts: bool):
        if rich_shortcuts:
            self._hotkey("ctrl", "shift", "8")
            self._short_delay()
            return
        self._run_text("- ")

    def _chunk_retype(self):
        n = random.randint(2, 6)
        for _ in range(n):
            self._press("backspace")
            self._short_delay()
            self.logger.log("edit_backspace", "chunk")

    def _type_char(self, char: str):
        if self.stop_event.is_set():
            return
        self._wait_if_paused()

        hold = random.uniform(0.03, 0.11)
        if char == "\n":
            self._press("enter")
        elif char == "\t":
            self._press("tab")
        elif char.isupper():
            self._key_with_modifiers(char.lower(), ["shift"])
        elif char in SHIFT_CHAR_MAP:
            self._key_with_modifiers(SHIFT_CHAR_MAP[char], ["shift"])
        else:
            self._write_key(char)

        time.sleep(hold)
        self.typed_chars += 1
        self.stats.chars_typed += 1
        self.logger.log("char", repr(char))
        self.progress_cb(self.stats.chars_typed)

    def _write_key(self, key: str):
        if not self.dry_run:
            pyautogui.press(key)

    def _press(self, key: str):
        if not self.dry_run:
            pyautogui.press(key)

    def _hotkey(self, *keys: str):
        self.logger.log("hotkey", "+".join(keys))
        if not self.dry_run:
            pyautogui.hotkey(*keys)

    def _key_with_modifiers(self, key: str, modifiers):
        self.logger.log("keymod", f"{'+'.join(modifiers)}+{key}")
        if self.dry_run:
            return
        for m in modifiers:
            pyautogui.keyDown(m)
        pyautogui.press(key)
        for m in reversed(modifiers):
            pyautogui.keyUp(m)

    def _flight_delay(self, prev_char: str, current_char: str):
        cps = (self.config.base_wpm * 5.0) / 60.0
        baseline = 1.0 / max(cps, 0.1)
        if self.typed_chars < self.config.warmup_chars:
            baseline *= 1.25 - 0.35 * (self.typed_chars / max(1, self.config.warmup_chars))
        fatigue_factor = 1.0 + (self.config.fatigue_per_100_chars / 100.0) * (self.typed_chars / 100.0)
        baseline *= fatigue_factor
        baseline *= COMMON_DIGRAPHS.get((prev_char + current_char).lower(), 1.0)
        if current_char.isdigit() or current_char in ",.;:!?()[]{}":
            baseline *= random.uniform(1.2, 1.8)
        jitter = random.uniform(-(self.config.variation_pct / 100.0), self.config.variation_pct / 100.0)
        delay = max(0.01, baseline * (1.0 + jitter))
        self.logger.log("flight", f"{delay:.3f}s")
        time.sleep(delay)

    def _boundary_pause(self, char: str):
        if char in " ,;" and random.random() < self.config.micro_pause_chance:
            pause = random.uniform(0.08, 0.35)
            self.stats.micro_pause_total += pause
            self.logger.log("micro_pause", f"{pause:.3f}s")
            time.sleep(pause)
        if char in ".!?":
            pause = random.uniform(0.25, 1.0)
            self.stats.think_pause_total += pause
            self.logger.log("boundary_pause", f"{pause:.3f}s")
            time.sleep(pause)

    def _short_delay(self):
        time.sleep(random.uniform(0.03, 0.12))

    def _pause_after_error(self):
        time.sleep(random.uniform(0.18, 0.7))

    def _should_enter_hesitation(self, char: str) -> bool:
        return (self.recent_error and random.random() < 0.35) or (char in ".,;:!?" and random.random() < 0.25)

    def _should_make_typo(self, char: str) -> bool:
        if not char.isalpha():
            return False
        chance = self.config.typo_chance / 100.0
        if self.state == "flow":
            chance *= 1.15
        return random.random() < chance

    def _make_adjacent_typo(self, char: str):
        neighbors = NEIGHBOR_KEYS.get(char.lower(), "")
        if not neighbors:
            return None
        out = random.choice(neighbors)
        return out.upper() if char.isupper() else out


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Human-ish Typer v2 (Formatted Text)")
        self.root.geometry("1040x760")

        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.worker = None
        self.global_hotkey_listener = None
        self.total_chars = 0
        self.current_theme = "dark"

        self._build_ui()
        self._apply_theme("dark")
        self._bind_hotkeys()
        self._setup_global_emergency_hotkey()

    def _ui(self, fn):
        self.root.after(0, fn)

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Formatted text (supports **bold**, *italic*, bullets '- ') ").grid(row=0, column=0, sticky="w")
        self.text_input = tk.Text(frm, height=10, wrap="word")
        self.text_input.grid(row=1, column=0, columnspan=5, sticky="nsew", pady=(4, 8))
        self.text_input.bind("<KeyRelease>", lambda _e: self._refresh_text_stats())

        self.armed_var = tk.StringVar(value="DISARMED")
        ttk.Label(frm, textvariable=self.armed_var, foreground="red", font=("Segoe UI", 12, "bold")).grid(row=2, column=0, sticky="w")

        self.rich_shortcuts_var = tk.BooleanVar(value=True)
        self.dry_run_var = tk.BooleanVar(value=False)
        self.log_events_var = tk.BooleanVar(value=True)
        self.guard_window_var = tk.BooleanVar(value=True)
        self.dark_mode_var = tk.BooleanVar(value=True)
        self.power_user_var = tk.BooleanVar(value=False)

        ttk.Checkbutton(frm, text="Use rich-text shortcuts", variable=self.rich_shortcuts_var).grid(row=2, column=1, sticky="w")
        ttk.Checkbutton(frm, text="Dry run (simulate only)", variable=self.dry_run_var).grid(row=2, column=2, sticky="w")
        ttk.Checkbutton(frm, text="Enable event log", variable=self.log_events_var).grid(row=2, column=3, sticky="w")
        ttk.Checkbutton(frm, text="Guard active window title", variable=self.guard_window_var).grid(row=2, column=4, sticky="w")
        ttk.Checkbutton(frm, text="Dark mode", variable=self.dark_mode_var, command=self.toggle_dark_mode).grid(row=3, column=1, sticky="w")
        ttk.Checkbutton(frm, text="Power user mode", variable=self.power_user_var, command=self.toggle_power_user_mode).grid(row=3, column=2, sticky="w")

        self.active_window_var = tk.StringVar(value="Active window: (unknown)")
        ttk.Label(frm, textvariable=self.active_window_var).grid(row=3, column=0, columnspan=1, sticky="w")

        controls = [
            ("Base WPM", 10, 160, 70), ("Variation %", 0, 80, 25), ("Burst min chars", 1, 30, 6),
            ("Burst max chars", 2, 80, 18), ("Micro pause chance %", 0, 100, 30),
            ("Think pause chance %", 0, 100, 14), ("Typo chance %", 0, 20, 1),
            ("Correction chance %", 0, 100, 85), ("Warmup chars", 0, 300, 40), ("Fatigue % / 100 chars", 0, 30, 4),
        ]

        self.scale_vars = {}
        for i, (label, mn, mx, dv) in enumerate(controls):
            r = 4 + i
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w")
            var = tk.DoubleVar(value=dv)
            ttk.Scale(frm, from_=mn, to=mx, variable=var, style="Themed.Horizontal.TScale").grid(row=r, column=1, columnspan=2, sticky="ew", padx=(8, 8))
            ttk.Label(frm, textvariable=var, width=8).grid(row=r, column=3, sticky="e")
            self.scale_vars[label] = var

        seed_frame = ttk.Frame(frm)
        seed_frame.grid(row=14, column=0, columnspan=5, sticky="ew", pady=(10, 0))
        self.use_seed_var = tk.BooleanVar(value=True)
        self.seed_var = tk.StringVar(value="12345")
        self.preset_var = tk.StringVar(value="Careful")
        ttk.Checkbutton(seed_frame, text="Use seed", variable=self.use_seed_var, command=self._on_use_seed_toggle).pack(side="left")
        ttk.Label(seed_frame, text="Random seed").pack(side="left", padx=(8, 0))
        self.seed_entry = ttk.Entry(seed_frame, width=12, textvariable=self.seed_var)
        self.seed_entry.pack(side="left", padx=(6, 8))
        ttk.Button(seed_frame, text="Randomize seed", command=self.randomize_seed).pack(side="left")
        ttk.Label(seed_frame, text="Preset").pack(side="left", padx=(14, 4))
        self.preset_combo = ttk.Combobox(seed_frame, values=list(PRESETS.keys()), textvariable=self.preset_var, width=12, state="readonly")
        self.preset_combo.pack(side="left")
        ttk.Button(seed_frame, text="Apply preset", command=self.apply_preset).pack(side="left", padx=(6, 0))
        ttk.Button(seed_frame, text="Save profile", command=self.save_profile).pack(side="left", padx=(12, 0))
        ttk.Button(seed_frame, text="Load profile", command=self.load_profile).pack(side="left", padx=(6, 0))

        run_frame = ttk.Frame(frm)
        run_frame.grid(row=15, column=0, columnspan=5, sticky="ew", pady=(8, 0))
        self.countdown_var = tk.IntVar(value=4)
        ttk.Label(run_frame, text="Start delay (seconds)").pack(side="left")
        self.countdown_spin = ttk.Spinbox(run_frame, from_=0, to=20, textvariable=self.countdown_var, width=6)
        self.countdown_spin.pack(side="left", padx=(6, 12))
        self.start_btn = ttk.Button(run_frame, text="Start (F8)", command=self.start)
        self.start_btn.pack(side="left")
        self.pause_btn = ttk.Button(run_frame, text="Pause (F9)", command=self.pause_resume, state="disabled")
        self.pause_btn.pack(side="left", padx=6)
        self.stop_btn = ttk.Button(run_frame, text="Stop (F10)", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left")
        ttk.Button(run_frame, text="Update from Git", command=self.update_from_git).pack(side="left", padx=(12, 0))

        self.status = tk.StringVar(value="Ready")
        self.progress_var = tk.StringVar(value="Typed 0 / 0 chars")
        self.preview_var = tk.StringVar(value="Estimated WPM range: 56-84 | Expected typos per 1k chars: 10")
        self.input_stats_var = tk.StringVar(value="Input: 0 chars | 0 words | 0 lines")
        self.summary_var = tk.StringVar(value="Run summary: n/a")

        ttk.Label(frm, textvariable=self.status).grid(row=16, column=0, columnspan=5, sticky="w", pady=(8, 0))
        ttk.Label(frm, textvariable=self.progress_var).grid(row=17, column=0, columnspan=5, sticky="w")
        ttk.Label(frm, textvariable=self.preview_var).grid(row=18, column=0, columnspan=5, sticky="w")
        ttk.Label(frm, textvariable=self.input_stats_var).grid(row=19, column=0, columnspan=5, sticky="w")
        ttk.Label(frm, textvariable=self.summary_var).grid(row=20, column=0, columnspan=5, sticky="w")

        self.log_box = tk.Text(frm, height=9, wrap="none")
        self.log_box.grid(row=21, column=0, columnspan=5, sticky="nsew", pady=(8, 0))

        self.debug_var = tk.StringVar(value="Debug: disabled")
        self.debug_label = ttk.Label(frm, textvariable=self.debug_var)
        self.debug_label.grid(row=22, column=0, columnspan=5, sticky="w", pady=(6, 0))
        self.toggle_power_user_mode()

        frm.columnconfigure(2, weight=1)
        frm.rowconfigure(1, weight=1)
        frm.rowconfigure(21, weight=1)

        self._refresh_text_stats()
        self._refresh_preview()
        self._on_use_seed_toggle()
        self._poll_active_window_title()

    def _bind_hotkeys(self):
        self.root.bind("<F8>", lambda _e: self.start())
        self.root.bind("<F9>", lambda _e: self.pause_resume())
        self.root.bind("<F10>", lambda _e: self.stop())

    def _apply_theme(self, mode: str):
        style = ttk.Style(self.root)
        if "clam" in style.theme_names() and style.theme_use() != "clam":
            style.theme_use("clam")

        if mode == "dark":
            bg = "#1e1e1e"
            fg = "#f2f2f2"
            panel = "#2a2a2a"
            entry_bg = "#151515"
            entry_fg = "#ffffff"
            border = "#3a3a3a"
            button_bg = "#343434"
            button_active_bg = "#3f3f3f"
            button_disabled_bg = "#2b2b2b"
            disabled_fg = "#cfcfcf"
            disabled_btn_fg = "#9a9a9a"
        else:
            bg = "#f2f2f2"
            fg = "#111111"
            panel = "#ffffff"
            entry_bg = "#ffffff"
            entry_fg = "#111111"
            border = "#bcbcbc"
            button_bg = "#ffffff"
            button_active_bg = "#f4f4f4"
            button_disabled_bg = "#ececec"
            disabled_fg = "#666666"
            disabled_btn_fg = "#7a7a7a"

        self.root.configure(bg=bg)
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TCheckbutton", background=bg, foreground=fg)

        style.configure(
            "TButton",
            background=button_bg,
            foreground=fg,
            bordercolor=border,
            darkcolor=button_bg,
            lightcolor=button_bg,
            relief="flat",
            borderwidth=1,
            focusthickness=1,
            focuscolor=border,
            padding=(8, 4),
        )

        style.configure(
            "Readable.TEntry",
            fieldbackground=entry_bg,
            foreground=entry_fg,
            bordercolor=border,
            insertcolor=entry_fg,
        )
        style.map(
            "Readable.TEntry",
            foreground=[("disabled", disabled_fg), ("!disabled", entry_fg)],
            fieldbackground=[("disabled", panel), ("!disabled", entry_bg)],
        )

        style.configure(
            "Readable.TCombobox",
            fieldbackground=entry_bg,
            foreground=entry_fg,
            background=panel,
            bordercolor=border,
            arrowcolor=entry_fg,
        )
        style.map(
            "Readable.TCombobox",
            fieldbackground=[("readonly", entry_bg), ("disabled", panel), ("!readonly", entry_bg)],
            foreground=[("readonly", entry_fg), ("disabled", disabled_fg), ("!disabled", entry_fg)],
            selectforeground=[("readonly", entry_fg)],
            arrowcolor=[("disabled", disabled_fg), ("!disabled", entry_fg)],
        )

        style.configure(
            "Readable.TSpinbox",
            fieldbackground=entry_bg,
            foreground=entry_fg,
            background=panel,
            bordercolor=border,
            arrowcolor=entry_fg,
        )
        style.map(
            "Readable.TSpinbox",
            foreground=[("disabled", disabled_fg), ("!disabled", entry_fg)],
            fieldbackground=[("disabled", panel), ("!disabled", entry_bg)],
            arrowcolor=[("disabled", disabled_fg), ("!disabled", entry_fg)],
        )

        scale_trough = "#2f2f2f" if mode == "dark" else "#d9d9d9"
        style.configure("Themed.Horizontal.TScale", background=bg, troughcolor=scale_trough)
        style.map("Themed.Horizontal.TScale", background=[("active", bg)])

        style.map(
            "TButton",
            background=[("active", button_active_bg), ("disabled", button_disabled_bg), ("!disabled", button_bg)],
            foreground=[("disabled", disabled_btn_fg), ("!disabled", fg)],
            bordercolor=[("disabled", border), ("!disabled", border)],
        )

        self.seed_entry.configure(style="Readable.TEntry")
        self.preset_combo.configure(style="Readable.TCombobox")
        self.countdown_spin.configure(style="Readable.TSpinbox")

        for widget in (self.text_input, self.log_box):
            widget.configure(
                bg=entry_bg,
                fg=entry_fg,
                insertbackground=entry_fg,
                selectbackground="#3b82f6" if mode == "dark" else "#9ec5fe",
                selectforeground="#ffffff" if mode == "dark" else "#111111",
            )

        self.current_theme = mode

    def toggle_dark_mode(self):
        self._apply_theme("dark" if self.dark_mode_var.get() else "light")
        self.status.set(f"Theme set to {self.current_theme}")

    def toggle_power_user_mode(self):
        enabled = self.power_user_var.get()
        if enabled:
            self.log_box.grid()
            self.debug_label.grid()
            self.debug_var.set("Debug: power user mode enabled")
        else:
            self.log_box.grid_remove()
            self.debug_label.grid_remove()
            self.debug_var.set("Debug: disabled")

    def _setup_global_emergency_hotkey(self):
        if pynput_keyboard is None:
            self.status.set("Ready (global Ctrl+Alt+Esc unavailable: pynput not installed)")
            return

        def for_canonical(f):
            return lambda k: f(self.global_hotkey_listener.canonical(k))

        hotkey = pynput_keyboard.HotKey(
            pynput_keyboard.HotKey.parse("<ctrl>+<alt>+<esc>"),
            lambda: self._ui(self.emergency_stop),
        )
        self.global_hotkey_listener = pynput_keyboard.Listener(
            on_press=for_canonical(hotkey.press),
            on_release=for_canonical(hotkey.release),
        )
        self.global_hotkey_listener.daemon = True
        self.global_hotkey_listener.start()

    def _poll_active_window_title(self):
        try:
            win = pyautogui.getActiveWindow()
            title = win.title if win else "(none)"
        except Exception:
            title = "(unavailable)"
        self.active_window_var.set(f"Active window: {title}")
        self.root.after(700, self._poll_active_window_title)

    def _refresh_text_stats(self):
        text = self.text_input.get("1.0", "end-1c")
        chars = len(text)
        words = len([w for w in text.split() if w])
        lines = max(1, text.count("\n") + 1) if text else 0
        self.input_stats_var.set(f"Input: {chars} chars | {words} words | {lines} lines")
        if chars and (sum(c in "{}[]|\\" for c in text) > chars * 0.08):
            self.status.set("Warning: text contains many symbols; verify target app supports them.")
        self._refresh_preview()
        self._refresh_debug_panel()

    def _refresh_preview(self):
        wpm = self.scale_vars["Base WPM"].get()
        var = self.scale_vars["Variation %"].get()
        typo = self.scale_vars["Typo chance %"].get()
        low = max(1, int(wpm * (1 - var / 100)))
        high = int(wpm * (1 + var / 100))
        self.preview_var.set(f"Estimated WPM range: {low}-{high} | Expected typos per 1k chars: {int(typo*10)}")

    def _refresh_debug_panel(self):
        if not self.power_user_var.get():
            return
        self.debug_var.set(
            f"Debug: theme={self.current_theme} | use_seed={self.use_seed_var.get()} | seed={self.seed_var.get() or '(auto)'} | dry_run={self.dry_run_var.get()} | event_log={self.log_events_var.get()} | guard_window={self.guard_window_var.get()}"
        )

    def _on_use_seed_toggle(self):
        if self.use_seed_var.get():
            if not self.seed_var.get().strip():
                self.seed_var.set("12345")
            self.seed_entry.config(state="normal")
        else:
            self.seed_entry.config(state="disabled")
        self._refresh_debug_panel()

    def _config_from_ui(self) -> TyperConfig:
        return TyperConfig(
            base_wpm=self.scale_vars["Base WPM"].get(),
            variation_pct=self.scale_vars["Variation %"].get(),
            burst_min=int(self.scale_vars["Burst min chars"].get()),
            burst_max=int(self.scale_vars["Burst max chars"].get()),
            micro_pause_chance=self.scale_vars["Micro pause chance %"].get() / 100.0,
            think_pause_chance=self.scale_vars["Think pause chance %"].get() / 100.0,
            typo_chance=self.scale_vars["Typo chance %"].get(),
            correction_chance=self.scale_vars["Correction chance %"].get() / 100.0,
            warmup_chars=int(self.scale_vars["Warmup chars"].get()),
            fatigue_per_100_chars=self.scale_vars["Fatigue % / 100 chars"].get(),
        )

    def randomize_seed(self):
        self.seed_var.set(str(random.randint(1, 2_000_000_000)))
        self.use_seed_var.set(True)
        self.seed_entry.config(state="normal")
        self._refresh_debug_panel()

    def apply_preset(self):
        cfg = PRESETS[self.preset_var.get()]
        mapping = {
            "Base WPM": cfg.base_wpm,
            "Variation %": cfg.variation_pct,
            "Burst min chars": cfg.burst_min,
            "Burst max chars": cfg.burst_max,
            "Micro pause chance %": cfg.micro_pause_chance * 100,
            "Think pause chance %": cfg.think_pause_chance * 100,
            "Typo chance %": cfg.typo_chance,
            "Correction chance %": cfg.correction_chance * 100,
            "Warmup chars": cfg.warmup_chars,
            "Fatigue % / 100 chars": cfg.fatigue_per_100_chars,
        }
        for k, v in mapping.items():
            self.scale_vars[k].set(v)
        self._refresh_preview()

    def save_profile(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        data = {
            "typer_config": asdict(self._config_from_ui()),
            "countdown": self.countdown_var.get(),
            "use_seed": self.use_seed_var.get(),
            "seed": self.seed_var.get(),
            "dry_run": self.dry_run_var.get(),
            "rich_shortcuts": self.rich_shortcuts_var.get(),
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load_profile(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        cfg = data.get("typer_config", {})
        key_map = {
            "base_wpm": "Base WPM",
            "variation_pct": "Variation %",
            "burst_min": "Burst min chars",
            "burst_max": "Burst max chars",
            "micro_pause_chance": "Micro pause chance %",
            "think_pause_chance": "Think pause chance %",
            "typo_chance": "Typo chance %",
            "correction_chance": "Correction chance %",
            "warmup_chars": "Warmup chars",
            "fatigue_per_100_chars": "Fatigue % / 100 chars",
        }
        for ck, ui in key_map.items():
            if ck in cfg:
                val = cfg[ck]
                if ck in {"micro_pause_chance", "think_pause_chance", "correction_chance"}:
                    val *= 100
                self.scale_vars[ui].set(val)
        self.countdown_var.set(int(data.get("countdown", self.countdown_var.get())))
        self.use_seed_var.set(bool(data.get("use_seed", self.use_seed_var.get())))
        self.seed_var.set(str(data.get("seed", self.seed_var.get())))
        self._on_use_seed_toggle()
        self.dry_run_var.set(bool(data.get("dry_run", self.dry_run_var.get())))
        self.rich_shortcuts_var.set(bool(data.get("rich_shortcuts", self.rich_shortcuts_var.get())))
        self._refresh_preview()
        self._refresh_debug_panel()

    def start(self):
        text = self.text_input.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showwarning("No text", "Paste or type text first.")
            return

        cfg = self._config_from_ui()
        if cfg.burst_max < cfg.burst_min:
            messagebox.showerror("Invalid config", "Burst max must be >= burst min")
            return

        if self.use_seed_var.get():
            seed_text = self.seed_var.get().strip()
            if not seed_text:
                seed_text = "12345"
                self.seed_var.set(seed_text)
            try:
                seed = int(seed_text)
            except ValueError:
                messagebox.showerror("Invalid seed", "Seed must be an integer")
                return
        else:
            seed = random.SystemRandom().randint(1, 2_147_483_647)

        self.total_chars = len(text)
        self.stop_event.clear()
        self.pause_event.clear()
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal", text="Pause (F9)")
        self.stop_btn.config(state="normal")

        self.armed_var.set("ARMED")
        delay = max(0, self.countdown_var.get())
        seed_mode = "fixed" if self.use_seed_var.get() else "stochastic"
        self.status.set(f"Armed. Starting in {delay}s... ({seed_mode} seed)")
        self._refresh_debug_panel()

        self.worker = threading.Thread(
            target=self._worker,
            args=(text, cfg, delay, self.rich_shortcuts_var.get(), seed, self.dry_run_var.get()),
            daemon=True,
        )
        self.worker.start()

    def _worker(self, text: str, cfg: TyperConfig, delay: int, rich_shortcuts: bool, seed: int, dry_run: bool):
        random.seed(seed)
        logger = EventLogger(self.log_events_var.get())
        stats = RunStats(start_ts=time.time())

        self._ui(lambda: self.status.set(f"Armed (seed={seed})."))
        self._ui(lambda: self.log_box.delete("1.0", "end"))

        for remaining in range(delay, 0, -1):
            if self.stop_event.is_set():
                break
            self._ui(lambda r=remaining: self.status.set(f"ARMED: {r}..."))
            time.sleep(1)

        if self.stop_event.is_set():
            stats.end_ts = time.time()
            self._finish("Stopped", stats, logger, seed)
            return

        if self.guard_window_var.get():
            try:
                win = pyautogui.getActiveWindow()
                title = win.title if win else ""
            except Exception:
                title = ""
            if not title:
                self._ui(lambda: self.status.set("Warning: no active window detected."))
            else:
                self._ui(lambda: self.status.set(f"Typing into: {title}"))

        typer = HumanTyper(
            cfg,
            self.stop_event,
            self.pause_event,
            logger,
            stats,
            progress_cb=lambda c: self._ui(lambda: self.progress_var.set(f"Typed {c} / {self.total_chars} chars")),
            dry_run=dry_run,
        )
        try:
            typer.run_formatted(text, rich_shortcuts=rich_shortcuts)
            state = "Stopped" if self.stop_event.is_set() else "Done"
        except Exception as exc:
            state = f"Error: {exc}"

        stats.end_ts = time.time()
        self._finish(state, stats, logger, seed)

    def _finish(self, msg: str, stats: RunStats, logger: EventLogger, seed: int):
        def ui():
            self.armed_var.set("DISARMED")
            self.status.set(msg)
            self.start_btn.config(state="normal")
            self.pause_btn.config(state="disabled", text="Pause (F9)")
            self.stop_btn.config(state="disabled")
            self.summary_var.set(
                f"Run summary: seed={seed} | WPM={stats.effective_wpm():.1f} | chars={stats.chars_typed} | typos={stats.typo_count} | corrections={stats.correction_count} | micro_pause={stats.micro_pause_total:.2f}s | think_pause={stats.think_pause_total:.2f}s | duration={stats.end_ts - stats.start_ts:.2f}s"
            )
            if logger.enabled:
                for ts, kind, detail in logger.events[-400:]:
                    self.log_box.insert("end", f"{ts:.3f}\t{kind}\t{detail}\n")
                self.log_box.see("end")
            self._refresh_debug_panel()

        self._ui(ui)

    def pause_resume(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.status.set("Resumed")
            self.pause_btn.config(text="Pause (F9)")
        else:
            if self.start_btn["state"] == "disabled":
                self.pause_event.set()
                self.status.set("Paused")
                self.pause_btn.config(text="Resume (F9)")
        self._refresh_debug_panel()

    def emergency_stop(self):
        self.stop()
        self.status.set("EMERGENCY STOP")

    def stop(self):
        self.stop_event.set()
        self.pause_event.clear()
        self.status.set("Stopping...")
        self._refresh_debug_panel()


    def _resolve_git_repo(self):
        candidates = [Path(__file__).resolve().parent, Path.cwd()]
        exe_path = getattr(sys, "executable", "")
        if exe_path:
            candidates.append(Path(exe_path).resolve().parent)

        seen = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            probe = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=candidate,
                capture_output=True,
                text=True,
            )
            if probe.returncode == 0:
                return Path(probe.stdout.strip())
        return None

    def update_from_git(self):
        def worker():
            repo_dir = self._resolve_git_repo()
            if repo_dir is None:
                msg = "Update unavailable: this copy is not inside a Git repository. Use a cloned repo checkout to update from Git."
                self._ui(lambda text=msg: self.status.set(text))
                self._ui(lambda text=msg: self.log_box.insert("end", f"[update-error]\n{text}\n"))
                return

            try:
                result = subprocess.run(
                    ["git", "pull", "--ff-only"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                out = (result.stdout or "").strip()
                if result.stderr:
                    out = f"{out}\n{result.stderr.strip()}".strip()
                self._ui(lambda out_text=out: self.status.set("Update complete. Restart app manually if files changed."))
                self._ui(lambda out_text=out: self.log_box.insert("end", f"[update]\n{out_text}\n"))
            except subprocess.CalledProcessError as exc:
                err_out = "\n".join(part.strip() for part in [exc.stdout or "", exc.stderr or ""] if part.strip())
                err_msg = err_out or str(exc)
                self._ui(lambda err=err_msg: self.status.set(f"Update failed: {err}"))
                self._ui(lambda err=err_msg: self.log_box.insert("end", f"[update-error]\n{err}\n"))
            except Exception as exc:
                self._ui(lambda err=str(exc): self.status.set(f"Update failed: {err}"))
                self._ui(lambda err=str(exc): self.log_box.insert("end", f"[update-error]\n{err}\n"))

        threading.Thread(target=worker, daemon=True).start()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
