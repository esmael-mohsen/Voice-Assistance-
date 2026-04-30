"""Integration tests for recoverable and offline runtime failure handling."""

from datetime import datetime

from core.assistant_runtime import (
    AssistantRuntime,
    RuntimeEventType,
    RuntimeMode,
    UnrecoverableRuntimeError,
)
from core.wake_word import WakeAction, WakeResult


def test_recoverable_failure_returns_to_standby_within_five_seconds(
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
    events = []
    listener = listener_factory(any_responses=["hi egb"], command_responses=["run command", None])
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    dispatch = dispatch_spy_factory(responses=[RuntimeError("temporary failure")])

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )
    runtime.run_forever(max_cycles=3)

    error_events = [event for event in events if event.type == RuntimeEventType.ERROR]
    status_events = [event for event in events if event.type == RuntimeEventType.STATUS]
    assert error_events
    assert error_events[-1].payload["recoverable"] is True
    assert error_events[-1].payload["next_state"] == "standby"

    error_time = datetime.fromisoformat(error_events[-1].timestamp)
    standby_after_error = next(
        event
        for event in status_events
        if event.payload.get("state") == "standby" and datetime.fromisoformat(event.timestamp) >= error_time
    )
    standby_time = datetime.fromisoformat(standby_after_error.timestamp)
    assert (standby_time - error_time).total_seconds() <= 5.0


def test_startup_initialization_failure_goes_directly_offline(
    isolated_settings_manager,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    events = []

    def failing_listener_factory(*, default_language):  # noqa: ARG001
        raise RuntimeError("microphone initialization failed")

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=failing_listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatcher=dispatch_spy_factory(),
    )
    runtime.run_forever(max_cycles=1)

    error_events = [event for event in events if event.type == RuntimeEventType.ERROR]
    status_states = [event.payload["state"] for event in events if event.type == RuntimeEventType.STATUS]
    assert error_events
    assert error_events[-1].payload["recoverable"] is False
    assert error_events[-1].payload["next_state"] == "offline"
    assert status_states == ["offline"]


def test_unrecoverable_runtime_exception_transitions_to_offline_without_standby(
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
    events = []
    listener = listener_factory(any_responses=["hi egb"], command_responses=["run command", None])
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    dispatch = dispatch_spy_factory(responses=[UnrecoverableRuntimeError("fatal runtime failure")])

    runtime = AssistantRuntime(
        mode=RuntimeMode.GUI,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )
    runtime.run_forever(max_cycles=3)

    error_events = [event for event in events if event.type == RuntimeEventType.ERROR]
    status_states = [event.payload["state"] for event in events if event.type == RuntimeEventType.STATUS]

    assert error_events
    assert error_events[-1].payload["recoverable"] is False
    assert error_events[-1].payload["next_state"] == "offline"
    assert "error" in status_states
    assert "offline" in status_states

    error_index = status_states.index("error")
    assert "standby" not in status_states[error_index + 1 :]
