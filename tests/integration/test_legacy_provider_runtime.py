"""Integration parity checks for legacy provider runtime paths."""

from __future__ import annotations

import pytest

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.wake_word import WakeAction, WakeResult


@pytest.mark.parametrize("mode", [RuntimeMode.GUI, RuntimeMode.CONSOLE])
def test_legacy_provider_mode_preserves_baseline_flow(
    mode,
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US", "speech_provider": "legacy"},
        persist=False,
    )
    events = []
    listener = listener_factory(any_responses=["hi egb"], command_responses=["status", None])
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    tts = tts_engine_factory()
    dispatch = dispatch_spy_factory(responses=["All good"])

    runtime = AssistantRuntime(
        mode=mode,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )
    runtime.run_forever(max_cycles=3)

    states = [event.payload["state"] for event in events if event.type == RuntimeEventType.STATUS]
    config_payloads = [event.payload for event in events if event.type == RuntimeEventType.CONFIG]
    assert "wake" in states
    assert "thinking" in states
    assert "speaking" in states
    assert config_payloads
    assert config_payloads[-1]["speech_provider"] == "legacy"
