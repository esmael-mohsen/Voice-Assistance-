"""Integration coverage for Phase 11 wake strategy behavior."""

from __future__ import annotations

from core.command_models import CommandRecognitionResult
from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.speech.interfaces import LEGACY_PROVIDER_ID, SpeechProviderProfile
from core.speech.provider_registry import ProviderBundle, ProviderRegistry
from core.wake_word import WakeAction, WakeResult, WakeWordDetector


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
        self.listen_any_calls = 0

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
        self.listen_any_calls += 1
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
                payload.setdefault("session_id", "svc-session")
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


def _registry(*, wake_service: _Svc, stt_service: _Svc, tts_service: _Svc | None = None) -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(
        ProviderBundle(
            profile=SpeechProviderProfile(provider_id=LEGACY_PROVIDER_ID, display_name="legacy", requires_network=True),
            wake_service=wake_service,
            stt_service=stt_service,
            tts_service=tts_service or _Svc(),
        )
    )
    return registry


def test_keyword_wake_path_matches_between_console_and_gui(isolated_settings_manager) -> None:
    for mode in (RuntimeMode.CONSOLE, RuntimeMode.GUI):
        events = []
        isolated_settings_manager.apply_settings_snapshot(
            {
                "username": "Tester",
                "language": "en-US",
                "wake_primary_mode": "keyword_low_power",
                "wake_fallback_mode": "hardware_trigger",
                "stt_wake_allowed_in_production": False,
            },
            persist=False,
        )
        wake = _Svc(wake_responses=[WakeResult(action=WakeAction.START, phrase="hi egb")], available=True)
        stt = _Svc(any_responses=["hi egb"], command_responses=[None], available=True)
        runtime = AssistantRuntime(
            mode=mode,
            observer=events.append,
            settings_manager_obj=isolated_settings_manager,
            provider_registry_obj=_registry(wake_service=wake, stt_service=stt),
            dispatcher=lambda _text: None,
        )
        runtime.run_forever(max_cycles=2)

        assert stt.listen_any_calls == 0
        wake_outcomes = [
            event.payload
            for event in events
            if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "wake_accepted"
        ]
        assert wake_outcomes
        assert wake_outcomes[-1]["selected_wake_mode"] == "keyword_low_power"


def test_dev_fallback_stt_wake_is_available_only_when_enabled(isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "wake_primary_mode": "hardware_trigger",
            "wake_fallback_mode": "hardware_trigger",
            "wake_dev_fallback_mode": "stt_based_wake",
            "stt_wake_allowed_in_production": True,
        },
        persist=False,
    )
    events = []
    wake = _Svc(available=False)
    stt = _Svc(any_responses=["hi egb"], command_responses=[None], available=True)
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(wake_service=wake, stt_service=stt),
        dispatcher=lambda _text: None,
    )
    runtime.run_forever(max_cycles=2)
    accepted = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "wake_accepted"
    ]
    assert accepted
    assert accepted[-1]["selected_wake_mode"] == "stt_based_wake"


def test_weak_network_keeps_local_wake_operational(isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "network_override_mode": "force_offline",
            "wake_primary_mode": "keyword_low_power",
            "wake_fallback_mode": "hardware_trigger",
            "stt_wake_allowed_in_production": False,
        },
        persist=False,
    )
    events = []
    wake = _Svc(wake_responses=[WakeResult(action=WakeAction.START, phrase="hi egb")], available=True)
    stt = _Svc(any_responses=["hi egb"], command_responses=[None], available=True)
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(wake_service=wake, stt_service=stt),
        dispatcher=lambda _text: None,
    )
    runtime.run_forever(max_cycles=2)

    degraded = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "degraded_standby"
    ]
    accepted = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "wake_accepted"
    ]
    assert not degraded
    assert accepted


def test_unavailable_wake_sources_enter_safe_degraded_standby(isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "wake_primary_mode": "keyword_low_power",
            "wake_fallback_mode": "hardware_trigger",
            "stt_wake_allowed_in_production": False,
        },
        persist=False,
    )
    events = []
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(
            wake_service=_Svc(available=False),
            stt_service=_Svc(available=False),
        ),
        dispatcher=lambda _text: None,
    )
    runtime.run_forever(max_cycles=3)

    degraded = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "degraded_standby"
    ]
    assert len(degraded) == 1


def test_default_legacy_provider_keyword_wake_runs_end_to_end(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    dispatch_spy_factory,
) -> None:
    events = []
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "wake_primary_mode": "keyword_low_power",
            "wake_fallback_mode": "hardware_trigger",
            "stt_wake_allowed_in_production": False,
        },
        persist=False,
    )

    listener = listener_factory(any_responses=["هاي اي جي بي"], command_responses=[None])
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: WakeWordDetector(),
        dispatcher=dispatch_spy_factory(),
    )
    runtime.run_forever(max_cycles=2)

    accepted = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "wake_accepted"
    ]
    assert accepted
    assert accepted[-1]["selected_wake_mode"] == "keyword_low_power"
    assert len(listener.listen_any_calls) >= 1


def test_default_legacy_provider_accepts_english_stt_wake_variants(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    dispatch_spy_factory,
) -> None:
    events = []
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "wake_primary_mode": "keyword_low_power",
            "wake_fallback_mode": "hardware_trigger",
            "stt_wake_allowed_in_production": False,
        },
        persist=False,
    )

    listener = listener_factory(any_responses=["hi hgb"], command_responses=[None])
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: WakeWordDetector(),
        dispatcher=dispatch_spy_factory(),
    )
    runtime.run_forever(max_cycles=2)

    accepted = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "wake_accepted"
    ]
    assert accepted
    assert accepted[-1]["selected_wake_mode"] == "keyword_low_power"
    assert len(listener.listen_any_calls) >= 1


def test_stt_based_wake_accepts_cloud_primary_with_structured_metadata(isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "wake_primary_mode": "stt_based_wake",
            "wake_fallback_mode": "hardware_trigger",
            "wake_dev_fallback_mode": "stt_based_wake",
            "stt_wake_allowed_in_production": True,
        },
        persist=False,
    )
    events = []
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(
            wake_service=_Svc(available=False),
            stt_service=_Svc(
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
            ),
        ),
        dispatcher=lambda _text: None,
    )
    runtime.run_forever(max_cycles=2)

    accepted = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "wake_accepted"
    ]
    assert accepted
    payload = accepted[-1]
    assert payload["selected_wake_mode"] == "stt_based_wake"
    assert payload["source_classification"] == "cloud_primary"
    assert payload["canonical_wake_alias"] == "hi egb"
    assert payload["command_suffix_ignored"] is True


def test_stt_based_wake_cloud_timeout_then_strict_no_match_emits_wake_missed(isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "wake_primary_mode": "stt_based_wake",
            "wake_fallback_mode": "hardware_trigger",
            "wake_dev_fallback_mode": "stt_based_wake",
            "stt_wake_allowed_in_production": True,
        },
        persist=False,
    )
    events = []
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(
            wake_service=_Svc(available=False),
            stt_service=_Svc(
                command_result_responses=[
                    {
                        "primary_transcript": "",
                        "recognition_source": "wake_strict_vosk_fallback",
                        "failure_reason_code": "cloud_network_timeout",
                        "error_code": "strict_grammar_no_match",
                    }
                ],
                available=True,
            ),
        ),
        dispatcher=lambda _text: None,
    )
    runtime.run_forever(max_cycles=1)

    missed = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "wake_missed"
    ]
    assert missed
    payload = missed[-1]
    assert payload["source_classification"] == "wake_strict_vosk_fallback"
    assert payload["payload"]["fallback_used"] is True
    assert payload["next_state"] == "standby"


def test_stt_based_wake_noncanonical_candidate_is_rejected_without_transition(isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "wake_primary_mode": "stt_based_wake",
            "wake_fallback_mode": "hardware_trigger",
            "wake_dev_fallback_mode": "stt_based_wake",
            "stt_wake_allowed_in_production": True,
        },
        persist=False,
    )
    events = []
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(
            wake_service=_Svc(available=False),
            stt_service=_Svc(
                command_result_responses=[
                    {
                        "primary_transcript": "open navigation now",
                        "alternative_transcripts": ("open navigation now",),
                        "recognition_source": "cloud_primary",
                        "failure_reason_code": None,
                        "error_code": None,
                    }
                ],
                available=True,
            ),
        ),
        dispatcher=lambda _text: None,
    )
    runtime.run_forever(max_cycles=1)

    rejected = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "wake_rejected"
    ]
    assert rejected
    payload = rejected[-1]
    assert payload["source_classification"] == "noncanonical_rejected"
    assert payload["error_code"] == "wake_phrase_not_approved"


def test_stt_based_wake_repeated_misses_return_to_standby_without_crash(isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "wake_primary_mode": "stt_based_wake",
            "wake_fallback_mode": "hardware_trigger",
            "wake_dev_fallback_mode": "stt_based_wake",
            "stt_wake_allowed_in_production": True,
        },
        persist=False,
    )
    events = []
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(
            wake_service=_Svc(available=False),
            stt_service=_Svc(
                command_result_responses=[
                    {
                        "primary_transcript": "",
                        "recognition_source": "wake_strict_vosk_fallback",
                        "failure_reason_code": "strict_grammar_no_match",
                        "error_code": "strict_grammar_no_match",
                    }
                    for _ in range(10)
                ],
                available=True,
            ),
        ),
        dispatcher=lambda _text: None,
    )
    runtime.run_forever(max_cycles=10)

    missed = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "wake_missed"
    ]
    assert len(missed) == 10
    assert all(item["next_state"] == "standby" for item in missed)
