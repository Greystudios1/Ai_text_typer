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

    def run_text(self, text: str):
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

    def run_formatted(self, text: str, rich_shortcuts: bool = True):
        lines = text.splitlines()
        for line_idx, line in enumerate(lines):
            if self.stop_event.is_set():
                return

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
            if text.startswith("**", i):
                end = text.find("**", i + 2)
                if end != -1 and end > i + 2:
                    self._toggle_bold(rich_shortcuts)
                    self.run_text(text[i + 2:end])
                    self._toggle_bold(rich_shortcuts)
                    i = end + 2
                    continue
            if text[i] in "*_":
                marker = text[i]
                end = text.find(marker, i + 1)
                if end != -1 and end > i + 1:
                    self._toggle_italic(rich_shortcuts)
                    self.run_text(text[i + 1:end])
                    self._toggle_italic(rich_shortcuts)
                    i = end + 1
                    continue

            self._type_char(text[i])
            prev = text[i - 1] if i > 0 else ""
            self._flight_delay(prev, text[i])
            self._boundary_pause(text[i])
            i += 1

    def _toggle_bold(self, rich_shortcuts: bool):
        if rich_shortcuts:
            pyautogui.hotkey("ctrl", "b")
            self._short_delay()

    def _toggle_italic(self, rich_shortcuts: bool):
        if rich_shortcuts:
            pyautogui.hotkey("ctrl", "i")
            self._short_delay()

    def _type_bullet(self, rich_shortcuts: bool):
        if rich_shortcuts:
            try:
                pyautogui.hotkey("ctrl", "shift", "8")
                self._short_delay()
                return
            except Exception:
                pass
        self.run_text("- ")

    def _type_char(self, char: str):
        if self.stop_event.is_set():
            return

        if char == "\n":
            pyautogui.press("enter")
            self.typed_chars += 1
            return
        if char == "\t":
            pyautogui.press("tab")
            self.typed_chars += 1
            return

        hold = random.uniform(0.03, 0.11)
        if char.isupper() or char in "~!@#$%^&*()_+{}|:\\<>?":
            hold *= random.uniform(1.1, 1.4)

        pyautogui.keyDown(char)
        time.sleep(hold)
        pyautogui.keyUp(char)
        self.typed_chars += 1

    def _flight_delay(self, prev_char: str, current_char: str):
        cps = (self.config.base_wpm * 5.0) / 60.0
        baseline = 1.0 / max(cps, 0.1)

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
        if char in " ,;":
            if random.random() < self.config.micro_pause_chance:
                time.sleep(random.uniform(0.08, 0.35))
        if char in ".!?":
            time.sleep(random.uniform(0.25, 1.0))

    def _short_delay(self):
        time.sleep(random.uniform(0.03, 0.12))

    def _pause_after_error(self):
        time.sleep(random.uniform(0.18, 0.7))

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
        self.root.title("Human-ish Typer v2 (Formatted Text)")
        self.root.geometry("920x680")

        self.stop_event = threading.Event()
        self.worker = None

        self._build_ui()

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Formatted text to type (supports **bold**, *italic*, bullet lines '- ') ").grid(row=0, column=0, sticky="w")
        self.text_input = tk.Text(frm, height=12, wrap="word")
        self.text_input.grid(row=1, column=0, columnspan=4, sticky="nsew", pady=(4, 8))

        self.rich_shortcuts_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frm,
            text="Use rich-text shortcuts (Ctrl+B, Ctrl+I, Ctrl+Shift+8 for bullets)",
            variable=self.rich_shortcuts_var,
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(0, 10))

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
        for i, (label, mn, mx, dv) in enumerate(controls):
            r = 3 + i
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w")
            var = tk.DoubleVar(value=dv)
            scl = ttk.Scale(frm, from_=mn, to=mx, variable=var)
            scl.grid(row=r, column=1, sticky="ew", padx=(8, 8))
            ttk.Label(frm, textvariable=var, width=8).grid(row=r, column=2, sticky="e")
            self.scale_vars[label] = var

        self.countdown_var = tk.IntVar(value=4)
        ttk.Label(frm, text="Start delay (seconds)").grid(row=13, column=0, sticky="w", pady=(10, 0))
        ttk.Spinbox(frm, from_=0, to=20, textvariable=self.countdown_var, width=8).grid(row=13, column=1, sticky="w", pady=(10, 0))

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=14, column=0, columnspan=4, sticky="ew", pady=(14, 6))

        self.start_btn = ttk.Button(btn_frame, text="Start Typing", command=self.start)
        self.start_btn.pack(side="left")

        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=(8, 0))

        self.status = tk.StringVar(value="Ready")
        ttk.Label(frm, textvariable=self.status).grid(row=15, column=0, columnspan=4, sticky="w", pady=(8, 0))

        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(1, weight=1)

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

    def start(self):
        text = self.text_input.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showwarning("No text", "Paste or type text first.")
            return

        cfg = self._config_from_ui()
        if cfg.burst_max < cfg.burst_min:
            messagebox.showerror("Invalid config", "Burst max must be >= burst min")
            return

        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        delay = max(0, self.countdown_var.get())
        self.status.set(f"Starting in {delay}s. Focus the target input now...")

        self.worker = threading.Thread(
            target=self._worker,
            args=(text, cfg, delay, self.rich_shortcuts_var.get()),
            daemon=True,
        )
        self.worker.start()

    def _worker(self, text: str, cfg: TyperConfig, delay: int, rich_shortcuts: bool):
        time.sleep(delay)
        if self.stop_event.is_set():
            self._finish("Stopped")
            return
        self.status.set("Typing...")

        typer = HumanTyper(cfg, self.stop_event)
        try:
            typer.run_formatted(text, rich_shortcuts=rich_shortcuts)
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
