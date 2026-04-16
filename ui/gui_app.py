import time
from dataclasses import dataclass
from queue import Queue, Empty
from typing import Optional

import customtkinter as ctk

from settings.settings_manager import settings_manager
from ui.assistant_worker import AssistantWorker, UiEvent
from ui.orb_widget import OrbWidget


@dataclass(frozen=True)
class ChatMessage:
    role: str  # 'user' | 'assistant' | 'system' | 'error'
    text: str
    ts: float


class VoiceAssistantApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Voice Assistant")
        self.geometry("1100x720")
        self.minsize(900, 600)

        # Load profile (if any) before wiring STT/TTS.
        settings_manager.load_user_profile()

        self._queue: Queue[UiEvent] = Queue()
        self.worker = AssistantWorker(event_queue=self._queue)

        self._status_var = ctk.StringVar(value="offline")
        self._language_var = ctk.StringVar(value=settings_manager.language)
        self._gender_var = ctk.StringVar(value=settings_manager.voice_gender)
        self._speed_var = ctk.StringVar(value=f"{settings_manager.speech_speed:.2f}x")

        self._build_ui()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(80, self._drain_events)

        # Auto-start: worker will run voice onboarding first if needed.
        self.worker.start()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar (minimal)
        sidebar = ctk.CTkFrame(self, corner_radius=16)
        sidebar.grid(row=0, column=0, sticky="nsw", padx=14, pady=14)
        sidebar.grid_rowconfigure(10, weight=1)

        title = ctk.CTkLabel(
            sidebar,
            text="GPT Voice Assistant",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        # Status pill
        status_pill = ctk.CTkFrame(sidebar, corner_radius=999, fg_color="#22262d")
        status_pill.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))
        self._status_dot = ctk.CTkLabel(status_pill, text="●", text_color="#9aa4b2", font=ctk.CTkFont(size=14))
        self._status_dot.grid(row=0, column=0, padx=(10, 6), pady=6)
        status = ctk.CTkLabel(
            status_pill,
            textvariable=self._status_var,
            font=ctk.CTkFont(size=13),
            text_color="#cbd5e1",
        )
        status.grid(row=0, column=1, padx=(0, 10), pady=6)

        btn_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self._start_btn = ctk.CTkButton(btn_row, text="Start", command=self._start)
        self._start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self._stop_btn = ctk.CTkButton(btn_row, text="Stop", command=self._stop, fg_color="#2b2f36")
        self._stop_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # Info card (display-only)
        info_card = ctk.CTkFrame(sidebar, corner_radius=14)
        info_card.grid(row=3, column=0, sticky="ew", padx=14, pady=10)
        info_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(info_card, text="Info", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 6)
        )

        self._lang_label = ctk.CTkLabel(info_card, textvariable=self._language_var, text_color="#dbeafe")
        self._gender_label = ctk.CTkLabel(info_card, textvariable=self._gender_var, text_color="#e5e7eb")
        self._speed_label = ctk.CTkLabel(info_card, textvariable=self._speed_var, text_color="#9aa4b2")

        ctk.CTkLabel(info_card, text="Language", text_color="#9aa4b2").grid(row=1, column=0, sticky="w", padx=12)
        self._lang_label.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 8))

        ctk.CTkLabel(info_card, text="Voice", text_color="#9aa4b2").grid(row=3, column=0, sticky="w", padx=12)
        self._gender_label.grid(row=4, column=0, sticky="w", padx=12, pady=(0, 8))

        ctk.CTkLabel(info_card, text="Speed", text_color="#9aa4b2").grid(row=5, column=0, sticky="w", padx=12)
        self._speed_label.grid(row=6, column=0, sticky="w", padx=12, pady=(0, 12))

        # Main panel
        main = ctk.CTkFrame(self, corner_radius=16)
        main.grid(row=0, column=1, sticky="nsew", padx=(0, 14), pady=14)
        main.grid_rowconfigure(2, weight=1)
        main.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(main, corner_radius=14, fg_color="#101023")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 10))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            header,
            text="Conversation",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=12)

        # Badges row (language/voice/speed)
        badges = ctk.CTkFrame(header, fg_color="transparent")
        badges.grid(row=0, column=1, sticky="e", padx=12, pady=12)

        def _badge(text_var: ctk.StringVar, fg: str) -> ctk.CTkFrame:
            pill = ctk.CTkFrame(badges, corner_radius=999, fg_color=fg)
            ctk.CTkLabel(pill, textvariable=text_var, font=ctk.CTkFont(size=12), text_color="#e5e7eb").grid(
                row=0, column=0, padx=10, pady=6
            )
            return pill

        _badge(self._language_var, "#1f2a44").pack(side="left", padx=6)
        _badge(self._gender_var, "#2b2f36").pack(side="left", padx=6)
        _badge(self._speed_var, "#22262d").pack(side="left", padx=6)

        # Center orb area
        orb_area = ctk.CTkFrame(main, corner_radius=14, fg_color="#0b0b12")
        orb_area.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))
        orb_area.grid_columnconfigure(0, weight=1)

        self._orb = OrbWidget(orb_area, width=600, height=260)
        self._orb.pack(padx=10, pady=8)

        self._chat = ctk.CTkScrollableFrame(main, corner_radius=14)
        self._chat.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))
        self._chat.grid_columnconfigure(0, weight=1)

        self._add_message("system", "جاهز. قل: اهلا EGB / Hi EGB لتشغيل المساعد. (أول مرة هيتم الإعداد بالصوت بعد كلمة التنبيه)")

    def _add_message(self, role: str, text: str) -> None:
        ts = time.strftime("%H:%M")

        if role == "user":
            bubble = ctk.CTkFrame(self._chat, corner_radius=14, fg_color="#1f2a44")
            anchor = "e"
            label_color = "#dbeafe"
            header = "You"
        elif role == "assistant":
            bubble = ctk.CTkFrame(self._chat, corner_radius=14, fg_color="#2b2f36")
            anchor = "w"
            label_color = "#e5e7eb"
            header = "Assistant"
        elif role == "error":
            bubble = ctk.CTkFrame(self._chat, corner_radius=14, fg_color="#3b1e24")
            anchor = "w"
            label_color = "#fecaca"
            header = "Error"
        else:
            bubble = ctk.CTkFrame(self._chat, corner_radius=14, fg_color="#22262d")
            anchor = "w"
            label_color = "#9aa4b2"
            header = "System"

        container = ctk.CTkFrame(self._chat, fg_color="transparent")
        container.grid_columnconfigure(0, weight=1)
        container.grid(sticky="ew", padx=12, pady=6)

        bubble.grid(in_=container, row=0, column=0, sticky=anchor)

        top = ctk.CTkFrame(bubble, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top, text=header, text_color=label_color, font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(top, text=ts, text_color="#9aa4b2", font=ctk.CTkFont(size=11)).grid(
            row=0, column=1, sticky="e"
        )

        ctk.CTkLabel(
            bubble,
            text=text,
            justify="left",
            wraplength=680,
            text_color=label_color,
            font=ctk.CTkFont(size=13),
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 12))

        self.update_idletasks()
        try:
            self._chat._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _set_status(self, state: str) -> None:
        pretty = {
            "offline": "offline",
            "online": "online",
            "stopping": "stopping…",
            "listening": "listening…",
            "thinking": "processing…",
            "standby": "standby (say Hi EGB)…",
            "setup": "setup (voice)…",
        }.get(state, state)
        self._status_var.set(pretty)
        try:
            dot_color = {
                "offline": "#64748b",
                "standby": "#60a5fa",
                "online": "#22c55e",
                "listening": "#60a5fa",
                "thinking": "#f59e0b",
                "stopping": "#f97316",
                "setup": "#a78bfa",
            }.get(state, "#9aa4b2")
            self._status_dot.configure(text_color=dot_color)
        except Exception:
            pass
        try:
            if state in ("listening", "thinking", "online", "offline", "standby"):
                self._orb.set_state(state)
            elif state == "setup":
                self._orb.set_state("thinking")
            elif state == "stopping":
                self._orb.set_state("online")
        except Exception:
            pass

    def _start(self) -> None:
        if self.worker.running:
            return
        self._add_message("system", "Starting voice listener…")
        self.worker.start()

    def _stop(self) -> None:
        if not self.worker.running:
            return
        self._add_message("system", "Stopping…")
        self.worker.stop()

    def _drain_events(self) -> None:
        # Pull events from background thread and apply to UI.
        try:
            while True:
                event = self._queue.get_nowait()
                self._handle_event(event)
        except Empty:
            pass
        self.after(80, self._drain_events)

    def _handle_event(self, event: UiEvent) -> None:
        if event.type == "status":
            self._set_status(event.payload.get("state", ""))
            return

        if event.type == "system":
            self._add_message("system", event.payload.get("text", ""))
            return

        if event.type == "config":
            lang = event.payload.get("language")
            gender = event.payload.get("gender")
            speed = event.payload.get("speed")
            if lang:
                self._language_var.set(str(lang))
            if gender:
                self._gender_var.set(str(gender))
            if speed is not None:
                try:
                    self._speed_var.set(f"{float(speed):.2f}x")
                except Exception:
                    self._speed_var.set(str(speed))
            return

        if event.type == "user":
            self._add_message("user", event.payload.get("text", ""))
            return

        if event.type == "assistant":
            self._add_message("assistant", event.payload.get("text", ""))
            return

        if event.type == "error":
            self._add_message("error", event.payload.get("message", "Unknown error"))
            self._set_status("online")
            return

    def _on_close(self) -> None:
        try:
            if self.worker and self.worker.running:
                self.worker.shutdown()
            try:
                self._orb.stop()
            except Exception:
                pass
        finally:
            self.destroy()


def run_gui() -> None:
    app = VoiceAssistantApp()
    app.mainloop()
