"""Integration tests for GUI/console shared runtime parity."""

import pytest

from core.assistant_runtime import (
    AssistantRuntime,
    RuntimeEventType,
    RuntimeMode,
    RuntimeSession,
    RuntimeState,
    status_event,
)
from core.wake_word import WakeAction, WakeResult


@pytest.mark.parametrize("mode", [RuntimeMode.GUI, RuntimeMode.CONSOLE])
def test_runtime_mode_bootstrap_emits_standby_status(mode: RuntimeMode) -> None:
    session = RuntimeSession(mode=mode)
    session.transition_to(RuntimeState.STANDBY)
    event = status_event(session, RuntimeState.STANDBY)

    assert session.mode == mode
    assert event.payload["state"] == "standby"


def test_gui_and_console_share_transition_contract() -> None:
    gui_session = RuntimeSession(mode=RuntimeMode.GUI)
    console_session = RuntimeSession(mode=RuntimeMode.CONSOLE)

    for next_state in (RuntimeState.STANDBY, RuntimeState.OFFLINE):
        assert gui_session.can_transition_to(next_state) == console_session.can_transition_to(next_state)


def _run_scripted_mode(
    mode: RuntimeMode,
    *,
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
    configured: bool,
    any_responses: list[str | None],
    command_responses: list[str | None],
    dispatch_responses: list[object] | None = None,
    max_cycles: int = 3,
):
    isolated_settings_manager.username = "Tester" if configured else ""
    isolated_settings_manager.language = "en-US"
    isolated_settings_manager.voice_gender = "female"
    isolated_settings_manager.speech_speed = 1.0

    events = []
    listener = listener_factory(any_responses=any_responses, command_responses=command_responses)
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    dispatch = dispatch_spy_factory(responses=dispatch_responses or [])

    runtime = AssistantRuntime(
        mode=mode,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )
    runtime.run_forever(max_cycles=max_cycles)
    return events


def test_gui_console_configured_user_parity(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    gui_events = _run_scripted_mode(
        RuntimeMode.GUI,
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
        configured=True,
        any_responses=["hi egb"],
        command_responses=["check status", None],
        dispatch_responses=["All good"],
        max_cycles=3,
    )

    isolated_settings_manager.username = "Tester"
    isolated_settings_manager.language = "en-US"
    isolated_settings_manager.voice_gender = "female"
    isolated_settings_manager.speech_speed = 1.0

    console_events = _run_scripted_mode(
        RuntimeMode.CONSOLE,
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
        configured=True,
        any_responses=["hi egb"],
        command_responses=["check status", None],
        dispatch_responses=["All good"],
        max_cycles=3,
    )

    gui_states = [event.payload["state"] for event in gui_events if event.type == RuntimeEventType.STATUS]
    console_states = [event.payload["state"] for event in console_events if event.type == RuntimeEventType.STATUS]

    assert gui_states == console_states


def test_gui_console_first_run_onboarding_parity(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    onboarding_inputs = ["hi egb", "english", "female", "1.1", "Mina", "yes"]
    gui_events = _run_scripted_mode(
        RuntimeMode.GUI,
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
        configured=False,
        any_responses=list(onboarding_inputs),
        command_responses=[None],
        max_cycles=2,
    )

    isolated_settings_manager.username = ""
    isolated_settings_manager.language = "en-US"
    isolated_settings_manager.voice_gender = "female"
    isolated_settings_manager.speech_speed = 1.0

    console_events = _run_scripted_mode(
        RuntimeMode.CONSOLE,
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
        configured=False,
        any_responses=list(onboarding_inputs),
        command_responses=[None],
        max_cycles=2,
    )

    gui_states = [event.payload["state"] for event in gui_events if event.type == RuntimeEventType.STATUS]
    console_states = [event.payload["state"] for event in console_events if event.type == RuntimeEventType.STATUS]
    assert "setup" in gui_states
    assert "setup" in console_states
    assert gui_states == console_states


def test_mode_status_vocabulary_remains_canonical(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    events = _run_scripted_mode(
        RuntimeMode.GUI,
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
        configured=True,
        any_responses=["hi egb"],
        command_responses=["check status", None],
        dispatch_responses=["All good"],
        max_cycles=3,
    )
    states = [event.payload["state"] for event in events if event.type == RuntimeEventType.STATUS]
    canonical_states = {"standby", "wake", "setup", "listening", "thinking", "speaking", "error", "offline"}
    assert set(states).issubset(canonical_states)


def test_mode_config_payload_keeps_legacy_keys_with_provider_extensions(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    events = _run_scripted_mode(
        RuntimeMode.CONSOLE,
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
        configured=True,
        any_responses=["hi egb"],
        command_responses=["check status", None],
        dispatch_responses=["All good"],
        max_cycles=3,
    )
    config_payloads = [event.payload for event in events if event.type == RuntimeEventType.CONFIG]
    assert config_payloads
    payload = config_payloads[-1]
    assert {"language", "gender", "speed"}.issubset(payload.keys())
    assert "speech_provider" in payload


def test_mode_config_payload_exposes_command_confidence_policy(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "command_confidence_high_threshold": 0.9,
            "command_confidence_medium_threshold": 0.7,
            "command_protected_threshold": 0.95,
        },
        persist=False,
    )
    events = _run_scripted_mode(
        RuntimeMode.CONSOLE,
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
        configured=True,
        any_responses=["hi egb"],
        command_responses=["check status", None],
        dispatch_responses=["All good"],
        max_cycles=3,
    )
    config_payloads = [event.payload for event in events if event.type == RuntimeEventType.CONFIG]
    assert config_payloads
    payload = config_payloads[-1]
    assert payload["command_confidence_high_threshold"] == pytest.approx(0.9)
    assert payload["command_confidence_medium_threshold"] == pytest.approx(0.7)
    assert payload["command_protected_threshold"] == pytest.approx(0.95)


def test_mode_config_payload_exposes_capture_profile_and_qualification_fields(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "command_capture_profile_id": "command.default",
            "confirmation_capture_profile_id": "confirmation.default",
            "speech_qualification_profile": "simplified",
            "enable_capture_relisten": True,
        },
        persist=False,
    )
    events = _run_scripted_mode(
        RuntimeMode.CONSOLE,
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
        configured=True,
        any_responses=["hi egb"],
        command_responses=["check status", None],
        dispatch_responses=["All good"],
        max_cycles=3,
    )
    config_payloads = [event.payload for event in events if event.type == RuntimeEventType.CONFIG]
    assert config_payloads
    payload = config_payloads[-1]
    assert payload["command_capture_profile_id"] == "command.default"
    assert payload["confirmation_capture_profile_id"] == "confirmation.default"
    assert payload["speech_qualification_profile"] == "simplified"


@pytest.mark.parametrize("mode", [RuntimeMode.GUI, RuntimeMode.CONSOLE])
def test_disabled_cloud_rollout_preserves_keyword_and_hardware_wake_parity(
    mode: RuntimeMode,
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
            "wake_dev_fallback_mode": "stt_based_wake",
            "stt_wake_allowed_in_production": False,
        },
        persist=False,
    )
    events = []
    runtime = AssistantRuntime(
        mode=mode,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener_factory(default_language=default_language, command_responses=[None]),
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")]),
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
    assert accepted[-1]["source_classification"] in {"keyword_low_power", "hardware_trigger"}


@pytest.mark.parametrize("mode", [RuntimeMode.GUI, RuntimeMode.CONSOLE])
def test_runtime_modes_share_confirmation_phrase_policy(
    mode: RuntimeMode,
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = AssistantRuntime(
        mode=mode,
        observer=lambda _event: None,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener_factory(default_language=default_language),
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text: None,
    )

    assert runtime._is_yes("yes please") is True
    assert runtime._is_yes("ايوه") is True
    assert runtime._is_yes("yes cancel") is False
    assert runtime._is_yes("not sure") is False
