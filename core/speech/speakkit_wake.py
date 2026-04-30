"""SpeakKit wake adapter."""

from __future__ import annotations

from typing import Any

from core.speech.interfaces import (
    WAKE_MODE_HARDWARE_TRIGGER,
    WAKE_MODE_KEYWORD_LOW_POWER,
    WAKE_MODE_STT_BASED,
    WakeService,
)


class SpeakKitWakeService(WakeService):
    """Adapter wrapper around a SpeakKit wake backend."""

    def __init__(self, backend: Any = None, *, available: bool | None = None) -> None:
        self._backend = backend
        self._available_override = available

    def detect(self, input_text: str) -> Any:
        if self._backend is None:
            return None
        detector = getattr(self._backend, "detect", None)
        if callable(detector):
            return detector(input_text)
        return None

    def wait_for_wake(
        self,
        *,
        timeout_s: float = 1.0,
        wake_mode: str | None = None,
        interrupt_event: Any | None = None,
    ) -> Any:
        if self._backend is None:
            return None
        waiter = getattr(self._backend, "wait_for_wake", None)
        if callable(waiter):
            try:
                return waiter(timeout_s=timeout_s, wake_mode=wake_mode, interrupt_event=interrupt_event)
            except TypeError:
                try:
                    return waiter(timeout_s=timeout_s, wake_mode=wake_mode)
                except TypeError:
                    return waiter(timeout_s=timeout_s)
        return self.detect("")

    def supports_mode(self, wake_mode: str) -> bool:
        if self._backend is None:
            return False
        supports = getattr(self._backend, "supports_mode", None)
        if callable(supports):
            try:
                return bool(supports(wake_mode))
            except Exception:  # noqa: BLE001
                return False
        normalized = str(wake_mode or "").strip().lower()
        return normalized in {
            WAKE_MODE_KEYWORD_LOW_POWER,
            WAKE_MODE_HARDWARE_TRIGGER,
            WAKE_MODE_STT_BASED,
        }

    def is_available(self) -> bool:
        if self._available_override is not None:
            return bool(self._available_override)
        checker = getattr(self._backend, "is_available", None)
        if callable(checker):
            return bool(checker())
        return self._backend is not None

    def request_stop(self) -> None:
        stopper = getattr(self._backend, "request_stop", None)
        if callable(stopper):
            stopper()
