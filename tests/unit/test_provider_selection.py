"""Unit tests for provider selection and restart-only switching."""

from __future__ import annotations

from core.assistant_runtime import AssistantRuntime, RuntimeMode
from core.runtime_diagnostics import attach_runtime_diagnostic_fields
from core.speech.interfaces import LEGACY_PROVIDER_ID, SPEAKKIT_PROVIDER_ID, SpeechProviderProfile
from core.speech.provider_registry import ProviderBundle, ProviderRegistry
from core.speech.provider_resolver import resolve_provider_switch_request


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


def _provider_bundle(provider_id: str) -> ProviderBundle:
    return ProviderBundle(
        profile=SpeechProviderProfile(provider_id=provider_id, display_name=provider_id),
        wake_service=_Service(available=True),
        stt_service=_Service(available=True),
        tts_service=_Service(available=True),
    )


def _registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(_provider_bundle(LEGACY_PROVIDER_ID))
    registry.register(_provider_bundle(SPEAKKIT_PROVIDER_ID))
    return registry


def test_switch_request_is_deferred_when_runtime_active() -> None:
    decision = resolve_provider_switch_request(
        active_provider=LEGACY_PROVIDER_ID,
        requested_provider=SPEAKKIT_PROVIDER_ID,
        runtime_active=True,
    )
    assert decision.applied_provider == LEGACY_PROVIDER_ID
    assert decision.pending_provider == SPEAKKIT_PROVIDER_ID
    assert decision.deferred_until_restart is True


def test_switch_request_applies_when_runtime_inactive() -> None:
    decision = resolve_provider_switch_request(
        active_provider=LEGACY_PROVIDER_ID,
        requested_provider=SPEAKKIT_PROVIDER_ID,
        runtime_active=False,
    )
    assert decision.applied_provider == SPEAKKIT_PROVIDER_ID
    assert decision.pending_provider is None
    assert decision.deferred_until_restart is False


def test_runtime_applies_pending_provider_at_startup(
    isolated_settings_manager,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "speech_provider": LEGACY_PROVIDER_ID,
            "pending_speech_provider": SPEAKKIT_PROVIDER_ID,
            "deferred_provider_switch": True,
        },
        persist=False,
    )
    events = []

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(),
    )
    runtime.run_forever(max_cycles=1)

    config_events = [event for event in events if event.type.value == "config"]
    assert config_events
    assert config_events[-1].payload["speech_provider"] == SPEAKKIT_PROVIDER_ID
    assert config_events[-1].payload["event_category"] == "provider_selection"
    assert config_events[-1].payload["provider_context"]["provider_id"] == SPEAKKIT_PROVIDER_ID
    assert config_events[-1].payload["field_safe"] is True
    assert isolated_settings_manager.speech_provider == SPEAKKIT_PROVIDER_ID
    assert isolated_settings_manager.pending_speech_provider is None


def test_provider_selection_diagnostic_payload_includes_canonical_metadata() -> None:
    payload = attach_runtime_diagnostic_fields(
        {"speech_provider": SPEAKKIT_PROVIDER_ID},
        session_or_run_id="session-provider",
        event_category="provider_selection",
        status_or_decision="selected",
        reason_code=None,
        provider_id=SPEAKKIT_PROVIDER_ID,
        provider_availability="ready",
        degraded_mode=False,
        degraded_reason=None,
        next_state="standby",
    )

    assert payload["event_category"] == "provider_selection"
    assert payload["status_or_decision"] == "selected"
    assert payload["provider_context"]["provider_availability"] == "ready"
    assert payload["field_safe"] is True
