"""Integration tests for startup readiness and standby wake behavior."""

from __future__ import annotations

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.speech.provider_resolver import NetworkProbeResult
from core.wake_word import WakeAction, WakeResult


class _Probe:
    def __init__(self, statuses: list[str]) -> None:
        self._statuses = list(statuses)
        self._index = 0

    def probe(self, *, source: str = "background") -> NetworkProbeResult:
        status = self._statuses[min(self._index, len(self._statuses) - 1)]
        self._index += 1
        return NetworkProbeResult(
            source=source,
            target_label="wearable_startup_probe",
            status=status,
            latency_ms=5,
            checked_at=float(self._index),
            failure_reason=None if status == "online" else "wearable_startup_status",
        )


def test_startup_emits_non_visual_readiness_snapshot(
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
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener_factory(default_language=default_language, any_responses=[None]),
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=dispatch_spy_factory(),
        network_probe=_Probe(["online", "online"]),
    )
    runtime.run_forever(max_cycles=1)

    readiness_events = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("startup_status")
    ]
    assert readiness_events
    payload = readiness_events[-1]
    assert payload["startup_status"] in {"ready", "degraded", "offline"}
    if payload["startup_status"] == "ready":
        assert payload["startup_latency_ms"] <= 8000


def test_standby_remains_wake_responsive_after_ready_signal(
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
    listener = listener_factory(any_responses=["hi egb"], command_responses=[None])
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(
            responses=[WakeResult(action=WakeAction.START, phrase="hi egb")]
        ),
        dispatcher=dispatch_spy_factory(),
        network_probe=_Probe(["online", "online", "online"]),
    )
    runtime.run_forever(max_cycles=3)

    states = [event.payload["state"] for event in events if event.type == RuntimeEventType.STATUS]
    assert "standby" in states
    assert "wake" in states
    assert "listening" in states


def test_ready_state_emits_non_speech_cue_when_enabled(
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
            "non_speech_cues_enabled": True,
        },
        persist=False,
    )
    events = []
    runtime = AssistantRuntime(
        mode=RuntimeMode.GUI,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener_factory(default_language=default_language),
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=dispatch_spy_factory(),
        network_probe=_Probe(["online", "online"]),
    )
    runtime.run_forever(max_cycles=1)

    cue_events = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("cue_id")
    ]
    assert cue_events
    assert cue_events[-1]["cue_id"] == "tone_ready"
