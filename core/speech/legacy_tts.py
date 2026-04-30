"""Legacy text-to-speech adapter."""

from __future__ import annotations

from typing import Any

from core.speech.interfaces import TextToSpeechService
from tts.tts_engine import TTSEngine


class LegacyTextToSpeechAdapter(TextToSpeechService):
    """Adapter over the existing TTSEngine implementation."""

    def __init__(self, tts_engine: TTSEngine | None = None) -> None:
        self._tts_engine = tts_engine or TTSEngine()

    @property
    def engine(self) -> TTSEngine:
        return self._tts_engine

    def configure(self, **kwargs: Any) -> None:
        configure = getattr(self._tts_engine, "configure", None)
        if callable(configure):
            configure(**kwargs)

    def set_language(self, language_code: str) -> None:
        self._tts_engine.set_language(language_code)

    def set_voice_gender(self, gender: str) -> None:
        self._tts_engine.set_voice_gender(gender)

    def set_speech_speed(self, speed: float) -> None:
        self._tts_engine.set_speech_speed(speed)

    def set_voice_profile(self, voice_id: str) -> None:
        setter = getattr(self._tts_engine, "set_voice_profile", None)
        if callable(setter):
            setter(voice_id)

    def speak(self, text: str, **kwargs: Any) -> Any:
        speaker = getattr(self._tts_engine, "speak", None)
        if callable(speaker):
            try:
                return speaker(text, **kwargs)
            except TypeError:
                return speaker(text)
        return None

    def is_available(self) -> bool:
        checker = getattr(self._tts_engine, "is_available", None)
        if callable(checker):
            return bool(checker())
        return True

    def request_stop(self) -> None:
        stopper = getattr(self._tts_engine, "request_stop", None)
        if callable(stopper):
            stopper()

    def clear_stop_request(self) -> None:
        clearer = getattr(self._tts_engine, "clear_stop_request", None)
        if callable(clearer):
            clearer()
