"""Integration tests for runtime interruption latency and timeout recovery."""

from __future__ import annotations

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.wake_word import WakeAction, WakeResult


def _run_interrupt_flow(
    *,
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
    command_responses,
    max_cycles: int = 4,
):
    events = []
    listener = listener_factory(any_responses=["hi egb"], command_responses=command_responses)
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    dispatch = dispatch_spy_factory(responses=["normal command response"])
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )
    runtime.run_forever(max_cycles=max_cycles)
    return events


def test_interrupt_preemption_latency_is_reported_under_one_second(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot({"username": "Tester", "language": "en-US"}, persist=False)
    events = _run_interrupt_flow(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
        command_responses=["stop", None],
    )

    outcomes = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("recovery_trigger") == "interrupt"
    ]
    assert outcomes
    assert outcomes[-1]["preemption_latency_ms"] <= 1000
    assert outcomes[-1]["next_state"] == "standby"
    assert outcomes[-1]["event_category"] == "interrupt"
    assert "raw_utterance" not in outcomes[-1]["payload"]["interrupt_detection"]


def test_timeout_recovery_returns_runtime_to_standby(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US", "max_listen_seconds": 0.1},
        persist=False,
    )
    events = _run_interrupt_flow(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
        command_responses=[None, None],
    )
    outcomes = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("recovery_trigger") == "timeout"
    ]
    assert outcomes
    assert outcomes[-1]["completion_status"] == "timeout"
    assert outcomes[-1]["next_state"] == "standby"
