"""Integration tests for GUI observer runtime bridge behavior."""

from __future__ import annotations

from dataclasses import dataclass
from queue import Queue
from typing import Any, Callable

from core.assistant_runtime import RuntimeEvent, RuntimeEventType, RuntimeMode
from ui.assistant_worker import AssistantWorker, UiEvent


@dataclass
class SequenceRuntime:
    mode: RuntimeMode
    observer: Callable[[RuntimeEvent], None]
    default_language: str | None = None
    running: bool = False
    stop_requested: bool = False

    def start_in_background(self) -> None:
        self.running = True
        self._emit(RuntimeEventType.STATUS, {"state": "standby"})
        self._emit(
            RuntimeEventType.SYSTEM,
            {
                "wake_mode": "keyword_low_power",
                "wake_fallback_mode": "hardware_trigger",
                "selection_source": "configured",
            },
        )
        self._emit(RuntimeEventType.CONFIG, {"language": "en-US", "gender": "female", "speed": 1.0})
        self._emit(RuntimeEventType.STATUS, {"state": "wake"})
        self._emit(RuntimeEventType.STATUS, {"state": "listening"})
        self._emit(RuntimeEventType.USER, {"text": "check status"})
        self._emit(RuntimeEventType.STATUS, {"state": "thinking"})
        self._emit(RuntimeEventType.ASSISTANT, {"text": "All good"})
        self._emit(RuntimeEventType.STATUS, {"state": "speaking"})

    def request_stop(self) -> None:
        self.stop_requested = True
        self.running = False
        self._emit(RuntimeEventType.STATUS, {"state": "stopping"})
        self._emit(RuntimeEventType.STATUS, {"state": "offline"})

    def shutdown(self, join_timeout_s: float = 2.0) -> None:  # noqa: ARG002
        self.running = False

    def _emit(self, event_type: RuntimeEventType, payload: dict[str, Any]) -> None:
        self.observer(
            RuntimeEvent(
                type=event_type,
                session_id="session-gui",
                payload=payload,
                timestamp="2026-01-01T00:00:00+00:00",
            )
        )


def _runtime_factory_sink(container: list[SequenceRuntime]):
    def _factory(*, mode, observer, default_language=None):
        runtime = SequenceRuntime(mode=mode, observer=observer, default_language=default_language)
        container.append(runtime)
        return runtime

    return _factory


def _drain_queue(queue: Queue[UiEvent]) -> list[UiEvent]:
    events: list[UiEvent] = []
    while not queue.empty():
        events.append(queue.get_nowait())
    return events


def test_gui_bridge_forwards_lifecycle_and_message_sequence() -> None:
    queue: Queue[UiEvent] = Queue()
    runtimes: list[SequenceRuntime] = []
    worker = AssistantWorker(event_queue=queue, runtime_factory=_runtime_factory_sink(runtimes))

    worker.start()
    ui_events = _drain_queue(queue)

    event_types = [event.type for event in ui_events]
    states = [event.payload["state"] for event in ui_events if event.type == "status"]

    assert runtimes[-1].mode == RuntimeMode.GUI
    assert event_types[:3] == ["status", "system", "config"]
    assert states[:4] == ["standby", "wake", "listening", "thinking"]
    assert any(event.type == "assistant" and event.payload["text"] == "All good" for event in ui_events)


def test_gui_bridge_preserves_error_payload_for_ui_handling() -> None:
    queue: Queue[UiEvent] = Queue()
    runtimes: list[SequenceRuntime] = []
    worker = AssistantWorker(event_queue=queue, runtime_factory=_runtime_factory_sink(runtimes))

    worker.start()
    runtimes[-1]._emit(
        RuntimeEventType.ERROR,
        {"message": "temporary failure", "recoverable": True, "next_state": "standby"},
    )

    ui_events = _drain_queue(queue)
    error_events = [event for event in ui_events if event.type == "error"]
    assert error_events
    error_payload = error_events[-1].payload
    assert error_payload["message"] == "temporary failure"
    assert error_payload["recoverable"] is True
    assert error_payload["next_state"] == "standby"


def test_gui_bridge_preserves_wearable_runtime_observability_payloads() -> None:
    queue: Queue[UiEvent] = Queue()
    runtimes: list[SequenceRuntime] = []
    worker = AssistantWorker(event_queue=queue, runtime_factory=_runtime_factory_sink(runtimes))

    worker.start()
    runtimes[-1]._emit(
        RuntimeEventType.SYSTEM,
        {
            "startup_status": "ready",
            "startup_latency_ms": 1200,
            "cue_id": "tone_ready",
            "offline_policy_decision": "safe_refusal",
            "requires_network": True,
        },
    )

    ui_events = _drain_queue(queue)
    system_events = [event for event in ui_events if event.type == "system"]
    assert system_events
    payload = system_events[-1].payload
    assert payload["startup_status"] == "ready"
    assert payload["cue_id"] == "tone_ready"
    assert payload["offline_policy_decision"] == "safe_refusal"


def test_gui_bridge_preserves_canonical_runtime_diagnostic_fields() -> None:
    queue: Queue[UiEvent] = Queue()
    runtimes: list[SequenceRuntime] = []
    worker = AssistantWorker(event_queue=queue, runtime_factory=_runtime_factory_sink(runtimes))

    worker.start()
    runtimes[-1]._emit(
        RuntimeEventType.SYSTEM,
        {
            "event_category": "offline_policy",
            "status_or_decision": "safe_refusal",
            "reason_code": "offline_not_allowlisted",
            "provider_context": {
                "provider_id": "speakkit",
                "provider_availability": "ready",
                "degraded_mode": False,
                "degraded_reason": None,
            },
            "field_safe": True,
        },
    )

    ui_events = _drain_queue(queue)
    system_events = [event.payload for event in ui_events if event.type == "system"]
    assert system_events
    payload = system_events[-1]
    assert payload["event_category"] == "offline_policy"
    assert payload["provider_context"]["provider_id"] == "speakkit"
    assert payload["field_safe"] is True


def test_gui_bridge_preserves_wake_policy_observability_payload() -> None:
    queue: Queue[UiEvent] = Queue()
    runtimes: list[SequenceRuntime] = []
    worker = AssistantWorker(event_queue=queue, runtime_factory=_runtime_factory_sink(runtimes))

    worker.start()
    ui_events = _drain_queue(queue)
    wake_policy_events = [
        event.payload
        for event in ui_events
        if event.type == "system" and event.payload.get("wake_mode")
    ]
    assert wake_policy_events
    payload = wake_policy_events[-1]
    assert payload["wake_mode"] == "keyword_low_power"
    assert payload["wake_fallback_mode"] == "hardware_trigger"
    assert payload["selection_source"] == "configured"


def test_gui_bridge_preserves_command_recognition_telemetry_payload() -> None:
    queue: Queue[UiEvent] = Queue()
    runtimes: list[SequenceRuntime] = []
    worker = AssistantWorker(event_queue=queue, runtime_factory=_runtime_factory_sink(runtimes))

    worker.start()
    runtimes[-1]._emit(
        RuntimeEventType.SYSTEM,
        {
            "command_recognition_telemetry": {
                "session_id": "session-gui",
                "event_id": "recognition-1",
                "recognition_path": "fallback",
                "confidence_band": "medium",
                "fallback_used": True,
                "decision_outcome": "retry",
                "protected_command": False,
                "latency_ms": 1800,
                "field_safe": True,
                "raw_utterance_present": False,
            }
        },
    )

    ui_events = _drain_queue(queue)
    system_events = [event.payload for event in ui_events if event.type == "system"]
    assert system_events
    telemetry = system_events[-1]["command_recognition_telemetry"]
    assert telemetry["field_safe"] is True
    assert telemetry["raw_utterance_present"] is False


def test_gui_bridge_preserves_phase14_capture_metadata_payload() -> None:
    queue: Queue[UiEvent] = Queue()
    runtimes: list[SequenceRuntime] = []
    worker = AssistantWorker(event_queue=queue, runtime_factory=_runtime_factory_sink(runtimes))

    worker.start()
    runtimes[-1]._emit(
        RuntimeEventType.SYSTEM,
        {
            "recognition_metadata": {
                "capture_attempt_id": "cap-42",
                "profile_id": "command.default",
                "endpoint_quality_hints": ["low_trailing_silence"],
                "closed_vocabulary_id": None,
                "dictionary_bias_applied": True,
            }
        },
    )

    ui_events = _drain_queue(queue)
    system_events = [event.payload for event in ui_events if event.type == "system"]
    assert system_events
    recognition = system_events[-1]["recognition_metadata"]
    assert recognition["capture_attempt_id"] == "cap-42"
    assert recognition["profile_id"] == "command.default"
    assert recognition["dictionary_bias_applied"] is True
