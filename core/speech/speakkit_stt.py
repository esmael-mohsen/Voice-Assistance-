"""SpeakKit speech-to-text adapter."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from core.command_models import CommandRecognitionResult
from core.speech.interfaces import SpeechToTextService


class SpeakKitSpeechToTextAdapter(SpeechToTextService):
    """Adapter wrapper around a SpeakKit STT backend."""

    def __init__(
        self,
        backend: Any = None,
        *,
        default_language: str = "ar-EG",
        available: bool | None = None,
    ) -> None:
        self._backend = backend
        self._language = default_language
        self._available_override = available

    def set_language(self, language_code: str) -> None:
        self._language = language_code
        setter = getattr(self._backend, "set_language", None)
        if callable(setter):
            setter(language_code)

    def listen_command(self, **kwargs: Any) -> str | None:
        if self._backend is None:
            return None
        listener = getattr(self._backend, "listen_command", None)
        if callable(listener):
            try:
                return listener(
                    timeout=kwargs.get("timeout"),
                    phrase_time_limit=kwargs.get("phrase_time_limit"),
                    interrupt_event=kwargs.get("interrupt_event"),
                )
            except TypeError:
                return listener()
        return None

    def listen_command_result(self, **kwargs: Any) -> CommandRecognitionResult | None:
        if self._backend is None:
            return None
        listener = getattr(self._backend, "listen_command_result", None)
        if callable(listener):
            try:
                return listener(**kwargs)
            except TypeError:
                return listener()
        text = self.listen_command(**kwargs)
        if not text:
            return None
        return CommandRecognitionResult(
            session_id=str(kwargs.get("session_id", "speakkit-session")),
            recognition_path=str(kwargs.get("recognition_path", "local_first")),
            provider_id="speakkit",
            primary_transcript=text,
            confidence_available=False,
            confidence_score=None,
            alternative_transcripts=(text,),
            detected_language=self._language,
            selected_language=self._language,
            latency_ms=0,
            error_code=None,
            recognition_source="legacy_local",
        )

    def listen_any(
        self,
        languages: Sequence[str],
        prompt: str = "[STT] Listening...",
        timeout: int = 7,
        phrase_time_limit: int = 10,
    ) -> str | None:
        if self._backend is None:
            return None
        listener = getattr(self._backend, "listen_any", None)
        if callable(listener):
            return listener(
                list(languages),
                prompt=prompt,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit,
            )
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

    def provider_availability_state(self) -> dict[str, Any]:
        return {
            "provider_source": "cloud_primary",
            "availability": "ready" if self.is_available() else "unavailable",
            "credential_state": "not_required",
            "client_import_state": "available" if self._backend is not None else "missing",
            "network_required": True,
            "startup_safe": True,
            "reason_code": None if self.is_available() else "backend_unavailable",
            "checked_at_ms": 0,
        }

    def recognition_configuration_snapshot(self) -> dict[str, Any]:
        return {}
