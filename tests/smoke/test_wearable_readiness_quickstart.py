"""Smoke validation for wearable readiness quickstart paths."""

from __future__ import annotations

import pytest

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.speech.interfaces import LEGACY_PROVIDER_ID, SPEAKKIT_PROVIDER_ID, SpeechProviderProfile
from core.speech.provider_registry import ProviderBundle, ProviderRegistry
from core.speech.provider_resolver import NetworkProbeResult
from core.wake_word import WakeAction, WakeResult


class _Svc:
    def __init__(self, *, any_responses=None, command_responses=None, wake_responses=None, available=True) -> None:
        self._any = list(any_responses or [])
        self._cmd = list(command_responses or [])
        self._wake = list(wake_responses or [])
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def detect(self, _text):
        if not self._wake:
            return None
        return self._wake.pop(0)

    def listen_any(self, _languages, prompt="", timeout=0, phrase_time_limit=0):
        if not self._any:
            return None
        return self._any.pop(0)

    def listen_command(self):
        if not self._cmd:
            return None
        return self._cmd.pop(0)

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
            target_label="wearable_probe",
            status=status,
            latency_ms=5,
            checked_at=float(self._index),
            failure_reason=None if status == "online" else "wearable_status",
        )


def _provider_registry(*, command_responses: list[str | None]) -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(
        ProviderBundle(
            profile=SpeechProviderProfile(provider_id=LEGACY_PROVIDER_ID, display_name="legacy", requires_network=True),
            wake_service=_Svc(),
            stt_service=_Svc(),
            tts_service=_Svc(),
        )
    )
    registry.register(
        ProviderBundle(
            profile=SpeechProviderProfile(provider_id=SPEAKKIT_PROVIDER_ID, display_name="speakkit", requires_network=True),
            wake_service=_Svc(wake_responses=[WakeResult(action=WakeAction.START, phrase="hi egb")]),
            stt_service=_Svc(any_responses=["hi egb"], command_responses=command_responses),
            tts_service=_Svc(),
        )
    )
    return registry


SMOKE_SCENARIOS = [
    {"name": "interrupt_preemption", "command": "stop"},
    {"name": "offline_safe_refusal", "command": "start ocr"},
]


def test_wearable_smoke_matrix_shape() -> None:
    assert [scenario["name"] for scenario in SMOKE_SCENARIOS] == [
        "interrupt_preemption",
        "offline_safe_refusal",
    ]


@pytest.mark.parametrize("scenario", SMOKE_SCENARIOS, ids=[item["name"] for item in SMOKE_SCENARIOS])
def test_wearable_smoke_runtime_scenarios(scenario, isolated_settings_manager, dispatch_spy_factory) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "speech_provider": SPEAKKIT_PROVIDER_ID,
            "network_available": scenario["name"] != "offline_safe_refusal",
            "offline_allowlisted_capabilities": ["system_status"],
        },
        persist=False,
    )
    events = []
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_provider_registry(command_responses=[scenario["command"], None]),
        dispatcher=dispatch_spy_factory(responses=["ok"]),
        network_probe=_Probe(
            ["offline", "offline", "offline"] if scenario["name"] == "offline_safe_refusal" else ["online", "online"]
        ),
    )
    runtime.run_forever(max_cycles=4)

    if scenario["name"] == "interrupt_preemption":
        assert any(
            event.type == RuntimeEventType.SYSTEM and event.payload.get("recovery_trigger") == "interrupt"
            for event in events
        )
    if scenario["name"] == "offline_safe_refusal":
        assert any(
            event.type == RuntimeEventType.SYSTEM and event.payload.get("offline_policy_decision") == "safe_refusal"
            for event in events
        )
