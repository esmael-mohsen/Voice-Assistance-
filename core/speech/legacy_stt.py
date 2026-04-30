"""Legacy speech-to-text adapter."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from core.speech.interfaces import SpeechToTextService
from core.stt import VoiceListener
from core.command_models import CommandRecognitionResult


class LegacySpeechToTextAdapter(SpeechToTextService):
    """Adapter over the existing VoiceListener implementation."""

    def __init__(self, listener: VoiceListener | None = None, *, default_language: str = "ar-EG") -> None:
        self._listener = listener or VoiceListener(default_language=default_language)

    @property
    def listener(self) -> VoiceListener:
        return self._listener

    def set_language(self, language_code: str) -> None:
        self._listener.set_language(language_code)

    def listen_command(self, **kwargs: Any) -> str | None:
        listener = getattr(self._listener, "listen_command_window", None)
        if callable(listener):
            listener_language = str(getattr(self._listener, "language", "") or "").strip()
            language_candidates: list[str] = []
            if listener_language:
                language_candidates.append(listener_language)
            for language_code in ("en-US", "ar-EG"):
                if language_code not in language_candidates:
                    language_candidates.append(language_code)
            try:
                return listener(
                    timeout_s=kwargs.get("timeout"),
                    phrase_time_limit_s=kwargs.get("phrase_time_limit"),
                    interrupt_event=kwargs.get("interrupt_event"),
                    languages=language_candidates,
                )
            except TypeError:
                try:
                    return listener(
                        timeout_s=kwargs.get("timeout"),
                        phrase_time_limit_s=kwargs.get("phrase_time_limit"),
                        interrupt_event=kwargs.get("interrupt_event"),
                        usage_mode=kwargs.get("usage_mode", "command"),
                        closed_vocabulary_id=kwargs.get("closed_vocabulary_id"),
                        closed_vocabulary_choices=kwargs.get("closed_vocabulary_choices"),
                    )
                except TypeError:
                    pass
        try:
            return self._listener.listen_command(**kwargs)
        except TypeError:
            return self._listener.listen_command()

    def listen_command_result(self, **kwargs: Any) -> CommandRecognitionResult | None:
        listener = getattr(self._listener, "listen_command_result", None)
        if callable(listener):
            try:
                return listener(
                    timeout_s=kwargs.get("timeout") or kwargs.get("timeout_s"),
                    phrase_time_limit_s=kwargs.get("phrase_time_limit") or kwargs.get("phrase_time_limit_s"),
                    interrupt_event=kwargs.get("interrupt_event"),
                    languages=kwargs.get("languages"),
                    recognition_path=kwargs.get("recognition_path", "local_first"),
                    session_id=kwargs.get("session_id"),
                    force_missing_confidence=bool(kwargs.get("force_missing_confidence", False)),
                    usage_mode=kwargs.get("usage_mode", "command"),
                    capture_profile_id=kwargs.get("capture_profile_id"),
                    closed_vocabulary_id=kwargs.get("closed_vocabulary_id"),
                    closed_vocabulary_choices=kwargs.get("closed_vocabulary_choices"),
                    dictionary_bias_mode=kwargs.get("dictionary_bias_mode"),
                    qualification_profile_id=kwargs.get("qualification_profile_id", "default"),
                    recovery_prompt_surface=kwargs.get("recovery_prompt_surface"),
                    attempt_index=int(kwargs.get("attempt_index", 0) or 0),
                )
            except TypeError:
                try:
                    return listener(**kwargs)
                except TypeError:
                    pass
        listen_command = getattr(self._listener, "listen_command", None)
        if callable(listen_command):
            text = listen_command(**kwargs)
            if text:
                return CommandRecognitionResult(
                    session_id=str(kwargs.get("session_id", "legacy-session")),
                    recognition_path=str(kwargs.get("recognition_path", "local_first")),
                    provider_id="legacy",
                    primary_transcript=text,
                    confidence_available=False,
                    confidence_score=None,
                    alternative_transcripts=(text,),
                    detected_language=getattr(self._listener, "language", "en-US"),
                    selected_language=getattr(self._listener, "language", "en-US"),
                    latency_ms=0,
                    error_code=None,
                    recognition_source="legacy_local",
                )
        return None

    def listen_any(
        self,
        languages: Sequence[str],
        prompt: str = "[STT] Listening...",
        timeout: int = 7,
        phrase_time_limit: int = 10,
    ) -> str | None:
        return self._listener.listen_any(
            list(languages),
            prompt=prompt,
            timeout=timeout,
            phrase_time_limit=phrase_time_limit,
        )

    def is_available(self) -> bool:
        checker = getattr(self._listener, "is_available", None)
        if callable(checker):
            return bool(checker())
        return True

    def provider_availability_state(self) -> dict[str, Any]:
        probe = getattr(self._listener, "provider_availability_state", None)
        if callable(probe):
            try:
                payload = probe()
                if isinstance(payload, dict):
                    return dict(payload)
            except Exception:  # noqa: BLE001
                return {}
        return {}

    def recognition_configuration_snapshot(self) -> dict[str, Any]:
        probe = getattr(self._listener, "recognition_configuration_snapshot", None)
        if callable(probe):
            try:
                payload = probe()
                if isinstance(payload, dict):
                    return dict(payload)
            except Exception:  # noqa: BLE001
                return {}
        return {}

    def request_stop(self) -> None:
        stopper = getattr(self._listener, "request_stop", None)
        if callable(stopper):
            stopper()
