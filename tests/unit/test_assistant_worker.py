"""Unit tests for the GUI runtime bridge worker."""

from __future__ import annotations

from dataclasses import dataclass, field
from queue import Queue
from typing import Any, Callable

from core.assistant_runtime import RuntimeEvent, RuntimeEventType, RuntimeMode
from ui.assistant_worker import AssistantWorker, UiEvent


@dataclass
class FakeRuntime:
    mode: RuntimeMode
    observer: Callable[[RuntimeEvent], None]
    default_language: str | None = None
    running: bool = False
    started: bool = False
    stop_requested: bool = False
    shutdown_called: bool = False
    emitted_events: list[RuntimeEvent] = field(default_factory=list)

    def start_in_background(self) -> None:
        self.started = True
        self.running = True

    def request_stop(self) -> None:
        self.stop_requested = True
        self.running = False

    def shutdown(self, join_timeout_s: float = 2.0) -> None:  # noqa: ARG002
        self.shutdown_called = True
        self.running = False

    def emit(self, event_type: RuntimeEventType, payload: dict[str, Any]) -> None:
        event = RuntimeEvent(
            type=event_type,
            session_id="session-1",
            payload=payload,
            timestamp="2026-01-01T00:00:00+00:00",
        )
        self.emitted_events.append(event)
        self.observer(event)


def _runtime_factory_sink(container: list[FakeRuntime]):
    def _factory(*, mode, observer, default_language=None):
        runtime = FakeRuntime(mode=mode, observer=observer, default_language=default_language)
        container.append(runtime)
        return runtime

    return _factory


def test_worker_translates_runtime_event_to_ui_event() -> None:
    queue: Queue[UiEvent] = Queue()
    runtimes: list[FakeRuntime] = []
    worker = AssistantWorker(event_queue=queue, runtime_factory=_runtime_factory_sink(runtimes))

    worker.start()
    runtime = runtimes[-1]
    runtime.emit(RuntimeEventType.STATUS, {"state": "standby"})

    ui_event = queue.get_nowait()
    assert ui_event.type == "status"
    assert ui_event.payload["state"] == "standby"
    assert ui_event.payload["session_id"] == "session-1"
    assert ui_event.payload["timestamp"] == "2026-01-01T00:00:00+00:00"


def test_worker_delegates_start_stop_shutdown_to_runtime() -> None:
    queue: Queue[UiEvent] = Queue()
    runtimes: list[FakeRuntime] = []
    worker = AssistantWorker(
        event_queue=queue,
        default_language="en-US",
        runtime_factory=_runtime_factory_sink(runtimes),
    )

    worker.start()
    runtime = runtimes[-1]
    assert runtime.started is True
    assert runtime.mode == RuntimeMode.GUI
    assert runtime.default_language == "en-US"
    assert worker.running is True

    worker.stop()
    assert runtime.stop_requested is True

    worker.shutdown()
    assert runtime.shutdown_called is True
    assert worker.running is False


def test_worker_restart_uses_fresh_runtime_instance() -> None:
    queue: Queue[UiEvent] = Queue()
    runtimes: list[FakeRuntime] = []
    worker = AssistantWorker(event_queue=queue, runtime_factory=_runtime_factory_sink(runtimes))

    worker.start()
    first_runtime = runtimes[-1]
    worker.shutdown()

    worker.start()
    second_runtime = runtimes[-1]

    assert first_runtime is not second_runtime
    assert second_runtime.started is True
