import json
import threading
from dataclasses import dataclass
from queue import Queue
from typing import Any, Optional

from core.dispatcher import dispatch
from core.stt import VoiceListener
from core.wake_word import WakeAction, WakeWordDetector
from settings.settings_manager import settings_manager
from tts.tts_engine import TTSEngine


@dataclass(frozen=True)
class UiEvent:
    type: str
    payload: dict


class AssistantWorker:
    """Runs STT -> dispatch loop on a background thread and emits UI events."""

    def __init__(self, event_queue: Queue, default_language: Optional[str] = None):
        self._queue = event_queue
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._active = False  # standby until wake phrase
        self._wake = WakeWordDetector()

        self.listener = VoiceListener(default_language=default_language or settings_manager.language)
        settings_manager.attach_listener(self.listener)

        self.tts_engine = TTSEngine()
        settings_manager.attach_tts_engine(self.tts_engine)

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="AssistantWorker", daemon=True)
        self._thread.start()
        self._emit("status", state="standby")
        self._emit_config()

    def stop(self) -> None:
        self._stop_event.set()
        self._emit("status", state="stopping")

    def shutdown(self, join_timeout_s: float = 2.0) -> None:
        self.stop()
        if self._thread:
            self._thread.join(timeout=join_timeout_s)

    def _emit(self, event_type: str, **payload: Any) -> None:
        self._queue.put(UiEvent(type=event_type, payload=dict(payload)))

    def _emit_config(self) -> None:
        self._emit(
            "config",
            language=settings_manager.language,
            gender=settings_manager.voice_gender,
            speed=settings_manager.speech_speed,
        )

    def _run(self) -> None:
        # Start in standby (no command processing) until wake phrase.
        name = settings_manager.username.strip() if getattr(settings_manager, "username", "") else ""
        self._emit("system", text=settings_manager.speak_localized(
            f"أهلاً {name}. قل: اهلا EGB لتشغيل المساعد" if name else "قل: اهلا EGB لتشغيل المساعد",
            f"Hi {name}. Say: Hi EGB to start" if name else "Say: Hi EGB to start",
        ))
        self._emit_config()

        while not self._stop_event.is_set():
            try:
                self._emit("status", state="listening" if self._active else "standby")

                # In standby, listen in both languages for better wake reliability.
                if not self._active:
                    recognized_text = self.listener.listen_any(
                        ["ar-EG", "en-US"],
                        prompt="[STT] Wake listening...",
                        timeout=8,
                        phrase_time_limit=6,
                    )
                else:
                    recognized_text = self.listener.listen_command()

                if self._stop_event.is_set():
                    break
                if not recognized_text:
                    continue

                wake = self._wake.detect(recognized_text)

                # Voice START when in standby.
                if not self._active and wake and wake.action == WakeAction.START:
                    # Determine language from the wake phrase and keep setup in that language.
                    session_lang = self._infer_session_language(recognized_text)
                    if session_lang:
                        settings_manager.set_language(session_lang)
                        self.listener.set_language(session_lang)

                    self._active = True

                    # First-run setup (voice) happens AFTER wake.
                    if not settings_manager.is_configured():
                        self._emit("status", state="setup")
                        self._emit("assistant", text=settings_manager.speak_localized(
                            "إعداد أول مرة. هسألك شوية أسئلة. لو ما فهمتش هعيد تاني.",
                            "First time setup. I'll ask a few questions. If I miss it, I'll ask again.",
                        ))
                        self._run_voice_onboarding(session_lang=settings_manager.language)
                        self._emit_config()

                    greeting = settings_manager.speak_localized(
                        "تمام. أنا جاهز، اتفضل",
                        "Alright. I'm listening.",
                    )
                    self._emit("assistant", text=greeting)
                    self._emit("status", state="online")
                    continue

                # Ignore everything except wake phrase while in standby.
                if not self._active:
                    continue

                # Never close/stop the app by voice. If the user says "close/stop/exit",
                # respond and keep the assistant running.
                if self._is_close_intent(recognized_text):
                    msg = settings_manager.speak_localized(
                        "تمام—مش هقفل. أنا موجود.",
                        "Okay — I won't close. I'm here.",
                    )
                    self._emit("assistant", text=msg)
                    self._emit("status", state="online")
                    continue

                # Polite thanks should not affect state.
                if self._is_thanks_intent(recognized_text):
                    msg = settings_manager.speak_localized("العفو!", "You're welcome!")
                    self._emit("assistant", text=msg)
                    self._emit("status", state="online")
                    continue

                self._emit("user", text=recognized_text)
                self._emit("status", state="thinking")

                result = dispatch(recognized_text)

                # Settings might have changed by voice commands.
                self._emit_config()

                if result is None:
                    # dispatch already spoke a localized fallback; UI still wants something.
                    self._emit("assistant", text=settings_manager.speak_localized(
                        "معذرة، لم أفهم هذا الأمر",
                        "Sorry, I didn't understand that command.",
                    ))
                elif isinstance(result, str):
                    self._emit("assistant", text=result)
                else:
                    try:
                        self._emit("assistant", text=json.dumps(result, ensure_ascii=False, indent=2))
                    except Exception:
                        self._emit("assistant", text=str(result))

            except Exception as err:  # noqa: BLE001
                self._emit("error", message=str(err))

        goodbye = settings_manager.speak_localized(
            "تم إيقاف المساعد",
            "Assistant stopped",
        )
        self._emit("assistant", text=goodbye)
        self._emit("status", state="offline")

    def _is_close_intent(self, text: str) -> bool:
        t = (text or "").lower()
        if not t:
            return False
        # Arabic + English "close/exit" variants.
        close_words = (
            "اقفل",
            "قفل",
            "قف",
            "وقف",
            "اخرج",
            "خروج",
            "انهاء",
            "انهِي",
            "مع السلامه",
            "باي",
            "وداعا",
            "stop",
            "close",
            "quit",
            "exit",
            "shutdown",
            "goodbye",
            "bye",
        )
        return any(w in t for w in close_words)

    def _is_thanks_intent(self, text: str) -> bool:
        t = (text or "").lower()
        if not t:
            return False
        thanks_words = (
            "شكرا",
            "شكر",
            "متشكر",
            "thanks",
            "thank you",
        )
        return any(w in t for w in thanks_words)

    def _infer_session_language(self, text: str) -> Optional[str]:
        if not text:
            return None
        if any("\u0600" <= ch <= "\u06FF" for ch in text):
            return "ar-EG"
        lowered = text.lower()
        if any(word in lowered for word in ("hi", "hello", "hey")):
            return "en-US"
        return None

    def _run_voice_onboarding(self, session_lang: str) -> None:
        """Voice-only first-run setup.

        - Runs after wake
        - Keeps asking (does NOT shut down assistant)
        - Uses the wake language for prompts
        """

        if session_lang:
            settings_manager.set_language(session_lang)
            self.listener.set_language(session_lang)

        # Ask language (optional) but keep prompt language consistent.
        for _ in range(6):
            settings_manager.speak_localized(
                "تحب المساعد عربي ولا إنجليزي؟ قل: عربي أو English",
                "Do you prefer Arabic or English? Say: Arabic or English",
            )
            lang_answer = self.listener.listen_any(["ar-EG", "en-US"], prompt="[SETUP] Language", timeout=8, phrase_time_limit=6)
            if not lang_answer:
                continue
            lowered = lang_answer.lower()
            if any(word in lowered for word in ("arabic", "عربي", "العربية")):
                settings_manager.set_language("ar-EG")
                self.listener.set_language("ar-EG")
                break
            if any(word in lowered for word in ("english", "انجليزي", "انجلش")):
                settings_manager.set_language("en-US")
                self.listener.set_language("en-US")
                break

        self._emit_config()

        # Voice gender
        for _ in range(6):
            settings_manager.speak_localized(
                "اختار نوع الصوت: ذكر ولا أنثى؟",
                "Choose voice: male or female?",
            )
            gender_answer = self.listener.listen_any([settings_manager.language, "en-US", "ar-EG"], prompt="[SETUP] Gender", timeout=8, phrase_time_limit=6)
            if not gender_answer:
                continue
            g = gender_answer.lower()
            if any(word in g for word in ("male", "ذكر")):
                settings_manager.set_voice_gender("male")
                break
            if any(word in g for word in ("female", "انثى", "أنثى", "بنت")):
                settings_manager.set_voice_gender("female")
                break

        self._emit_config()

        # Speech speed
        for _ in range(8):
            settings_manager.speak_localized(
                "اختار سرعة الكلام: طبيعي، سريع، أو بطيء. أو رقم زي 1.2",
                "Choose speech speed: normal, fast, slow, or a number like 1.2",
            )
            speed_answer = self.listener.listen_any([settings_manager.language, "en-US", "ar-EG"], prompt="[SETUP] Speed", timeout=8, phrase_time_limit=6)
            if not speed_answer:
                continue
            settings_manager.set_speech_speed(self._parse_speed(speed_answer))
            break

        self._emit_config()

        # Username with confirmation. Keep trying until confirmed.
        while not self._stop_event.is_set() and not settings_manager.is_configured():
            settings_manager.speak_localized("قول اسمك", "Tell me your name")
            name = self.listener.listen_any([settings_manager.language, "en-US", "ar-EG"], prompt="[SETUP] Name", timeout=10, phrase_time_limit=7)
            if not name:
                settings_manager.speak_localized("معلش، ما سمعتش. قول اسمك تاني.", "Sorry, I didn't catch that. Say it again.")
                continue
            name = name.strip()

            settings_manager.speak_localized(
                f"هل اسمك {name}؟ قول نعم أو لا",
                f"Is your name {name}? Say yes or no",
            )
            confirm = self.listener.listen_any([settings_manager.language, "en-US", "ar-EG"], prompt="[SETUP] Confirm", timeout=8, phrase_time_limit=4)
            if confirm and self._is_yes(confirm):
                settings_manager.set_username(name)
                self._emit_config()
                settings_manager.speak_localized("تم حفظ الإعدادات. شكرًا!", "Saved. Thank you!")
                break
            settings_manager.speak_localized("تمام، نجرب تاني.", "Okay, let's try again.")

    def _is_yes(self, text: str) -> bool:
        t = (text or "").lower()
        return any(word in t for word in ("yes", "yeah", "yep", "نعم", "ايوه", "أيوه", "تمام"))

    def _parse_speed(self, text: str) -> float:
        t = (text or "").lower()
        # Numeric extraction
        import re

        m = re.search(r"(\d+(?:\.\d+)?)", t)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                pass
        if any(word in t for word in ("fast", "faster", "سريع", "اسرع")):
            return 1.35
        if any(word in t for word in ("slow", "slower", "بطيء", "ابطي")):
            return 0.85
        return settings_manager.default_speech_speed
