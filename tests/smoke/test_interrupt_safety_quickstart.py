"""Smoke validation for Phase 10 interrupt safety quickstart paths."""

from __future__ import annotations

import threading
import time

import pytest

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.command_models import CommandExecutionResult
from core.wake_word import WakeAction, WakeResult


def _build_runtime(
    *,
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatcher,
    command_responses,
    speech_delay_s: float = 0.0,
    degrade_on_interrupt: bool = False,
):
    events = []
    listener = listener_factory(any_responses=["hi egb"], command_responses=command_responses)
    tts = tts_engine_factory(speech_delay_s=speech_delay_s, degrade_on_interrupt=degrade_on_interrupt)
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatcher,
    )
    return runtime, events


@pytest.mark.parametrize("interrupt_text", ["stop", "\u0642\u0641"])
def test_phase10_quickstart_interrupt_paths(
    interrupt_text,
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot({"username": "Tester", "language": "en-US"}, persist=False)
    runtime, events = _build_runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatcher=lambda _text, runtime_context=None: CommandExecutionResult(  # noqa: ARG005
            status="success",
            spoken_text="Long speaking response",
            intent_id="get_system_status",
        ),
        command_responses=[interrupt_text, None],
    )
    runtime.run_forever(max_cycles=4)

    assert any(
        event.type == RuntimeEventType.SYSTEM and event.payload.get("recovery_trigger") == "interrupt"
        for event in events
    )


def test_phase10_quickstart_weak_network_best_effort_interrupt(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot({"username": "Tester", "language": "en-US"}, persist=False)
    release = threading.Event()

    def _dispatcher(_text, runtime_context=None):
        release.wait(timeout=0.2)
        return CommandExecutionResult(
            status="success",
            spoken_text="Network-backed work finished",
            intent_id="recognize_face",
            payload={"capability_id": "face_recognition"},
        )

    runtime, events = _build_runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatcher=_dispatcher,
        command_responses=["recognize face", None],
        speech_delay_s=0.2,
        degrade_on_interrupt=True,
    )
    runtime._initialize_runtime()

    worker = threading.Thread(target=runtime._handle_active_input, args=("recognize face",), daemon=True)
    worker.start()
    started_at = time.perf_counter()
    while runtime._active_operation_context is None and (time.perf_counter() - started_at) < 0.2:
        time.sleep(0.01)
    runtime._handle_interrupt_signal("cancel")
    release.set()
    worker.join(timeout=1.0)

    outcomes = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("recovery_trigger") == "interrupt"
    ]
    assert outcomes
    assert outcomes[-1]["degraded_mode"] is True
