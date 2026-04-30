"""Unit coverage for wearable interrupt preemption and bounded sessions."""

from __future__ import annotations

import pytest

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.wake_word import WakeAction, WakeResult


def _run_runtime(
    *,
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
    any_responses,
    command_responses,
    dispatch_responses=None,
    max_cycles: int = 4,
):
    events = []
    listener = listener_factory(any_responses=any_responses, command_responses=command_responses)
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    dispatch = dispatch_spy_factory(responses=dispatch_responses or [])
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
    return events, dispatch


@pytest.mark.parametrize("interrupt_text", ["stop", "cancel", "emergency"])
def test_interrupt_preempts_active_listening_without_dispatch(
    interrupt_text,
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US"},
        persist=False,
    )
    events, dispatch = _run_runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
        any_responses=["hi egb"],
        command_responses=[interrupt_text, None],
        dispatch_responses=["should not be used"],
    )

    assert dispatch.calls == []
    outcomes = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("recovery_trigger") == "interrupt"
    ]
    assert outcomes
    assert outcomes[-1]["interrupt_signal_type"] == interrupt_text
    assert outcomes[-1]["completion_status"] == "interrupted"
    assert outcomes[-1]["event_category"] == "interrupt"
    assert outcomes[-1]["latency_ms"] >= 0
    assert "raw_utterance" not in outcomes[-1]["payload"]["interrupt_detection"]
    assert "normalized_utterance" not in outcomes[-1]["payload"]["interrupt_detection"]


def test_interrupted_noncritical_speech_is_not_auto_resumed(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US"},
        persist=False,
    )
    events, dispatch = _run_runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
        any_responses=["hi egb"],
        command_responses=["check status", "stop", None],
        dispatch_responses=["informational status update"],
        max_cycles=5,
    )

    assert dispatch.calls == ["check status"]
    assistant_texts = [event.payload["text"] for event in events if event.type == RuntimeEventType.ASSISTANT]
    assert "informational status update" in assistant_texts
    stop_index = next(index for index, text in enumerate(assistant_texts) if "stop" in text.lower())
    assert "informational status update" not in assistant_texts[stop_index + 1 :]


def test_listening_timeout_emits_machine_readable_recovery_outcome(
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
            "max_listen_seconds": 0.1,
        },
        persist=False,
    )
    events, _dispatch = _run_runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
        any_responses=["hi egb"],
        command_responses=[None, None],
    )
    timeout_events = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("recovery_trigger") == "timeout"
    ]
    assert timeout_events
    assert timeout_events[-1]["error_code"] == "listen_timeout"
    assert timeout_events[-1]["completion_status"] == "timeout"
