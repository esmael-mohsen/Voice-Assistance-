"""Legacy wake-detection adapter."""

from __future__ import annotations

import logging
import re
import sys
import time
import threading
from typing import Any
from typing import Callable

from core.speech.interfaces import (
    WAKE_MODE_HARDWARE_TRIGGER,
    WAKE_MODE_KEYWORD_LOW_POWER,
    WAKE_MODE_STT_BASED,
    WakeService,
)
from core.wake_word import (
    LocalKeywordWakeDetector,
    WakeAction,
    WakeDetectionProfile,
    WakeResult,
    WakeWordDetector,
    detect_wake,
    normalize_wake_phrase,
)

logger = logging.getLogger(__name__)


def _highlight_heard_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "").strip())
    quoted = f"\"{cleaned}\""
    try:
        if getattr(sys.stdout, "isatty", lambda: False)():
            return f"\x1b[1;96m{quoted}\x1b[0m"
    except Exception:  # noqa: BLE001
        return quoted
    return quoted


class LegacyWakeService(WakeService):
    """Adapter over the existing wake-word detector."""

    def __init__(
        self,
        detector: WakeWordDetector | None = None,
        *,
        listener: Any | None = None,
        keyword_detector: LocalKeywordWakeDetector | None = None,
        hardware_signal_supplier: Callable[[], Any] | None = None,
        poll_interval_s: float = 0.05,
    ) -> None:
        self._detector = detector or WakeWordDetector()
        self._listener = listener
        self._keyword_detector = keyword_detector or LocalKeywordWakeDetector()
        self._hardware_signal_supplier = hardware_signal_supplier
        self._poll_interval_s = max(0.01, float(poll_interval_s))
        self._stop_requested = threading.Event()

    @property
    def detector(self) -> WakeWordDetector:
        return self._detector

    def attach_listener(self, listener: Any) -> None:
        self._listener = listener

    def set_hardware_signal_supplier(self, supplier: Callable[[], Any] | None) -> None:
        self._hardware_signal_supplier = supplier

    def clear_stop_request(self) -> None:
        self._stop_requested.clear()

    def request_stop(self) -> None:
        self._stop_requested.set()
        keyword_stop = getattr(self._keyword_detector, "request_stop", None)
        if callable(keyword_stop):
            keyword_stop()
        listener_stop = getattr(self._listener, "request_stop", None)
        if callable(listener_stop):
            listener_stop()

    def detect(self, input_text: str) -> Any:
        detected = self._detector.detect(input_text)
        if detected is not None:
            logger.info(
                "[WAKE] Accepted phrase=%s source=detector",
                _highlight_heard_text(getattr(detected, "phrase", input_text) or input_text),
            )
            return detected

        raw_text = str(input_text or "").strip()
        if not raw_text:
            return None

        detector_profile = getattr(self._detector, "profile", WakeDetectionProfile.BALANCED)
        detector_aliases = getattr(self._detector, "wake_names", None)
        primary = detect_wake(raw_text, profile=detector_profile, aliases=detector_aliases)
        # Recovery path: if balanced profile misses a noisy STT phrase in wake-only mode,
        # try a permissive profile before giving up.
        rescue = detect_wake(raw_text, profile=WakeDetectionProfile.DEVELOPMENT, aliases=detector_aliases)
        if rescue.accepted:
            logger.info(
                "[WAKE] Recovery accepted phrase=%s alias=%s score=%.3f threshold=%.3f",
                rescue.normalized_phrase,
                rescue.matched_alias,
                rescue.best_score,
                rescue.decision_threshold,
            )
            return WakeResult(action=WakeAction.START, phrase=normalize_wake_phrase(raw_text))
        logger.info(
            "[WAKE] Rejected phrase=%s primary(score=%.3f th=%.3f alias=%s) dev(score=%.3f th=%.3f alias=%s)",
            normalize_wake_phrase(raw_text),
            primary.best_score,
            primary.decision_threshold,
            primary.matched_alias,
            rescue.best_score,
            rescue.decision_threshold,
            rescue.matched_alias,
        )
        return None

    def wait_for_wake(
        self,
        *,
        timeout_s: float = 1.0,
        wake_mode: str | None = None,
        interrupt_event: Any | None = None,
    ) -> Any:
        self.clear_stop_request()
        timeout_value = max(0.1, float(timeout_s))
        deadline = time.monotonic() + timeout_value
        checker = getattr(interrupt_event, "is_set", None) if interrupt_event is not None else None
        if self._stop_requested.is_set() or (callable(checker) and checker()):
            return None
        waiter = getattr(self._detector, "wait_for_wake", None)
        if callable(waiter):
            try:
                result = waiter(timeout_s=timeout_value, wake_mode=wake_mode, interrupt_event=interrupt_event)
            except TypeError:
                try:
                    result = waiter(timeout_s=timeout_value, wake_mode=wake_mode)
                except TypeError:
                    result = waiter(timeout_s=timeout_value)
            if result is not None:
                return result

        if self._stop_requested.is_set() or (callable(checker) and checker()):
            return None
        direct_result = self.detect("")
        if direct_result is not None:
            return direct_result

        normalized_mode = str(wake_mode or WAKE_MODE_KEYWORD_LOW_POWER).strip().lower()
        if normalized_mode == WAKE_MODE_KEYWORD_LOW_POWER:
            remaining = max(0.0, deadline - time.monotonic())
            if callable(getattr(self._listener, "listen_any", None)):
                logger.info(
                    "[WAKE] Keyword mode using structured STT wake capture "
                    "(reason=legacy_keyword_precheck_not_reliable timeout=%.1fs)",
                    remaining,
                )
                phrase = self._listen_for_wake_phrase(timeout_s=remaining, interrupt_event=interrupt_event)
                if not phrase:
                    logger.debug("[WAKE] No wake phrase recognized in current standby cycle")
                    return None
                return self.detect(phrase)

            keyword_wait = getattr(self._keyword_detector, "wait_for_wake", None)
            if callable(keyword_wait):
                # Keep local keyword spotting as a quick low-power pre-check only.
                # We reserve most of the wake window for full STT wake phrases.
                remaining_total = max(0.0, deadline - time.monotonic())
                keyword_budget = min(1.4, max(0.6, timeout_value * 0.2))
                remaining_for_keyword = min(keyword_budget, max(0.0, remaining_total - 1.0))
                if remaining_for_keyword > 0:
                    try:
                        keyword_result = keyword_wait(
                            timeout_s=remaining_for_keyword,
                            interrupt_event=interrupt_event,
                        )
                    except TypeError:
                        keyword_result = keyword_wait(timeout_s=remaining_for_keyword)
                    if keyword_result is not None:
                        return keyword_result

            remaining = max(0.0, deadline - time.monotonic())
            if remaining <= 0:
                logger.debug("[WAKE] Wake window exhausted before STT fallback listen")
                return None
            phrase = self._listen_for_wake_phrase(timeout_s=remaining, interrupt_event=interrupt_event)
            if not phrase:
                logger.debug("[WAKE] No wake phrase recognized in current standby cycle")
                return None
            return self.detect(phrase)

        if normalized_mode == WAKE_MODE_HARDWARE_TRIGGER:
            hardware_result = self._wait_for_hardware_trigger(timeout_s=timeout_value, interrupt_event=interrupt_event)
            return hardware_result

        if normalized_mode != WAKE_MODE_STT_BASED:
            return None

        remaining = max(0.0, deadline - time.monotonic())
        if remaining <= 0:
            return None
        phrase = self._listen_for_wake_phrase(timeout_s=remaining, interrupt_event=interrupt_event)
        if not phrase:
            logger.debug("[WAKE] STT-based wake mode: no phrase recognized")
            return None
        return self.detect(phrase)

    def _wait_for_hardware_trigger(
        self,
        *,
        timeout_s: float,
        interrupt_event: Any | None = None,
    ) -> WakeResult | None:
        supplier = self._hardware_signal_supplier
        if supplier is None:
            return None
        deadline = time.monotonic() + timeout_s
        checker = getattr(interrupt_event, "is_set", None) if interrupt_event is not None else None
        while time.monotonic() < deadline:
            if self._stop_requested.is_set() or (callable(checker) and checker()):
                return None
            signal = supplier()
            if signal is None or signal is False:
                time.sleep(self._poll_interval_s)
                continue
            if isinstance(signal, WakeResult):
                return signal
            if isinstance(signal, str):
                detected = self.detect(signal)
                if detected is not None:
                    return detected
                return WakeResult(action=WakeAction.START, phrase=signal.strip().lower() or WAKE_MODE_HARDWARE_TRIGGER)
            if isinstance(signal, bool):
                return WakeResult(action=WakeAction.START, phrase=WAKE_MODE_HARDWARE_TRIGGER)
            return WakeResult(action=WakeAction.START, phrase=WAKE_MODE_HARDWARE_TRIGGER)
        return None

    def _listen_for_wake_phrase(
        self,
        *,
        timeout_s: float,
        interrupt_event: Any | None = None,
    ) -> str | None:
        listener = self._listener
        if listener is None:
            return None

        listen_any = getattr(listener, "listen_any", None)
        if not callable(listen_any):
            return None

        languages: list[str] = []
        listener_language = str(getattr(listener, "language", "") or "").strip()
        if listener_language:
            languages.append(listener_language)
        for language in ("ar-EG", "en-US"):
            if language not in languages:
                languages.append(language)

        timeout_value = max(1.0, float(timeout_s))
        checker = getattr(interrupt_event, "is_set", None) if interrupt_event is not None else None
        if self._stop_requested.is_set() or (callable(checker) and checker()):
            return None

        deadline = time.monotonic() + timeout_value
        structured_attempted = False
        structured_listener = getattr(listener, "listen_command_result", None)
        if callable(structured_listener):
            structured_attempted = True
            structured_timeout = max(1.2, min(timeout_value, max(1.2, deadline - time.monotonic())))
            structured_phrase_limit = max(1.0, min(4.0, structured_timeout))
            logger.info(
                "[WAKE] Structured wake capture start languages=%s timeout=%.1fs phrase_limit=%.1fs",
                languages,
                structured_timeout,
                structured_phrase_limit,
            )
            try:
                structured_result = structured_listener(
                    timeout_s=structured_timeout,
                    phrase_time_limit_s=structured_phrase_limit,
                    interrupt_event=interrupt_event,
                    languages=languages,
                    recognition_path="local_first",
                    usage_mode="standby_wake",
                    capture_profile_id="standby_wake.default",
                    dictionary_bias_mode="none",
                    closed_vocabulary_id=None,
                    closed_vocabulary_choices=None,
                    qualification_profile_id="default",
                )
            except TypeError:
                try:
                    structured_result = structured_listener(
                        timeout_s=structured_timeout,
                        phrase_time_limit_s=structured_phrase_limit,
                        interrupt_event=interrupt_event,
                        languages=languages,
                    )
                except TypeError:
                    structured_result = structured_listener()

            if isinstance(structured_result, str):
                structured_text = structured_result.strip()
                if structured_text:
                    logger.info(
                        "[WAKE][HEARD] %s (source=structured_capture)",
                        _highlight_heard_text(structured_text),
                    )
                    return structured_text

            if structured_result is not None:
                error_code = getattr(structured_result, "error_code", None)
                primary_transcript = str(getattr(structured_result, "primary_transcript", "") or "").strip()
                source = getattr(structured_result, "recognition_source", None)
                latency_ms = getattr(structured_result, "latency_ms", None)
                if not error_code and primary_transcript:
                    logger.info(
                        "[WAKE][HEARD] %s (source=structured_capture recognition_source=%s latency_ms=%s)",
                        _highlight_heard_text(primary_transcript),
                        source or "unknown",
                        latency_ms if latency_ms is not None else "unknown",
                    )
                    return primary_transcript
                logger.info(
                    "[WAKE] Structured wake capture empty error=%s source=%s latency_ms=%s",
                    error_code or "no_transcript",
                    source or "unknown",
                    latency_ms if latency_ms is not None else "unknown",
                )

        while time.monotonic() < deadline:
            if self._stop_requested.is_set() or (callable(checker) and checker()):
                return None
            remaining = max(0.0, deadline - time.monotonic())
            if remaining <= 0:
                break
            slot_timeout = max(1, int(round(min(3.0, remaining))))
            slot_phrase_limit = max(2, min(4, slot_timeout + 1))
            try:
                text = listen_any(
                    languages,
                    prompt="[WAKE] Listening...",
                    timeout=slot_timeout,
                    phrase_time_limit=slot_phrase_limit,
                    interrupt_event=interrupt_event,
                )
            except TypeError:
                try:
                    text = listen_any(
                        languages,
                        prompt="[WAKE] Listening...",
                        timeout=slot_timeout,
                        phrase_time_limit=slot_phrase_limit,
                    )
                except TypeError:
                    text = listen_any(languages)
            if text:
                normalized_text = str(text).strip()
                if normalized_text:
                    logger.info("[WAKE][HEARD] %s (source=listen_any)", _highlight_heard_text(normalized_text))
                    return normalized_text

        # Recovery path: run one short structured-capture pass when wake STT
        # returns no transcript, to reduce false misses from borderline audio.
        if not structured_attempted:
            logger.info("[WAKE] No transcript from primary wake listen; trying structured fallback")
        else:
            logger.info("[WAKE] No transcript from wake capture")
        if callable(structured_listener) and not structured_attempted:
            structured_timeout = max(1.2, min(3.0, float(timeout_s)))
            structured_phrase_limit = max(1.0, min(3.0, structured_timeout))
            try:
                structured_result = structured_listener(
                    timeout_s=structured_timeout,
                    phrase_time_limit_s=structured_phrase_limit,
                    interrupt_event=interrupt_event,
                    languages=languages,
                    recognition_path="local_first",
                    usage_mode="standby_wake",
                    capture_profile_id="standby_wake.default",
                    dictionary_bias_mode="none",
                    closed_vocabulary_id=None,
                    closed_vocabulary_choices=None,
                    qualification_profile_id="default",
                )
            except TypeError:
                try:
                    structured_result = structured_listener(
                        timeout_s=structured_timeout,
                        phrase_time_limit_s=structured_phrase_limit,
                        interrupt_event=interrupt_event,
                        languages=languages,
                    )
                except TypeError:
                    structured_result = structured_listener()

            if isinstance(structured_result, str):
                structured_text = structured_result.strip()
                if structured_text:
                    logger.info(
                        "[WAKE][HEARD] %s (source=structured_fallback)",
                        _highlight_heard_text(structured_text),
                    )
                    return structured_text

            if structured_result is not None:
                error_code = getattr(structured_result, "error_code", None)
                primary_transcript = str(getattr(structured_result, "primary_transcript", "") or "").strip()
                if not error_code and primary_transcript:
                    logger.info(
                        "[WAKE][HEARD] %s (source=structured_fallback)",
                        _highlight_heard_text(primary_transcript),
                    )
                    return primary_transcript

        logger.warning(
            "[WAKE] Wake miss: no transcript captured (languages=%s timeout=%ss phrase_limit=%ss)",
            languages,
            max(1, int(round(timeout_value))),
            4,
        )
        return None

    def keyword_wake_available(self) -> bool:
        local_keyword_available = bool(getattr(self._keyword_detector, "is_available", lambda: False)())
        if local_keyword_available:
            return True
        if callable(getattr(self._detector, "wait_for_wake", None)):
            return True
        return callable(getattr(self._listener, "listen_any", None))

    def hardware_trigger_available(self) -> bool:
        return self._hardware_signal_supplier is not None

    def supports_mode(self, wake_mode: str) -> bool:
        normalized = str(wake_mode or "").strip().lower()
        if normalized == WAKE_MODE_KEYWORD_LOW_POWER:
            # Keep keyword mode available when dedicated local KWS exists
            # or a provider-specific detector can poll wake boundaries.
            if self.keyword_wake_available():
                return True
            return callable(getattr(self._detector, "wait_for_wake", None))
        if normalized == WAKE_MODE_HARDWARE_TRIGGER:
            return self.hardware_trigger_available()
        return normalized in {
            WAKE_MODE_STT_BASED,
        }

    def is_available(self) -> bool:
        keyword_available = bool(getattr(self._keyword_detector, "is_available", lambda: False)())
        if keyword_available:
            return True
        if self._detector is not None:
            return True
        checker = getattr(self._detector, "is_available", None)
        if callable(checker):
            return bool(checker())
        return True
