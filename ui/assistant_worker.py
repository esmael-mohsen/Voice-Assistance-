"""GUI worker bridge for forwarding shared runtime events to the UI queue."""

from __future__ import annotations

from dataclasses import dataclass
from queue import Queue
from typing import Any, Callable, Optional

from core.assistant_runtime import AssistantRuntime, RuntimeEvent, RuntimeMode


@dataclass(frozen=True)
class UiEvent:
    type: str
    payload: dict


RuntimeFactory = Callable[..., Any]


class AssistantWorker:
    """Starts shared runtime in GUI mode and forwards events to the UI queue."""

    def __init__(
        self,
        event_queue: Queue,
        default_language: Optional[str] = None,
        runtime_factory: RuntimeFactory | None = None,
    ):
        self._queue = event_queue
        self._default_language = default_language
        self._runtime_factory = runtime_factory or AssistantRuntime
        self._runtime: AssistantRuntime | None = None

    @property
    def running(self) -> bool:
        return bool(self._runtime and self._runtime.running)

    def start(self) -> None:
        if self.running:
            return
        self._runtime = self._create_runtime()
        self._runtime.start_in_background()

    def stop(self) -> None:
        if self._runtime:
            self._runtime.request_stop()

    def shutdown(self, join_timeout_s: float = 2.0) -> None:
        if self._runtime:
            self._runtime.shutdown(join_timeout_s=join_timeout_s)
            self._runtime = None

    def _create_runtime(self) -> AssistantRuntime:
        return self._runtime_factory(
            mode=RuntimeMode.GUI,
            observer=self._on_runtime_event,
            default_language=self._default_language,
        )

    def _on_runtime_event(self, event: RuntimeEvent) -> None:
        self._queue.put(self.translate_runtime_event(event))

    @staticmethod
    def translate_runtime_event(event: RuntimeEvent) -> UiEvent:
        payload = dict(event.payload)
        # Preserve provider-aware metadata so GUI observers can render degraded/fallback state.
        for key in (
            "speech_provider",
            "persisted_speech_provider",
            "pending_speech_provider",
            "deferred_provider_switch",
            "degraded_mode",
            "degraded_reason",
            "fallback_from",
            "fallback_to",
            "provider",
            "stage",
            "fallback_applied",
            "manual_restart_required",
            "reason_code",
        ):
            if key in event.payload:
                payload[key] = event.payload[key]
        payload["session_id"] = event.session_id
        payload["timestamp"] = event.timestamp
        return UiEvent(type=event.type.value, payload=payload)
