"""Unit coverage for provider startup and fallback resolver logic."""

from __future__ import annotations

from core.speech.interfaces import (
    LEGACY_PROVIDER_ID,
    SPEAKKIT_PROVIDER_ID,
    WAKE_MODE_HARDWARE_TRIGGER,
    WAKE_MODE_KEYWORD_LOW_POWER,
    WAKE_MODE_STT_BASED,
    SpeechProviderProfile,
)
from core.speech.provider_registry import ProviderBundle, ProviderRegistry
from core.speech.provider_resolver import (
    LEGACY_NO_AUTOSWITCH_REASON,
    NETWORK_REQUIRED_PROVIDER_OFFLINE_REASON,
    PROVIDER_UNAVAILABLE_REASON,
    SPEAKKIT_FALLBACK_REASON,
    build_connectivity_state,
    evaluate_offline_execution_policy,
    resolve_wake_mode,
    resolve_runtime_failure,
    resolve_startup_provider,
)


class _Service:
    def __init__(self, *, available: bool = True) -> None:
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


def _bundle(provider_id: str, *, available: bool, requires_network: bool = True) -> ProviderBundle:
    return ProviderBundle(
        profile=SpeechProviderProfile(
            provider_id=provider_id,
            display_name=provider_id,
            requires_network=requires_network,
        ),
        wake_service=_Service(available=available),
        stt_service=_Service(available=available),
        tts_service=_Service(available=available),
    )


def _registry(*, legacy_available: bool, speakkit_available: bool) -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(_bundle(LEGACY_PROVIDER_ID, available=legacy_available, requires_network=False))
    registry.register(_bundle(SPEAKKIT_PROVIDER_ID, available=speakkit_available, requires_network=True))
    return registry


def test_startup_uses_persisted_provider_when_available() -> None:
    startup = resolve_startup_provider(
        persisted_provider=SPEAKKIT_PROVIDER_ID,
        registry=_registry(legacy_available=True, speakkit_available=True),
    )
    assert startup.session_provider == SPEAKKIT_PROVIDER_ID
    assert startup.degraded_mode is False
    assert startup.offline_required is False


def test_startup_degrades_to_legacy_when_speakkit_unavailable() -> None:
    startup = resolve_startup_provider(
        persisted_provider=SPEAKKIT_PROVIDER_ID,
        registry=_registry(legacy_available=True, speakkit_available=False),
    )
    assert startup.session_provider == LEGACY_PROVIDER_ID
    assert startup.degraded_mode is True
    assert startup.persisted_provider_unchanged is True
    assert startup.offline_required is False


def test_startup_requires_offline_when_no_provider_available() -> None:
    startup = resolve_startup_provider(
        persisted_provider=SPEAKKIT_PROVIDER_ID,
        registry=_registry(legacy_available=False, speakkit_available=False),
    )
    assert startup.degraded_mode is True
    assert startup.offline_required is True


def test_startup_degrades_when_connectivity_offline_for_network_provider() -> None:
    startup = resolve_startup_provider(
        persisted_provider=SPEAKKIT_PROVIDER_ID,
        registry=_registry(legacy_available=True, speakkit_available=True),
        connectivity_state=build_connectivity_state(
            override_mode="auto",
            detected_status="offline",
            last_confirmed_status="offline",
            now_s=0.0,
        ),
    )
    assert startup.degraded_mode is True
    assert startup.degraded_reason == NETWORK_REQUIRED_PROVIDER_OFFLINE_REASON
    assert startup.offline_required is False


def test_recoverable_speakkit_failure_falls_back_to_legacy() -> None:
    decision = resolve_runtime_failure(
        active_provider=SPEAKKIT_PROVIDER_ID,
        recoverable=True,
        stage="listening",
        registry=_registry(legacy_available=True, speakkit_available=True),
    )
    assert decision.fallback_applied is True
    assert decision.fallback_provider == LEGACY_PROVIDER_ID
    assert decision.next_state == "standby"
    assert decision.reason_code == SPEAKKIT_FALLBACK_REASON


def test_recoverable_legacy_failure_does_not_autoswitch_to_speakkit() -> None:
    decision = resolve_runtime_failure(
        active_provider=LEGACY_PROVIDER_ID,
        recoverable=True,
        stage="listening",
        registry=_registry(legacy_available=True, speakkit_available=True),
    )
    assert decision.fallback_applied is False
    assert decision.fallback_provider is None
    assert decision.next_state == "standby"
    assert decision.reason_code == LEGACY_NO_AUTOSWITCH_REASON


def test_offline_policy_safe_refuses_when_capability_not_allowlisted() -> None:
    decision = evaluate_offline_execution_policy(
        capability_id="ocr",
        provider_id=SPEAKKIT_PROVIDER_ID,
        requires_network=True,
        network_available=False,
        offline_allowlist={"system_status"},
    )
    assert decision.decision == "safe_refusal"
    assert decision.error_code == "offline_not_allowlisted"
    assert decision.override_mode == "auto"
    assert decision.detected_status == "online"


def test_offline_policy_allows_on_device_fallback_when_allowlisted() -> None:
    decision = evaluate_offline_execution_policy(
        capability_id="system_status",
        provider_id=SPEAKKIT_PROVIDER_ID,
        requires_network=True,
        network_available=False,
        offline_allowlist={"system_status"},
    )
    assert decision.decision == "on_device_fallback"
    assert decision.error_code == "offline_allowlisted_fallback"
    assert decision.spoken_surface_id == "runtime.offline.safe_refusal"


def test_offline_policy_blocks_when_provider_is_unavailable() -> None:
    decision = evaluate_offline_execution_policy(
        capability_id="system_status",
        provider_id=LEGACY_PROVIDER_ID,
        requires_network=False,
        effective_network_available=True,
        provider_availability="unavailable",
        offline_allowlist={"system_status"},
    )
    assert decision.decision == "provider_degraded"
    assert decision.error_code == PROVIDER_UNAVAILABLE_REASON


def test_offline_policy_includes_override_and_detected_state() -> None:
    decision = evaluate_offline_execution_policy(
        capability_id="ocr",
        provider_id=SPEAKKIT_PROVIDER_ID,
        requires_network=True,
        effective_network_available=False,
        override_mode="force_offline",
        detected_status="uncertain",
        provider_availability="ready",
        offline_allowlist={"system_status"},
    )
    assert decision.decision == "safe_refusal"
    assert decision.override_mode == "force_offline"
    assert decision.detected_status == "uncertain"


def test_wake_mode_prefers_configured_keyword_path_when_available() -> None:
    selection = resolve_wake_mode(
        wake_primary_mode=WAKE_MODE_KEYWORD_LOW_POWER,
        wake_fallback_mode=WAKE_MODE_HARDWARE_TRIGGER,
        wake_dev_fallback_mode=WAKE_MODE_STT_BASED,
        stt_wake_allowed_in_production=False,
        runtime_environment="production_like",
        keyword_wake_available=True,
        hardware_trigger_available=True,
        stt_wake_available=True,
        provider_availability="ready",
        effective_network_available=True,
    )
    assert selection.selected_mode == WAKE_MODE_KEYWORD_LOW_POWER
    assert selection.selection_source == "configured"
    assert selection.degraded_mode is False


def test_wake_mode_degrades_when_only_stt_exists_but_production_disallows_it() -> None:
    selection = resolve_wake_mode(
        wake_primary_mode=WAKE_MODE_STT_BASED,
        wake_fallback_mode=WAKE_MODE_HARDWARE_TRIGGER,
        wake_dev_fallback_mode=WAKE_MODE_STT_BASED,
        stt_wake_allowed_in_production=False,
        runtime_environment="production_like",
        keyword_wake_available=False,
        hardware_trigger_available=False,
        stt_wake_available=True,
        provider_availability="ready",
        effective_network_available=True,
    )
    assert selection.degraded_mode is True
    assert selection.degraded_reason == "no_permitted_wake_source"
    assert selection.selection_source == "degraded"


def test_wake_mode_preserves_local_wake_when_network_weak() -> None:
    selection = resolve_wake_mode(
        wake_primary_mode=WAKE_MODE_KEYWORD_LOW_POWER,
        wake_fallback_mode=WAKE_MODE_HARDWARE_TRIGGER,
        wake_dev_fallback_mode=WAKE_MODE_STT_BASED,
        stt_wake_allowed_in_production=False,
        runtime_environment="production_like",
        keyword_wake_available=True,
        hardware_trigger_available=True,
        stt_wake_available=True,
        provider_availability="degraded",
        effective_network_available=False,
    )
    assert selection.selected_mode == WAKE_MODE_KEYWORD_LOW_POWER
    assert selection.degraded_mode is False


def test_wake_mode_uses_dev_fallback_when_enabled() -> None:
    selection = resolve_wake_mode(
        wake_primary_mode=WAKE_MODE_HARDWARE_TRIGGER,
        wake_fallback_mode=WAKE_MODE_HARDWARE_TRIGGER,
        wake_dev_fallback_mode=WAKE_MODE_STT_BASED,
        stt_wake_allowed_in_production=True,
        runtime_environment="production_like",
        keyword_wake_available=False,
        hardware_trigger_available=False,
        stt_wake_available=True,
        provider_availability="ready",
        effective_network_available=True,
    )
    assert selection.selected_mode == WAKE_MODE_STT_BASED
    assert selection.selection_source == "dev_fallback"
