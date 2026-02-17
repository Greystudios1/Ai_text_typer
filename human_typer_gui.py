import random
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk

import pyautogui


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


class HumanTyper:
    def __init__(self, config: TyperConfig, stop_event: threading.Event):
        self.config = config
        self.stop_event = stop_event
        self.typed_chars = 0
        self.recent_error = False
        self.state = "flow"

    def run(self, text: str):
        idx = 0
        while idx < len(text) and not self.stop_event.is_set():
            burst_len = random.randint(self.config.burst_min, self.config.burst_max)
            burst_end = min(idx + burst_len, len(text))

            while idx < burst_end and not self.stop_event.is_set():
                char = text[idx]
                prev = text[idx - 1] if idx > 0 else ""

                if self._should_enter_hesitation(char):
                    self.state = "hesitation"
                    time.sleep(random.uniform(0.25, 1.2))
                else:
                    self.state = "flow"

                if self._should_make_typo(char):
                    wrong_char = self._make_adjacent_typo(char)
                    if wrong_char:
                        self._type_char(wrong_char)
                        self.recent_error = True
                        if random.random() < self.config.correction_chance:
                            self._pause_after_error()
                            pyautogui.press("backspace")
                            self._short_delay()
                            self._type_char(char)
                            self.recent_error = False
                        else:
                            idx += 1
                            continue

                self._type_char(char)
                self._flight_delay(prev, char)
                self._boundary_pause(char)
                idx += 1

            if idx < len(text) and random.random() < self.config.think_pause_chance:
                self.state = "hesitation"
                time.sleep(random.uniform(0.6, 3.8))

    def _type_char(self, char: str):
        if self.stop_event.is_set():
            return

        baseline = self._char_interval()
        hold = baseline * random.uniform(0.20, 0.65)
        if char.isupper() or char in "~!@#$%^&*()_+{}|:\\<>?":
            hold *= random.uniform(1.1, 1.4)

        pyautogui.keyDown(char)
        time.sleep(hold)
        pyautogui.keyUp(char)
        self.typed_chars += 1

    def _flight_delay(self, prev_char: str, current_char: str):
        baseline = self._char_interval()

        if self.typed_chars < self.config.warmup_chars:
            baseline *= 1.25 - 0.35 * (self.typed_chars / max(1, self.config.warmup_chars))

        fatigue_factor = 1.0 + (self.config.fatigue_per_100_chars / 100.0) * (self.typed_chars / 100.0)
        baseline *= fatigue_factor

        digraph = (prev_char + current_char).lower()
        baseline *= COMMON_DIGRAPHS.get(digraph, 1.0)

        if current_char.isdigit() or current_char in ",.;:!?()[]{}":
            baseline *= random.uniform(1.2, 1.8)

        variation = self.config.variation_pct / 100.0
        jitter = random.uniform(-variation, variation)
        delay = max(0.01, baseline * (1.0 + jitter))
        time.sleep(delay)

    def _boundary_pause(self, char: str):
        baseline = self._char_interval()
        if char in " ,;":
            if random.random() < self.config.micro_pause_chance:
                time.sleep(baseline * random.uniform(1.2, 5.0))
        if char in ".!?":
            time.sleep(baseline * random.uniform(3.5, 14.0))

    def _short_delay(self):
        baseline = self._char_interval()
        time.sleep(baseline * random.uniform(0.4, 1.8))

    def _pause_after_error(self):
        baseline = self._char_interval()
        time.sleep(baseline * random.uniform(2.4, 10.0))

    def _char_interval(self) -> float:
        cps = (self.config.base_wpm * 5.0) / 60.0
        return 1.0 / max(cps, 0.1)

    def _should_enter_hesitation(self, char: str) -> bool:
        if self.recent_error and random.random() < 0.35:
            return True
        if char in ".,;:!?" and random.random() < 0.25:
            return True
        if char == " " and random.random() < self.config.micro_pause_chance * 0.35:
            return True
        return False

    def _should_make_typo(self, char: str) -> bool:
        if not char.isalpha():
            return False
        chance = self.config.typo_chance / 100.0
        if self.state == "flow":
            chance *= 1.15
        return random.random() < chance

    def _make_adjacent_typo(self, char: str):
        lower = char.lower()
        neighbors = NEIGHBOR_KEYS.get(lower, "")
        if not neighbors:
            return None
        out = random.choice(neighbors)
        return out.upper() if char.isupper() else out


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Human-ish Typer (GUI)")
        self.root.geometry("880x620")

        self.dark_mode_var = tk.BooleanVar(value=True)
        self.advanced_mode_var = tk.BooleanVar(value=False)
        self.debug_mode_var = tk.BooleanVar(value=False)
        self.manual_wpm_var = tk.StringVar(value="70")
        self.slider_base_wpm_var = tk.DoubleVar(value=70)
        self.debug_var = tk.StringVar(value="Debug mode is off")

        self.stop_event = threading.Event()
        self.worker = None
        self._updating_manual_wpm = False

        self._build_menu()
        self._build_ui()
        self.apply_theme()

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_checkbutton(
            label="Dark mode",
            variable=self.dark_mode_var,
            command=self.apply_theme,
        )
        view_menu.add_checkbutton(
            label="Advanced mode",
            variable=self.advanced_mode_var,
            command=self._toggle_advanced_mode,
        )
        view_menu.add_checkbutton(
            label="Debug mode",
            variable=self.debug_mode_var,
            command=self._toggle_debug_mode,
        )
        menubar.add_cascade(label="View", menu=view_menu)
        self.root.config(menu=menubar)

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill="both", expand=True)
        self.main_frame = frm

        ttk.Label(frm, text="Text to type").grid(row=0, column=0, sticky="w")
        self.text_input = tk.Text(frm, height=10, wrap="word")
        self.text_input.grid(row=1, column=0, columnspan=4, sticky="nsew", pady=(4, 12))

        controls = [
            ("Base WPM", 10, 160, 70),
            ("Variation %", 0, 80, 25),
            ("Burst min chars", 1, 30, 6),
            ("Burst max chars", 2, 80, 18),
            ("Micro pause chance %", 0, 100, 30),
            ("Think pause chance %", 0, 100, 14),
            ("Typo chance %", 0, 20, 1),
            ("Correction chance %", 0, 100, 85),
            ("Warmup chars", 0, 300, 40),
            ("Fatigue % / 100 chars", 0, 30, 4),
        ]

        self.scale_vars = {}
        self.control_widgets = {}
        advanced_labels = {
            "Burst min chars",
            "Burst max chars",
            "Micro pause chance %",
            "Think pause chance %",
            "Typo chance %",
            "Correction chance %",
            "Warmup chars",
            "Fatigue % / 100 chars",
        }
        self.advanced_control_labels = advanced_labels
        for i, (label, mn, mx, dv) in enumerate(controls):
            r = 2 + i
            lbl = ttk.Label(frm, text=label)
            lbl.grid(row=r, column=0, sticky="w")
            var = self.slider_base_wpm_var if label == "Base WPM" else tk.DoubleVar(value=dv)
            scl = ttk.Scale(frm, from_=mn, to=mx, variable=var)
            scl.grid(row=r, column=1, sticky="ew", padx=(8, 8))
            val_lbl = ttk.Label(frm, textvariable=var, width=8)
            val_lbl.grid(row=r, column=2, sticky="e")
            self.scale_vars[label] = var
            self.control_widgets[label] = (lbl, scl, val_lbl)

        self.scale_vars["Base WPM"].trace_add("write", self._sync_manual_wpm_from_slider)

        ttk.Label(frm, text="Manual Base WPM").grid(row=2, column=3, sticky="w")
        self.manual_wpm_entry = ttk.Entry(frm, textvariable=self.manual_wpm_var, width=10)
        self.manual_wpm_entry.grid(row=3, column=3, sticky="nw")
        self.manual_wpm_entry.bind("<KeyRelease>", self._sync_slider_from_manual_wpm)
        self.manual_wpm_entry.bind("<FocusOut>", self._validate_manual_wpm_field)

        self.debug_frame = ttk.LabelFrame(frm, text="Debug", padding=8)
        self.debug_frame.grid(row=12, column=3, rowspan=2, sticky="nsew", padx=(12, 0), pady=(10, 0))
        ttk.Label(self.debug_frame, textvariable=self.debug_var, wraplength=220, justify="left").pack(anchor="w")

        self.countdown_var = tk.IntVar(value=4)
        ttk.Label(frm, text="Start delay (seconds)").grid(row=12, column=0, sticky="w", pady=(10, 0))
        ttk.Spinbox(frm, from_=0, to=20, textvariable=self.countdown_var, width=8).grid(row=12, column=1, sticky="w", pady=(10, 0))

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=13, column=0, columnspan=4, sticky="ew", pady=(14, 6))

        self.start_btn = ttk.Button(btn_frame, text="Start Typing", command=self.start)
        self.start_btn.pack(side="left")

        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=(8, 0))

        self.status = tk.StringVar(value="Ready")
        ttk.Label(frm, textvariable=self.status).grid(row=14, column=0, columnspan=4, sticky="w", pady=(8, 0))

        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(1, weight=1)
        frm.columnconfigure(3, weight=0)

        self._toggle_advanced_mode()
        self._toggle_debug_mode()

    def apply_theme(self):
        style = ttk.Style(self.root)
        if self.dark_mode_var.get():
            bg = "#1e1e1e"
            fg = "#f2f2f2"
            entry_bg = "#2a2a2a"
            text_bg = "#181818"
            text_fg = "#f1f1f1"
        else:
            bg = "#f2f2f2"
            fg = "#202020"
            entry_bg = "#ffffff"
            text_bg = "#ffffff"
            text_fg = "#202020"

        self.root.configure(bg=bg)
        style.configure("TFrame", background=bg)
        style.configure("TLabelframe", background=bg, foreground=fg)
        style.configure("TLabelframe.Label", background=bg, foreground=fg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TButton", padding=5)
        style.configure("TEntry", fieldbackground=entry_bg, foreground=fg)
        style.configure("TSpinbox", fieldbackground=entry_bg, foreground=fg)
        self.text_input.configure(bg=text_bg, fg=text_fg, insertbackground=text_fg)

    def _toggle_advanced_mode(self):
        if self.advanced_mode_var.get():
            for label in self.advanced_control_labels:
                for widget in self.control_widgets[label]:
                    widget.grid()
        else:
            for label in self.advanced_control_labels:
                for widget in self.control_widgets[label]:
                    widget.grid_remove()

    def _toggle_debug_mode(self):
        if self.debug_mode_var.get():
            self.debug_frame.grid()
            self._update_debug("Debug mode enabled")
        else:
            self.debug_frame.grid_remove()

    def _update_debug(self, msg: str):
        if not self.debug_mode_var.get():
            return

        def _set_msg():
            self.debug_var.set(msg)

        self.root.after(0, _set_msg)

    def _sync_manual_wpm_from_slider(self, *_):
        if self._updating_manual_wpm:
            return
        self._updating_manual_wpm = True
        try:
            self.manual_wpm_var.set(f"{self.slider_base_wpm_var.get():.2f}".rstrip("0").rstrip("."))
        finally:
            self._updating_manual_wpm = False

    def _sync_slider_from_manual_wpm(self, _event=None):
        if self._updating_manual_wpm:
            return
        raw = self.manual_wpm_var.get().strip()
        if not raw:
            return
        try:
            val = float(raw)
        except ValueError:
            return

        self._updating_manual_wpm = True
        try:
            self.slider_base_wpm_var.set(min(160, max(10, val)))
        finally:
            self._updating_manual_wpm = False

    def _validate_manual_wpm_field(self, _event=None):
        raw = self.manual_wpm_var.get().strip()
        if not raw:
            return
        try:
            val = float(raw)
        except ValueError:
            messagebox.showerror("Invalid WPM", "Manual Base WPM must be a valid number.")
            self.manual_wpm_var.set(f"{self.slider_base_wpm_var.get():.2f}".rstrip("0").rstrip("."))
            return

        if val <= 0:
            messagebox.showerror("Invalid WPM", "Manual Base WPM must be greater than zero.")
            self.manual_wpm_var.set(f"{self.slider_base_wpm_var.get():.2f}".rstrip("0").rstrip("."))

    def _config_from_ui(self) -> TyperConfig:
        manual_wpm = self.manual_wpm_var.get().strip()
        try:
            base_wpm = float(manual_wpm)
        except ValueError as exc:
            raise ValueError("Manual Base WPM must be a valid number") from exc
        if base_wpm <= 0:
            raise ValueError("Manual Base WPM must be greater than zero")

        return TyperConfig(
            base_wpm=base_wpm,
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

    def start(self):
        text = self.text_input.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showwarning("No text", "Paste or type text first.")
            return

        try:
            cfg = self._config_from_ui()
        except ValueError as exc:
            messagebox.showerror("Invalid config", str(exc))
            return

        if cfg.burst_max < cfg.burst_min:
            messagebox.showerror("Invalid config", "Burst max must be >= burst min")
            return

        self._update_debug(
            f"Base WPM={cfg.base_wpm:.2f} | Slider={self.slider_base_wpm_var.get():.2f} | Variation={cfg.variation_pct:.1f}%"
        )

        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        delay = max(0, self.countdown_var.get())
        self.status.set(f"Starting in {delay}s. Focus the target input now...")

        self.worker = threading.Thread(target=self._worker, args=(text, cfg, delay), daemon=True)
        self.worker.start()

    def _worker(self, text: str, cfg: TyperConfig, delay: int):
        time.sleep(delay)
        if self.stop_event.is_set():
            self._finish("Stopped")
            return
        self.status.set("Typing...")
        self._update_debug(f"Typing started with char interval ~{60.0 / (cfg.base_wpm * 5.0):.3f}s")

        typer = HumanTyper(cfg, self.stop_event)
        try:
            typer.run(text)
            state = "Stopped" if self.stop_event.is_set() else "Done"
        except Exception as exc:
            state = f"Error: {exc}"
        self._finish(state)

    def _finish(self, msg: str):
        def ui():
            self.status.set(msg)
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

        self.root.after(0, ui)

    def stop(self):
        self.stop_event.set()
        self.status.set("Stopping...")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
