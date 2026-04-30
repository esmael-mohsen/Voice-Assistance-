"""Integration tests for startup degradation and provider-failure safety paths."""

from __future__ import annotations

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.speech.interfaces import LEGACY_PROVIDER_ID, SPEAKKIT_PROVIDER_ID, SpeechProviderProfile
from core.speech.provider_registry import ProviderBundle, ProviderRegistry
from core.speech.provider_resolver import NetworkProbeResult
from core.wake_word import WakeAction, WakeResult


class _Wake:
    def __init__(self, responses=None, *, available=True) -> None:
        self.responses = list(responses or [])
        self.available = available

    def is_available(self) -> bool:
        return self.available

    def detect(self, _text):
        if not self.responses:
            return None
        return self.responses.pop(0)


class _Stt:
    def __init__(self, *, any_responses=None, command_responses=None, available=True) -> None:
        self.any_responses = list(any_responses or [])
        self.command_responses = list(command_responses or [])
        self.available = available

    def is_available(self) -> bool:
        return self.available

    def set_language(self, _language):
        return None

    def listen_any(self, _languages, prompt="", timeout=0, phrase_time_limit=0):
        if not self.any_responses:
            return None
        value = self.any_responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def listen_command(self):
        if not self.command_responses:
            return None
        value = self.command_responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class _Tts:
    def __init__(self, *, available=True) -> None:
        self.available = available

    def is_available(self) -> bool:
        return self.available

    def configure(self, **_kwargs):
        return None

    def set_language(self, _language):
        return None

    def set_voice_gender(self, _gender):
        return None

    def set_speech_speed(self, _speed):
        return None

    def set_voice_profile(self, _voice):
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
            target_label="failure_probe",
            status=status,
            latency_ms=5,
            checked_at=float(self._index),
            failure_reason=None if status == "online" else "failure_status",
        )


def _bundle(provider_id: str, *, wake, stt, tts) -> ProviderBundle:
    return ProviderBundle(
        profile=SpeechProviderProfile(provider_id=provider_id, display_name=provider_id, requires_network=True),
        wake_service=wake,
        stt_service=stt,
        tts_service=tts,
    )


def _registry(
    *,
    legacy_available: bool,
    speakkit_available: bool,
    speakkit_runtime_failure: bool = False,
) -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(
        _bundle(
            LEGACY_PROVIDER_ID,
            wake=_Wake(available=legacy_available),
            stt=_Stt(available=legacy_available),
            tts=_Tts(available=legacy_available),
        )
    )
    if speakkit_runtime_failure:
        speakkit_stt = _Stt(
            any_responses=["hi egb"],
            command_responses=[RuntimeError("speakkit runtime failure"), None],
            available=True,
        )
        speakkit_wake = _Wake(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")], available=True)
        speakkit_tts = _Tts(available=True)
    else:
        speakkit_stt = _Stt(available=speakkit_available)
        speakkit_wake = _Wake(available=speakkit_available)
        speakkit_tts = _Tts(available=speakkit_available)

    registry.register(
        _bundle(
            SPEAKKIT_PROVIDER_ID,
            wake=speakkit_wake,
            stt=speakkit_stt,
            tts=speakkit_tts,
        )
    )
    return registry


def test_startup_degrades_to_legacy_when_persisted_speakkit_unavailable(isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "speech_provider": SPEAKKIT_PROVIDER_ID},
        persist=False,
    )
    events = []
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(legacy_available=True, speakkit_available=False),
        network_probe=_Probe(["online", "online"]),
    )
    runtime.run_forever(max_cycles=1)

    config_events = [event for event in events if event.type == RuntimeEventType.CONFIG]
    assert config_events
    payload = config_events[-1].payload
    assert payload["speech_provider"] == LEGACY_PROVIDER_ID
    assert payload["persisted_speech_provider"] == SPEAKKIT_PROVIDER_ID
    assert payload["degraded_mode"] is True
    assert payload["degraded_reason"] == "provider_unavailable_at_startup"
    assert payload["event_category"] == "provider_selection"
    assert payload["provider_context"]["provider_id"] == LEGACY_PROVIDER_ID
    assert isolated_settings_manager.speech_provider == SPEAKKIT_PROVIDER_ID


def test_dual_provider_unavailable_transitions_runtime_offline(isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "speech_provider": SPEAKKIT_PROVIDER_ID},
        persist=False,
    )
    events = []
    runtime = AssistantRuntime(
        mode=RuntimeMode.GUI,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(legacy_available=False, speakkit_available=False),
        network_probe=_Probe(["online", "online"]),
    )
    runtime.run_forever(max_cycles=1)

    status_states = [event.payload["state"] for event in events if event.type == RuntimeEventType.STATUS]
    errors = [event.payload for event in events if event.type == RuntimeEventType.ERROR]
    assert status_states == ["offline"]
    assert errors
    assert errors[-1]["reason_code"] == "dual_provider_unavailable"
    assert errors[-1]["manual_restart_required"] is True


def test_speakkit_runtime_failure_falls_back_to_legacy(isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US", "speech_provider": SPEAKKIT_PROVIDER_ID},
        persist=False,
    )
    events = []
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(
            legacy_available=True,
            speakkit_available=True,
            speakkit_runtime_failure=True,
        ),
        network_probe=_Probe(["online", "online", "online"]),
    )
    runtime.run_forever(max_cycles=3)

    error_events = [event.payload for event in events if event.type == RuntimeEventType.ERROR]
    system_events = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("event_category") == "provider_selection"
    ]
    config_events = [event.payload for event in events if event.type == RuntimeEventType.CONFIG]
    assert error_events
    assert system_events
    assert system_events[-1]["provider_context"]["provider_id"] == SPEAKKIT_PROVIDER_ID
    assert error_events[-1]["provider"] == SPEAKKIT_PROVIDER_ID
    assert error_events[-1]["fallback_applied"] is True
    assert error_events[-1]["fallback_to"] == LEGACY_PROVIDER_ID
    assert error_events[-1]["next_state"] == "standby"
    assert config_events[-1]["speech_provider"] == LEGACY_PROVIDER_ID
