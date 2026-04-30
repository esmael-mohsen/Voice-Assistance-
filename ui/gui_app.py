import time
from dataclasses import dataclass
from queue import Empty, Queue
import logging

import customtkinter as ctk

from core.assistant_runtime import canonical_runtime_state
from settings.settings_manager import settings_manager
from ui.assistant_worker import AssistantWorker, UiEvent
from ui.orb_widget import OrbWidget


@dataclass(frozen=True)
class ChatMessage:
    role: str  # user | assistant | system | error
    text: str
    ts: float


class VoiceAssistantApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Very Modern UI Theme
        BG_APP = "#09090B"  # Deep space dark

        ctk.set_appearance_mode("dark")
        self.configure(fg_color=BG_APP)

        self.title("Voice Assistant Pro")
        self.geometry("1100x720")
        self.minsize(900, 600)

        self._queue: Queue[UiEvent] = Queue()
        self.worker = AssistantWorker(event_queue=self._queue, default_language="en-US")
        self._manual_stop = False
        self._closing = False
        self._last_auto_restart_at = 0.0

        self._status_var = ctk.StringVar(value="offline")
        self._language_var = ctk.StringVar(value=settings_manager.language)
        self._gender_var = ctk.StringVar(value=settings_manager.voice_gender)
        self._speed_var = ctk.StringVar(value=f"{settings_manager.speech_speed:.2f}x")
        self._provider_var = ctk.StringVar(value=settings_manager.speech_provider)

        self._build_ui()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(80, self._drain_events)

        # Runtime owns startup/onboarding; GUI only observes.
        self.worker.start()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # -----------------------------
        # 1. SIDEBAR (MODERN GLASS/CARD)
        # -----------------------------
        BG_PANEL = "#18181B"
        ACCENT_PR = "#8B5CF6"
        TEXT_SEC = "#A1A1AA"
        
        sidebar = ctk.CTkFrame(self, corner_radius=20, fg_color=BG_PANEL)
        sidebar.grid(row=0, column=0, sticky="nsw", padx=16, pady=16)
        sidebar.grid_rowconfigure(10, weight=1)

        # Title
        title_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(24, 16))
        ctk.CTkLabel(
            title_frame, text="EGB", font=ctk.CTkFont("Segoe UI", 26, "bold"), text_color=ACCENT_PR
        ).pack(side="left")
        ctk.CTkLabel(
            title_frame, text=" Assistant", font=ctk.CTkFont("Segoe UI", 26, "normal"), text_color="#FFFFFF"
        ).pack(side="left")

        # Status Pill
        status_pill = ctk.CTkFrame(sidebar, corner_radius=12, fg_color="#27272A")
        status_pill.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 24))
        self._status_dot = ctk.CTkLabel(status_pill, text="●", text_color=TEXT_SEC, font=ctk.CTkFont(size=14))
        self._status_dot.grid(row=0, column=0, padx=(12, 6), pady=8)
        status = ctk.CTkLabel(
            status_pill, textvariable=self._status_var, font=ctk.CTkFont("Segoe UI", 13, "bold"), text_color="#F4F4F5"
        )
        status.grid(row=0, column=1, padx=(0, 16), pady=8)

        # Action Buttons
        btn_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 24))
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self._start_btn = ctk.CTkButton(
            btn_row, text="Start Session", command=self._start,
            font=ctk.CTkFont("Segoe UI", 14, "bold"), fg_color=ACCENT_PR, hover_color="#7C3AED", corner_radius=10, height=40
        )
        self._start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self._stop_btn = ctk.CTkButton(
            btn_row, text="Stop", command=self._stop,
            font=ctk.CTkFont("Segoe UI", 14, "bold"), fg_color="#27272A", hover_color="#3F3F46", text_color="#F4F4F5", corner_radius=10, height=40
        )
        self._stop_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # Info Cards
        info_card = ctk.CTkFrame(sidebar, corner_radius=16, fg_color="transparent")
        info_card.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        info_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(info_card, text="Configuration", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_SEC).grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )

        def _info_row(r_idx: int, label: str, var: ctk.StringVar):
            frame = ctk.CTkFrame(info_card, fg_color="#27272A", corner_radius=8)
            frame.grid(row=r_idx, column=0, sticky="ew", pady=(0, 8))
            frame.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(frame, text=label, text_color=TEXT_SEC, font=ctk.CTkFont(size=12)).grid(row=0, column=0, padx=12, pady=10, sticky="w")
            ctk.CTkLabel(frame, textvariable=var, text_color="#F4F4F5", font=ctk.CTkFont(size=12, weight="bold"), anchor="e").grid(row=0, column=1, padx=12, pady=10, sticky="e")

        _info_row(1, "Language", self._language_var)
        _info_row(2, "Voice", self._gender_var)
        _info_row(3, "Speed", self._speed_var)
        _info_row(4, "Provider", self._provider_var)

        # -----------------------------
        # 2. MAIN AREA
        # -----------------------------
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=(0, 16), pady=16)
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        orb_area = ctk.CTkFrame(main, corner_radius=20, fg_color=BG_PANEL)
        orb_area.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        orb_area.grid_columnconfigure(0, weight=1)

        self._orb = OrbWidget(orb_area, width=700, height=280)
        self._orb.pack(padx=20, pady=20)

        chat_container = ctk.CTkFrame(main, corner_radius=20, fg_color=BG_PANEL)
        chat_container.grid(row=1, column=0, sticky="nsew")
        chat_container.grid_columnconfigure(0, weight=1)
        chat_container.grid_rowconfigure(1, weight=1)

        chat_header = ctk.CTkFrame(chat_container, fg_color="transparent", height=50)
        chat_header.grid(row=0, column=0, sticky="ew", padx=24, pady=(16, 8))
        ctk.CTkLabel(
            chat_header,
            text="Conversation History",
            font=ctk.CTkFont("Segoe UI", 16, "bold"),
            text_color="#F4F4F5"
        ).pack(side="left")

        self._chat = ctk.CTkScrollableFrame(chat_container, fg_color="transparent")
        self._chat.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 16))
        self._chat.grid_columnconfigure(0, weight=1)

        self._add_message("system", "System ready. Click 'Start Session' or say your wake word.")

    def _add_message(self, role: str, text: str) -> None:
        ts = time.strftime("%H:%M")

        if role == "user":
            bubble_color = "#8B5CF6"
            anchor = "e"
            label_color = "#FFFFFF"
            header = "You"
            header_color = "#E5E7EB"
        elif role == "assistant":
            bubble_color = "#27272A"
            anchor = "w"
            label_color = "#F4F4F5"
            header = "EGB Assistant"
            header_color = "#8B5CF6"
        elif role == "error":
            bubble_color = "#4C1D26"
            anchor = "w"
            label_color = "#FECACA"
            header = "Error"
            header_color = "#F87171"
        else:
            bubble_color = "#18181B"
            anchor = "w"
            label_color = "#A1A1AA"
            header = "System"
            header_color = "#71717A"

        container = ctk.CTkFrame(self._chat, fg_color="transparent")
        container.grid_columnconfigure(0, weight=1)
        container.grid(sticky="ew", padx=12, pady=10)

        bubble = ctk.CTkFrame(container, corner_radius=16, fg_color=bubble_color)
        bubble.grid(row=0, column=0, sticky=anchor)

        top = ctk.CTkFrame(bubble, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top, text=header, text_color=header_color, font=ctk.CTkFont("Segoe UI", 12, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(top, text=ts, text_color="#A1A1AA" if role != "user" else "#E5E7EB", font=ctk.CTkFont("Segoe UI", 10)).grid(
            row=0, column=1, sticky="w", padx=(10, 0)
        )

        ctk.CTkLabel(
            bubble, text=text, justify="left", wraplength=650, text_color=label_color, font=ctk.CTkFont("Segoe UI", 14)
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 16))

        self.update_idletasks()
        try:
            self._chat._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _set_status(self, state: str) -> None:
        try:
            state = canonical_runtime_state(state).value
        except Exception:
            pass

        pretty = {
            "offline": "offline",
            "standby": "standby (say Hi EGB)...",
            "wake": "wake detected...",
            "setup": "setup (voice)...",
            "listening": "listening...",
            "thinking": "processing...",
            "speaking": "speaking...",
            "error": "recovering...",
            "online": "listening...",
            "stopping": "offline",
        }.get(state, state)
        self._status_var.set(pretty)
        try:
            dot_color = {
                "offline": "#64748b",
                "standby": "#60a5fa",
                "online": "#22c55e",
                "wake": "#38bdf8",
                "listening": "#60a5fa",
                "thinking": "#f59e0b",
                "speaking": "#22c55e",
                "error": "#ef4444",
                "stopping": "#f97316",
                "setup": "#a78bfa",
            }.get(state, "#9aa4b2")
            self._status_dot.configure(text_color=dot_color)
        except Exception:
            pass
        try:
            if state in ("listening", "thinking", "online", "offline", "standby", "wake", "speaking"):
                self._orb.set_state(state)
            elif state in ("setup", "error"):
                self._orb.set_state("thinking")
            elif state == "stopping":
                self._orb.set_state("online")
        except Exception:
            pass

    def _start(self) -> None:
        self._manual_stop = False
        if self.worker.running:
            return
        self._add_message("system", "Starting runtime...")
        self.worker.start()

    def _stop(self) -> None:
        self._manual_stop = True
        if not self.worker.running:
            return
        self._add_message("system", "Stopping runtime...")
        self.worker.stop()

    def _drain_events(self) -> None:
        try:
            while True:
                event = self._queue.get_nowait()
                self._handle_event(event)
        except Empty:
            pass
        if not self._closing and not self._manual_stop and not self.worker.running:
            now = time.time()
            if now - self._last_auto_restart_at >= 2.0:
                self._last_auto_restart_at = now
                logging.warning("[GUI] Runtime stopped unexpectedly; restarting worker")
                self._add_message("system", "Runtime restarted after unexpected stop.")
                self.worker.start()
        self.after(80, self._drain_events)

    def _handle_event(self, event: UiEvent) -> None:
        if event.type == "status":
            self._set_status(event.payload.get("state", ""))
            return

        if event.type == "system":
            self._add_message("system", event.payload.get("text", ""))
            return

        if event.type == "config":
            language = event.payload.get("language")
            gender = event.payload.get("gender")
            speed = event.payload.get("speed")
            provider = event.payload.get("speech_provider")
            if language:
                self._language_var.set(str(language))
            if gender:
                self._gender_var.set(str(gender))
            if speed is not None:
                try:
                    self._speed_var.set(f"{float(speed):.2f}x")
                except Exception:
                    self._speed_var.set(str(speed))
            if provider:
                self._provider_var.set(str(provider))
            return

        if event.type == "user":
            self._add_message("user", event.payload.get("text", ""))
            return

        if event.type == "assistant":
            self._add_message("assistant", event.payload.get("text", ""))
            return

        if event.type == "error":
            self._add_message("error", event.payload.get("message", "Unknown error"))
            self._set_status(event.payload.get("next_state", "error"))
            return

    def _on_close(self) -> None:
        self._closing = True
        self._manual_stop = True
        try:
            if self.worker:
                self.worker.shutdown()
            try:
                self._orb.stop()
            except Exception:
                pass
        finally:
            self.destroy()


def run_gui() -> None:
    app: VoiceAssistantApp | None = None
    try:
        app = VoiceAssistantApp()
        app.mainloop()
    except KeyboardInterrupt:
        logging.info("[GUI] KeyboardInterrupt received; shutting down GUI gracefully")
        if app is not None:
            try:
                app._on_close()
            except Exception:
                pass
