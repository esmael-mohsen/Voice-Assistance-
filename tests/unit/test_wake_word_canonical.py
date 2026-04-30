"""Unit tests for canonical Phase 11 wake vocabulary."""

from __future__ import annotations

from types import SimpleNamespace

import core.wake_word as wake_word_module
from core.wake_word import (
    LocalKeywordWakeDetector,
    WakeAction,
    WakeWordDetector,
    detect_wake,
    is_canonical_wake_phrase,
)


def test_canonical_wake_phrase_detector_accepts_hi_egb_and_marhaba() -> None:
    assert is_canonical_wake_phrase("hi egb") is True
    assert is_canonical_wake_phrase("\u0645\u0631\u062d\u0628\u0627") is True


def test_wake_detector_starts_on_canonical_phrase() -> None:
    detector = WakeWordDetector()
    wake = detector.detect("hi egb")
    assert wake is not None
    assert wake.action == WakeAction.START


def test_wake_detector_accepts_colloquial_arabic_stt_variants() -> None:
    detector = WakeWordDetector()
    for phrase in (
        "\u0647\u0627\u064a \u0627\u064a \u062c\u064a \u0628\u064a",
        "\u0627\u0647\u0644\u0627 \u0627\u064a\u062c\u064a",
        "\u0647\u0644\u0627 \u0627\u064a \u062c\u064a \u0628\u064a",
    ):
        wake = detector.detect(phrase)
        assert wake is not None, f"expected wake for phrase: {phrase}"
        assert wake.action == WakeAction.START


def test_wake_detector_accepts_common_english_stt_variants() -> None:
    detector = WakeWordDetector()
    for phrase in ("hi hgb", "hai e g p", "hello a g b"):
        wake = detector.detect(phrase)
        assert wake is not None, f"expected wake for phrase: {phrase}"
        assert wake.action == WakeAction.START


def test_wake_detector_rejects_non_wake_english_greetings() -> None:
    detector = WakeWordDetector()
    assert detector.detect("hi there") is None
    assert detector.detect("hello everyone") is None


def test_local_keyword_detector_accepts_arabic_marhaba(monkeypatch) -> None:
    detector = LocalKeywordWakeDetector()

    class _FakeMicrophone:
        def __init__(self) -> None:
            self.stream = SimpleNamespace(stop_stream=lambda: None)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ARG002
            return None

    class _FakeRecognizer:
        def listen(self, source, timeout, phrase_time_limit):  # noqa: ARG002
            return b"audio"

        def recognize_sphinx(self, audio, keyword_entries):  # noqa: ARG002
            return "مرحبا"

    monkeypatch.setattr(wake_word_module, "sr", SimpleNamespace(Microphone=_FakeMicrophone))
    detector._recognizer = _FakeRecognizer()
    monkeypatch.setattr(detector, "is_available", lambda: True)

    wake = detector.wait_for_wake(timeout_s=0.2)
    assert wake is not None
    assert wake.action == WakeAction.START
    assert wake.phrase == "مرحبا"

def test_wake_plus_command_is_accepted_as_wake_only_boundary() -> None:
    decision = detect_wake("hi egb open navigation")
    assert decision.accepted is True
    assert decision.matched_alias == "hi egb"


def test_command_only_phrase_is_rejected_as_non_wake() -> None:
    decision = detect_wake("open navigation")
    assert decision.accepted is False
