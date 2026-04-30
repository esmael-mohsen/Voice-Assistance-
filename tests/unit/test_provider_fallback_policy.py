"""Unit tests for directional provider fallback rules."""

from __future__ import annotations

from core.speech.interfaces import LEGACY_PROVIDER_ID, SPEAKKIT_PROVIDER_ID, SpeechProviderProfile
from core.speech.provider_registry import ProviderBundle, ProviderRegistry
from core.speech.provider_resolver import (
    DUAL_PROVIDER_UNAVAILABLE_REASON,
    LEGACY_NO_AUTOSWITCH_REASON,
    SPEAKKIT_FALLBACK_REASON,
    resolve_runtime_failure,
)


class _Svc:
    def __init__(self, *, available: bool) -> None:
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def detect(self, _text):
        return None

    def listen_command(self):
        return None

    def listen_any(self, _languages, prompt="", timeout=0, phrase_time_limit=0):
        return None

    def set_language(self, _language):
        return None

    def set_voice_gender(self, _gender):
        return None

    def set_speech_speed(self, _speed):
        return None

    def speak(self, _text):
        return None

    def configure(self, **_kwargs):
        return None


def _registry(*, legacy_available: bool, speakkit_available: bool) -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(
        ProviderBundle(
            profile=SpeechProviderProfile(provider_id=LEGACY_PROVIDER_ID, display_name="legacy"),
            wake_service=_Svc(available=legacy_available),
            stt_service=_Svc(available=legacy_available),
            tts_service=_Svc(available=legacy_available),
        )
    )
    registry.register(
        ProviderBundle(
            profile=SpeechProviderProfile(provider_id=SPEAKKIT_PROVIDER_ID, display_name="speakkit"),
            wake_service=_Svc(available=speakkit_available),
            stt_service=_Svc(available=speakkit_available),
            tts_service=_Svc(available=speakkit_available),
        )
    )
    return registry


def test_speakkit_can_fallback_to_legacy() -> None:
    decision = resolve_runtime_failure(
        active_provider=SPEAKKIT_PROVIDER_ID,
        recoverable=True,
        stage="speaking",
        registry=_registry(legacy_available=True, speakkit_available=False),
    )
    assert decision.fallback_applied is True
    assert decision.fallback_provider == LEGACY_PROVIDER_ID
    assert decision.reason_code == SPEAKKIT_FALLBACK_REASON


def test_legacy_does_not_autoswitch_to_speakkit() -> None:
    decision = resolve_runtime_failure(
        active_provider=LEGACY_PROVIDER_ID,
        recoverable=True,
        stage="listening",
        registry=_registry(legacy_available=True, speakkit_available=True),
    )
    assert decision.fallback_applied is False
    assert decision.fallback_provider is None
    assert decision.reason_code == LEGACY_NO_AUTOSWITCH_REASON


def test_dual_unavailable_requires_offline() -> None:
    decision = resolve_runtime_failure(
        active_provider=SPEAKKIT_PROVIDER_ID,
        recoverable=True,
        stage="startup",
        registry=_registry(legacy_available=False, speakkit_available=False),
    )
    assert decision.next_state == "offline"
    assert decision.manual_restart_required is True
    assert decision.reason_code == DUAL_PROVIDER_UNAVAILABLE_REASON
