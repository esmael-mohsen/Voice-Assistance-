"""Unit tests for Phase 11 wake strategy runtime behavior."""

from __future__ import annotations

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.speech.interfaces import LEGACY_PROVIDER_ID, SpeechProviderProfile
from core.speech.provider_registry import ProviderBundle, ProviderRegistry
from core.wake_word import WakeAction, WakeResult


def test_keyword_standby_does_not_use_open_stt_listening(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
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
    listener = listener_factory(any_responses=["hi egb"], command_responses=[None])
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=lambda _event: None,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(
            responses=[WakeResult(action=WakeAction.START, phrase="hi egb")]
        ),
        dispatcher=dispatch_spy_factory(),
    )
    runtime.run_forever(max_cycles=2)
    assert listener.listen_any_calls == []


def test_non_canonical_stt_wake_phrase_is_rejected(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    events = []
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "wake_primary_mode": "stt_based_wake",
            "wake_fallback_mode": "hardware_trigger",
            "stt_wake_allowed_in_production": True,
        },
        persist=False,
    )
    listener = listener_factory(any_responses=["hello assistant"], command_responses=[None])
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text: None,
    )
    runtime.run_forever(max_cycles=1)
    wake_rejections = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "wake_rejected"
    ]
    assert wake_rejections
    assert wake_rejections[-1]["error_code"] == "wake_phrase_not_approved"


def test_degraded_standby_guidance_is_announced_once_per_reason(
    isolated_settings_manager,
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

    class _UnavailableService:
        def __init__(self, *, available: bool = False) -> None:
            self._available = available

        def is_available(self) -> bool:
            return self._available

        def detect(self, _text):
            return None

        def listen_any(self, _languages, prompt="", timeout=0, phrase_time_limit=0):
            return None

        def listen_command(self):
            return None

        def set_language(self, _language):
            return None

        def set_voice_gender(self, _gender):
            return None

        def set_speech_speed(self, _speed):
            return None

        def speak(self, _text, **_kwargs):
            return None

        def configure(self, **_kwargs):
            return None

    registry = ProviderRegistry()
    registry.register(
        ProviderBundle(
            profile=SpeechProviderProfile(provider_id=LEGACY_PROVIDER_ID, display_name="legacy"),
            wake_service=_UnavailableService(available=False),
            stt_service=_UnavailableService(available=True),
            tts_service=_UnavailableService(available=True),
        )
    )

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=registry,
        dispatcher=lambda _text: None,
    )
    runtime.run_forever(max_cycles=3)
    degraded_events = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "degraded_standby"
    ]
    assert len(degraded_events) == 1


def test_first_valid_wake_locks_cycle_and_rejects_competing_signal(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    events = []
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US"},
        persist=False,
    )
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener_factory(default_language=default_language),
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text: None,
    )
    runtime._initialize_runtime()
    runtime._wake_selection = runtime._resolve_wake_selection()

    runtime._handle_standby_input("hi egb", attempt_mode="keyword_low_power")
    runtime._handle_standby_input("hi egb", attempt_mode="keyword_low_power")

    wake_rejections = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("error_code") == "wake_cycle_locked"
    ]
    assert wake_rejections
