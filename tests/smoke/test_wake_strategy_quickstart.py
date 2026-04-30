"""Smoke scenarios for Phase 11 wake strategy quickstart coverage."""

from __future__ import annotations

import pytest

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.command_models import CommandRecognitionResult
from core.speech.interfaces import LEGACY_PROVIDER_ID, SpeechProviderProfile
from core.speech.provider_registry import ProviderBundle, ProviderRegistry
from core.wake_word import WakeAction, WakeResult


class _Svc:
    def __init__(
        self,
        *,
        wake_responses=None,
        any_responses=None,
        command_responses=None,
        command_result_responses=None,
        available=True,
    ) -> None:
        self._wake = list(wake_responses or [])
        self._any = list(any_responses or [])
        self._cmd = list(command_responses or [])
        self._cmd_result = list(command_result_responses or [])
        self._available = bool(available)

    def is_available(self) -> bool:
        return self._available

    def detect(self, _text):
        if not self._wake:
            return None
        return self._wake.pop(0)

    def wait_for_wake(self, *, timeout_s=1.0, wake_mode=None):  # noqa: ARG002
        return self.detect("")

    def supports_mode(self, _wake_mode: str) -> bool:
        return True

    def listen_any(self, _languages, prompt="", timeout=0, phrase_time_limit=0):
        if not self._any:
            return None
        return self._any.pop(0)

    def listen_command(self):
        if not self._cmd:
            return None
        return self._cmd.pop(0)

    def listen_command_result(self, **kwargs):
        if self._cmd_result:
            scripted = self._cmd_result.pop(0)
            if scripted is None:
                return None
            if isinstance(scripted, CommandRecognitionResult):
                return scripted
            if isinstance(scripted, dict):
                payload = dict(scripted)
                payload.setdefault("session_id", "smoke-session")
                payload.setdefault("recognition_path", "local_first")
                payload.setdefault("provider_id", "legacy")
                payload.setdefault("primary_transcript", "")
                payload.setdefault("confidence_available", False)
                payload.setdefault("confidence_score", None)
                payload.setdefault("alternative_transcripts", ())
                payload.setdefault("detected_language", "en-US")
                payload.setdefault("selected_language", "en-US")
                payload.setdefault("latency_ms", 0)
                payload.setdefault("error_code", None)
                payload.setdefault("profile_id", str(kwargs.get("capture_profile_id", "standby_wake.default")))
                payload["alternative_transcripts"] = tuple(payload.get("alternative_transcripts", ()))
                return CommandRecognitionResult(**payload)
        return None

    def set_language(self, _language):
        return None

    def set_voice_gender(self, _gender):
        return None

    def set_speech_speed(self, _speed):
        return None

    def set_voice_profile(self, _voice):
        return None

    def configure(self, **_kwargs):
        return None

    def speak(self, _text, **_kwargs):
        return None


def _registry(*, wake: _Svc, stt: _Svc) -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(
        ProviderBundle(
            profile=SpeechProviderProfile(provider_id=LEGACY_PROVIDER_ID, display_name="legacy", requires_network=True),
            wake_service=wake,
            stt_service=stt,
            tts_service=_Svc(),
        )
    )
    return registry


SMOKE_MATRIX = (
    "production_keyword_wake",
    "production_stt_rejected",
    "development_stt_fallback",
    "degraded_no_source",
    "first_valid_wins",
    "cloud_primary_standby_wake",
    "cloud_timeout_to_fallback_miss",
    "repeated_standby_wake_misses",
)


def test_wake_strategy_smoke_matrix_shape() -> None:
    assert SMOKE_MATRIX == (
        "production_keyword_wake",
        "production_stt_rejected",
        "development_stt_fallback",
        "degraded_no_source",
        "first_valid_wins",
        "cloud_primary_standby_wake",
        "cloud_timeout_to_fallback_miss",
        "repeated_standby_wake_misses",
    )


def test_phase15_replay_fixture_matrix_has_required_scenarios(
    phase15_replay_scenarios,
) -> None:
    scenario_ids = {item["scenario_id"] for item in phase15_replay_scenarios}
    assert {
        "quiet_wake",
        "noisy_wake",
        "bilingual_wake",
        "degraded_provider",
        "repeated_fault",
    }.issubset(scenario_ids)


@pytest.mark.parametrize("scenario", SMOKE_MATRIX)
def test_wake_strategy_quickstart_scenarios(scenario: str, isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "wake_primary_mode": "keyword_low_power",
            "wake_fallback_mode": "hardware_trigger",
            "wake_dev_fallback_mode": "stt_based_wake",
            "stt_wake_allowed_in_production": False,
            "network_override_mode": "auto",
        },
        persist=False,
    )

    wake = _Svc(available=True)
    stt = _Svc(available=True, command_responses=[None])
    max_cycles = 2

    if scenario == "production_keyword_wake":
        wake = _Svc(wake_responses=[WakeResult(action=WakeAction.START, phrase="hi egb")], available=True)
        stt = _Svc(any_responses=["hi egb"], command_responses=[None], available=True)
    elif scenario == "production_stt_rejected":
        wake = _Svc(available=False)
        stt = _Svc(any_responses=["hi egb"], command_responses=[None], available=True)
    elif scenario == "development_stt_fallback":
        isolated_settings_manager.apply_settings_snapshot(
            {
                "wake_primary_mode": "hardware_trigger",
                "wake_fallback_mode": "hardware_trigger",
                "stt_wake_allowed_in_production": True,
            },
            persist=False,
        )
        wake = _Svc(available=False)
        stt = _Svc(any_responses=["hi egb"], command_responses=[None], available=True)
    elif scenario == "degraded_no_source":
        wake = _Svc(available=False)
        stt = _Svc(available=False)
        max_cycles = 3
    elif scenario == "first_valid_wins":
        wake = _Svc(
            wake_responses=[
                WakeResult(action=WakeAction.START, phrase="hi egb"),
                WakeResult(action=WakeAction.START, phrase="hi egb"),
            ],
            available=True,
        )
        stt = _Svc(command_responses=[None], available=True)
    elif scenario == "cloud_primary_standby_wake":
        isolated_settings_manager.apply_settings_snapshot(
            {
                "wake_primary_mode": "stt_based_wake",
                "wake_fallback_mode": "hardware_trigger",
                "stt_wake_allowed_in_production": True,
            },
            persist=False,
        )
        wake = _Svc(available=False)
        stt = _Svc(
            command_responses=[None],
            command_result_responses=[
                {
                    "primary_transcript": "hi egb open navigation",
                    "alternative_transcripts": ("hi egb open navigation", "hi egb"),
                    "recognition_source": "cloud_primary",
                    "failure_reason_code": None,
                    "error_code": None,
                }
            ],
            available=True,
        )
    elif scenario == "cloud_timeout_to_fallback_miss":
        isolated_settings_manager.apply_settings_snapshot(
            {
                "wake_primary_mode": "stt_based_wake",
                "wake_fallback_mode": "hardware_trigger",
                "stt_wake_allowed_in_production": True,
            },
            persist=False,
        )
        wake = _Svc(available=False)
        stt = _Svc(
            command_result_responses=[
                {
                    "primary_transcript": "",
                    "recognition_source": "wake_strict_vosk_fallback",
                    "failure_reason_code": "cloud_network_timeout",
                    "error_code": "strict_grammar_no_match",
                }
            ],
            available=True,
        )
        max_cycles = 1
    elif scenario == "repeated_standby_wake_misses":
        isolated_settings_manager.apply_settings_snapshot(
            {
                "wake_primary_mode": "stt_based_wake",
                "wake_fallback_mode": "hardware_trigger",
                "stt_wake_allowed_in_production": True,
            },
            persist=False,
        )
        wake = _Svc(available=False)
        stt = _Svc(
            command_result_responses=[
                {
                    "primary_transcript": "",
                    "recognition_source": "wake_strict_vosk_fallback",
                    "failure_reason_code": "strict_grammar_no_match",
                    "error_code": "strict_grammar_no_match",
                }
                for _ in range(50)
            ],
            available=True,
        )
        max_cycles = 50

    events = []
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(wake=wake, stt=stt),
        dispatcher=lambda _text: None,
    )
    runtime.run_forever(max_cycles=max_cycles)

    accepted = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "wake_accepted"
    ]
    rejected = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "wake_rejected"
    ]
    degraded = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "degraded_standby"
    ]
    missed = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "wake_missed"
    ]

    if scenario == "production_keyword_wake":
        assert accepted
        assert accepted[-1]["selected_wake_mode"] == "keyword_low_power"
    elif scenario == "production_stt_rejected":
        assert not accepted
        assert degraded
    elif scenario == "development_stt_fallback":
        assert accepted
        assert accepted[-1]["selected_wake_mode"] == "stt_based_wake"
    elif scenario == "degraded_no_source":
        assert not accepted
        assert len(degraded) == 1
    elif scenario == "first_valid_wins":
        assert len(accepted) == 1
        assert not rejected
    elif scenario == "cloud_primary_standby_wake":
        assert accepted
        assert accepted[-1]["selected_wake_mode"] == "stt_based_wake"
        assert accepted[-1]["source_classification"] == "cloud_primary"
        assert accepted[-1]["command_suffix_ignored"] is True
    elif scenario == "cloud_timeout_to_fallback_miss":
        assert not accepted
        assert missed
        assert missed[-1]["source_classification"] == "wake_strict_vosk_fallback"
    elif scenario == "repeated_standby_wake_misses":
        assert len(missed) == 50
        assert all(payload.get("next_state") == "standby" for payload in missed)
        assert missed[-1]["payload"]["wake_miss_streak"] >= 50
