import math
import tkinter as tk
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OrbTheme:
    # ChatGPT-like dark purple vibe
    bg: str = "#0b0b12"
    panel: str = "#101023"
    orb_outline: str = "#2a2540"
    orb_grad_outer: str = "#140d2b"
    orb_grad_inner: str = "#2a0f5f"
    glow_outer: str = "#5b21b6"
    glow_inner: str = "#a78bfa"
    accent: str = "#c4b5fd"
    accent_dim: str = "#7c3aed"
    text: str = "#a1a1aa"


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_color(c1: str, c2: str, t: float) -> str:
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    r = int(_lerp(r1, r2, t))
    g = int(_lerp(g1, g2, t))
    b = int(_lerp(b1, b2, t))
    return _rgb_to_hex(r, g, b)


class OrbWidget(tk.Canvas):
    """A lightweight animated 'voice orb'.

    This is intentionally not tied to real mic amplitude (keeps deps small).
    Animation intensity is driven by app state (listening/thinking/offline).
    """

    def __init__(
        self,
        master,
        width: int = 340,
        height: int = 240,
        theme: Optional[OrbTheme] = None,
        **kwargs,
    ):
        self.theme = theme or OrbTheme()
        super().__init__(
            master,
            width=width,
            height=height,
            bg=self.theme.bg,
            highlightthickness=0,
            bd=0,
            relief="flat",
            **kwargs,
        )

        self._height = height
        self._width = width
        self._state = "offline"  # offline | standby | listening | thinking | online
        self._phase = 0.0
        self._amp = 0.06
        self._speed = 0.05
        self._job = None

        self._orb_layers: list[int] = []

        self._draw_static()
        self.start()

    def set_state(self, state: str) -> None:
        self._state = state or "online"

    def start(self) -> None:
        if self._job is None:
            self._tick()

    def stop(self) -> None:
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

    def _draw_static(self) -> None:
        self.delete("all")
        cx, cy = self._width // 2, self._height // 2
        r = min(self._width, self._height) * 0.28

        # Background panel tint
        self.create_rectangle(0, 0, self._width, self._height, fill=self.theme.bg, outline="")

        # Outer glow ring (animated)
        self._glow_id = self.create_oval(
            cx - r - 18,
            cy - r - 18,
            cx + r + 18,
            cy + r + 18,
            outline=self.theme.glow_outer,
            width=2,
        )

        # Inner glow ring (static, gives gradient-ish halo)
        self._glow_inner_id = self.create_oval(
            cx - r - 8,
            cy - r - 8,
            cx + r + 8,
            cy + r + 8,
            outline=self.theme.glow_inner,
            width=2,
        )

        # Main orb (radial gradient via concentric ovals)
        self._orb_layers.clear()
        steps = 26
        for i in range(steps, 0, -1):
            t = i / steps
            rr = r * t
            color = _lerp_color(self.theme.orb_grad_outer, self.theme.orb_grad_inner, 1 - t)
            oid = self.create_oval(
                cx - rr,
                cy - rr,
                cx + rr,
                cy + rr,
                fill=color,
                outline="",
            )
            self._orb_layers.append(oid)

        # Orb outline on top
        self._orb_outline_id = self.create_oval(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            fill="",
            outline=self.theme.orb_outline,
            width=2,
        )

        # Wave bars (we update coords only)
        self._bars = []
        bars = 11
        gap = 10
        bar_w = 6
        base_y = cy
        start_x = cx - ((bars - 1) * gap) / 2
        for i in range(bars):
            x = start_x + i * gap
            bar = self.create_line(
                x,
                base_y - 8,
                x,
                base_y + 8,
                fill=self.theme.accent,
                width=bar_w,
                capstyle=tk.ROUND,
            )
            self._bars.append(bar)

        self._label_id = self.create_text(
            cx,
            cy + r + 28,
            text="Tap Start to listen",
            fill=self.theme.text,
            font=("Segoe UI", 11),
        )

    def _tick(self) -> None:
        self._phase += self._speed

        if self._state == "listening":
            self._amp = 0.22
            self._speed = 0.18
            glow = self.theme.glow_inner
            label = "Listening…"
        elif self._state == "standby":
            self._amp = 0.06
            self._speed = 0.05
            glow = self.theme.glow_outer
            label = "Say Hi EGB"
        elif self._state == "thinking":
            self._amp = 0.12
            self._speed = 0.10
            glow = self.theme.glow_outer
            label = "Processing…"
        elif self._state == "online":
            self._amp = 0.08
            self._speed = 0.06
            glow = self.theme.glow_outer
            label = "Online"
        else:
            self._amp = 0.05
            self._speed = 0.04
            glow = "#1f2937"
            label = "Offline"

        # Animate wave bars
        cx, cy = self._width // 2, self._height // 2
        base = 8
        for idx, bar in enumerate(self._bars):
            t = self._phase + idx * 0.35
            height = base + (math.sin(t) * 0.5 + 0.5) * (self._height * 0.12) * self._amp * 6
            x0, _, x1, _ = self.coords(bar)
            self.coords(bar, x0, cy - height, x1, cy + height)
            # Subtle color breathing
            self.itemconfigure(bar, fill=_lerp_color(self.theme.accent_dim, self.theme.accent, (math.sin(t) * 0.5 + 0.5)))

        # Pulse glow radius
        r = min(self._width, self._height) * 0.28
        pulse = 14 + (math.sin(self._phase) * 0.5 + 0.5) * (10 * self._amp * 6)
        self.coords(
            self._glow_id,
            cx - r - pulse,
            cy - r - pulse,
            cx + r + pulse,
            cy + r + pulse,
        )
        self.itemconfigure(self._glow_id, outline=glow)
        self.itemconfigure(self._label_id, text=label)

        self._job = self.after(33, self._tick)
