"""SpeakKit text-to-speech adapter."""

from __future__ import annotations

from typing import Any

from core.speech.interfaces import TextToSpeechService


class SpeakKitTextToSpeechAdapter(TextToSpeechService):
    """Adapter wrapper around a SpeakKit TTS backend."""

    def __init__(self, backend: Any = None, *, available: bool | None = None) -> None:
        self._backend = backend
        self._language = "ar-EG"
        self._voice_gender = "female"
        self._speech_speed = 1.0
        self._available_override = available

    def configure(self, **kwargs: Any) -> None:
        configure = getattr(self._backend, "configure", None)
        if callable(configure):
            configure(**kwargs)

    def set_language(self, language_code: str) -> None:
        self._language = language_code
        setter = getattr(self._backend, "set_language", None)
        if callable(setter):
            setter(language_code)

    def set_voice_gender(self, gender: str) -> None:
        self._voice_gender = gender
        setter = getattr(self._backend, "set_voice_gender", None)
        if callable(setter):
            setter(gender)

    def set_speech_speed(self, speed: float) -> None:
        self._speech_speed = speed
        setter = getattr(self._backend, "set_speech_speed", None)
        if callable(setter):
            setter(speed)

    def set_voice_profile(self, voice_id: str) -> None:
        setter = getattr(self._backend, "set_voice_profile", None)
        if callable(setter):
            setter(voice_id)

    def speak(self, text: str, **kwargs: Any) -> Any:
        if self._backend is None:
            return None
        speaker = getattr(self._backend, "speak", None)
        if callable(speaker):
            try:
                return speaker(text, **kwargs)
            except TypeError:
                return speaker(text)
        return None

    def is_available(self) -> bool:
        if self._available_override is not None:
            return bool(self._available_override)
        checker = getattr(self._backend, "is_available", None)
        if callable(checker):
            return bool(checker())
        return self._backend is not None

    def request_stop(self) -> None:
        stopper = getattr(self._backend, "request_stop", None)
        if callable(stopper):
            stopper()
