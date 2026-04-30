"""Integration matrix tests for runtime offline policy and connectivity truth."""

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
            target_label="test_probe",
            status=status,
            latency_ms=5,
            checked_at=float(self._index),
            failure_reason=None if status == "online" else "test_status",
        )


def _registry(*, command_responses: list[str | None], provider_available: bool = True) -> ProviderRegistry:
    registry = ProviderRegistry()
    legacy = ProviderBundle(
        profile=SpeechProviderProfile(provider_id=LEGACY_PROVIDER_ID, display_name="legacy", requires_network=True),
        wake_service=_Svc(available=provider_available),
        stt_service=_Svc(available=provider_available),
        tts_service=_Svc(available=provider_available),
    )
    speakkit = ProviderBundle(
        profile=SpeechProviderProfile(provider_id=SPEAKKIT_PROVIDER_ID, display_name="speakkit", requires_network=True),
        wake_service=_Svc(
            wake_responses=[WakeResult(action=WakeAction.START, phrase="hi egb")],
            available=provider_available,
        ),
        stt_service=_Svc(any_responses=["hi egb"], command_responses=command_responses, available=provider_available),
        tts_service=_Svc(available=provider_available),
    )
    registry.register(legacy)
    registry.register(speakkit)
    return registry


def test_startup_resets_manual_override_to_auto(isolated_settings_manager, dispatch_spy_factory) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "speech_provider": SPEAKKIT_PROVIDER_ID,
            "network_override_mode": "force_offline",
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
        network_probe=_Probe(["online", "online"]),
    )
    runtime.run_forever(max_cycles=1)

    config_payloads = [event.payload for event in events if event.type == RuntimeEventType.CONFIG]
    assert config_payloads
    assert config_payloads[-1]["override_mode"] == "auto"
    assert config_payloads[-1]["startup_reset_applied"] is True


def test_runtime_safe_refusal_policy_event_contains_connectivity_truth(
    isolated_settings_manager,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "speech_provider": SPEAKKIT_PROVIDER_ID,
            "offline_allowlisted_capabilities": ["system_status"],
        },
        persist=False,
    )
    events = []
    dispatch = dispatch_spy_factory(responses=["should not run"])
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(command_responses=["start ocr", None]),
        dispatcher=dispatch,
        network_probe=_Probe(["offline", "offline", "offline"]),
    )
    runtime.run_forever(max_cycles=4)

    assert dispatch.calls == []
    policy_payloads = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("decision") == "safe_refusal"
    ]
    assert policy_payloads
    payload = policy_payloads[-1]
    assert payload["provider_id"] == SPEAKKIT_PROVIDER_ID
    assert payload["override_mode"] == "auto"
    assert payload["detected_status"] == "offline"
    assert payload["provider_availability"] == "ready"
    assert payload["event_category"] == "offline_policy"
    assert payload["provider_context"]["provider_id"] == SPEAKKIT_PROVIDER_ID
    assert payload["field_safe"] is True


def test_runtime_allowlisted_offline_fallback_matrix_case(
    isolated_settings_manager,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "speech_provider": SPEAKKIT_PROVIDER_ID,
            "offline_allowlisted_capabilities": ["system_status"],
        },
        persist=False,
    )
    events = []
    dispatch = dispatch_spy_factory(responses=["local fallback status"])
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(command_responses=["get status", None]),
        dispatcher=dispatch,
        network_probe=_Probe(["offline", "offline", "offline"]),
    )
    runtime.run_forever(max_cycles=4)

    assert dispatch.calls == ["get status"]
    policy_payloads = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("decision") == "on_device_fallback"
    ]
    assert policy_payloads
    assert policy_payloads[-1]["offline_allowlisted"] is True
    assert policy_payloads[-1]["event_category"] == "offline_policy"


def test_force_online_override_cannot_mask_provider_unavailable_startup(
    isolated_settings_manager,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
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
        provider_registry_obj=_registry(command_responses=[None], provider_available=False),
        dispatcher=dispatch_spy_factory(),
        network_probe=_Probe(["online", "online"]),
    )
    runtime.run_forever(max_cycles=1)

    readiness_payloads = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("startup_status")
    ]
    assert readiness_payloads
    assert readiness_payloads[-1]["startup_status"] == "offline"
    assert readiness_payloads[-1]["provider_availability"] == "unavailable"
    assert readiness_payloads[-1]["override_mode"] == "auto"
