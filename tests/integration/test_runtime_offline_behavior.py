"""Integration tests for offline and degraded runtime decision behavior."""

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
            target_label="integration_probe",
            status=status,
            latency_ms=5,
            checked_at=float(self._index),
            failure_reason=None if status == "online" else "integration_status",
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


def test_offline_non_allowlisted_command_safe_refuses_without_dispatch(
    isolated_settings_manager,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "speech_provider": SPEAKKIT_PROVIDER_ID,
            "network_available": False,
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
    policy_events = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and (
            event.payload.get("offline_policy_decision") == "safe_refusal"
            or event.payload.get("decision") == "safe_refusal"
        )
    ]
    assert policy_events
    assert policy_events[-1]["error_code"] == "offline_not_allowlisted"


def test_offline_allowlisted_command_uses_fallback_and_dispatches(
    isolated_settings_manager,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "speech_provider": SPEAKKIT_PROVIDER_ID,
            "network_available": False,
            "offline_allowlisted_capabilities": ["system_status"],
        },
        persist=False,
    )
    events = []
    dispatch = dispatch_spy_factory(responses=["safe local status"])
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
    policy_events = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM
        and (
            event.payload.get("offline_policy_decision") == "on_device_fallback"
            or event.payload.get("decision") == "on_device_fallback"
        )
    ]
    assert policy_events
    assert policy_events[-1]["capability_id"] == "system_status"


def test_offline_policy_snapshot_exposes_local_only_command_flag(isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "command_offline_local_allowed": True,
            "command_fallback_enabled": True,
            "command_rescue_enabled": True,
            "speech_qualification_profile": "default",
        },
        persist=False,
    )
    snapshot = isolated_settings_manager.get_settings_snapshot()
    assert snapshot["command_offline_local_allowed"] is True
    assert snapshot["command_fallback_enabled"] is True
    assert snapshot["command_rescue_enabled"] is True
    assert snapshot["speech_qualification_profile"] == "default"
