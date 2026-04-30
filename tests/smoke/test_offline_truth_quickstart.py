"""Smoke checks for Phase 8 offline truth quickstart scenarios."""

from __future__ import annotations

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.speech.interfaces import LEGACY_PROVIDER_ID, SPEAKKIT_PROVIDER_ID, SpeechProviderProfile
from core.speech.provider_registry import ProviderBundle, ProviderRegistry
from core.speech.provider_resolver import NetworkProbeResult
from core.wake_word import WakeAction, WakeResult


class _Svc:
    def __init__(self, *, any_responses=None, command_responses=None, wake_responses=None, available=True) -> None:
        self._any_responses = list(any_responses or [])
        self._command_responses = list(command_responses or [])
        self._wake_responses = list(wake_responses or [])
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def detect(self, _text):
        if not self._wake_responses:
            return None
        return self._wake_responses.pop(0)

    def set_language(self, _language):
        return None

    def set_voice_gender(self, _gender):
        return None

    def set_speech_speed(self, _speed):
        return None

    def set_voice_profile(self, _voice):
        return None

    def listen_any(self, _languages, prompt="", timeout=0, phrase_time_limit=0):
        if not self._any_responses:
            return None
        return self._any_responses.pop(0)

    def listen_command(self):
        if not self._command_responses:
            return None
        return self._command_responses.pop(0)

    def configure(self, **_kwargs):
        return None

    def speak(self, _text):
        return None


class _Probe:
    def __init__(self, statuses: list[str]) -> None:
        self._statuses = list(statuses)
        self._index = 0

    def probe(self, *, source: str = "background") -> NetworkProbeResult:
        status = self._statuses[min(self._index, len(self._statuses) - 1)]
        self._index += 1
        return NetworkProbeResult(
            source=source,
            target_label="smoke_probe",
            status=status,
            latency_ms=5,
            checked_at=float(self._index),
            failure_reason=None if status == "online" else "smoke_status",
        )


def _registry(*, command_responses: list[str | None]) -> ProviderRegistry:
    registry = ProviderRegistry()
    legacy = ProviderBundle(
        profile=SpeechProviderProfile(provider_id=LEGACY_PROVIDER_ID, display_name="legacy", requires_network=True),
        wake_service=_Svc(),
        stt_service=_Svc(),
        tts_service=_Svc(),
    )
    speakkit = ProviderBundle(
        profile=SpeechProviderProfile(provider_id=SPEAKKIT_PROVIDER_ID, display_name="speakkit", requires_network=True),
        wake_service=_Svc(wake_responses=[WakeResult(action=WakeAction.START, phrase="hi egb")]),
        stt_service=_Svc(any_responses=["hi egb"], command_responses=command_responses),
        tts_service=_Svc(),
    )
    registry.register(legacy)
    registry.register(speakkit)
    return registry


def test_offline_startup_is_never_reported_ready_for_network_required_provider(
    isolated_settings_manager,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "speech_provider": LEGACY_PROVIDER_ID,
            "language": "en-US",
        },
        persist=False,
    )
    events = []
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(command_responses=[None]),
        dispatcher=dispatch_spy_factory(),
        network_probe=_Probe(["offline", "offline"]),
    )
    runtime.run_forever(max_cycles=1)

    readiness = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("startup_status")
    ]
    assert readiness
    payload = readiness[-1]
    assert payload["startup_status"] in {"degraded", "offline"}
    assert payload["requires_network"] is True
    assert payload["effective_network_available"] is False


def test_offline_truth_safe_refusal_and_allowlisted_fallback_smoke(
    isolated_settings_manager,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "speech_provider": SPEAKKIT_PROVIDER_ID,
            "language": "en-US",
            "offline_allowlisted_capabilities": ["system_status"],
        },
        persist=False,
    )

    safe_refusal_events = []
    safe_dispatch = dispatch_spy_factory(responses=["should not run"])
    safe_runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=safe_refusal_events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(command_responses=["start ocr", None]),
        dispatcher=safe_dispatch,
        network_probe=_Probe(["offline", "offline", "offline"]),
    )
    safe_runtime.run_forever(max_cycles=4)
    assert safe_dispatch.calls == []
    assert any(
        event.type == RuntimeEventType.SYSTEM and event.payload.get("decision") == "safe_refusal"
        for event in safe_refusal_events
    )

    fallback_events = []
    fallback_dispatch = dispatch_spy_factory(responses=["local fallback"])
    fallback_runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=fallback_events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(command_responses=["get status", None]),
        dispatcher=fallback_dispatch,
        network_probe=_Probe(["offline", "offline", "offline"]),
    )
    fallback_runtime.run_forever(max_cycles=4)
    assert fallback_dispatch.calls == ["get status"]
    assert any(
        event.type == RuntimeEventType.SYSTEM and event.payload.get("decision") == "on_device_fallback"
        for event in fallback_events
    )


def test_stale_override_does_not_survive_restart_smoke(
    isolated_settings_manager,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "speech_provider": SPEAKKIT_PROVIDER_ID,
            "network_override_mode": "force_online",
        },
        persist=False,
    )
    events = []
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(command_responses=[None]),
        dispatcher=dispatch_spy_factory(),
        network_probe=_Probe(["offline", "offline"]),
    )
    runtime.run_forever(max_cycles=1)

    config_payloads = [event.payload for event in events if event.type == RuntimeEventType.CONFIG]
    assert config_payloads
    assert config_payloads[-1]["override_mode"] == "auto"
    assert config_payloads[-1]["startup_reset_applied"] is True
