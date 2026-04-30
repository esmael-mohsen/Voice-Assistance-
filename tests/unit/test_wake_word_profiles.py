"""Unit tests for the profile-aware wake-word scoring pipeline."""

from __future__ import annotations

from core.wake_word import (
    WakeDetectionProfile,
    WakeWordDetector,
    detect_wake,
    normalize_text,
    score_wake_phrase,
)


def test_normalize_text_removes_noise_and_punctuation() -> None:
    normalized = normalize_text("Please, hi   EGB!!")
    assert normalized == "hi egb"


def test_score_wake_phrase_exact_beats_near_match() -> None:
    exact = score_wake_phrase("hi egb", "hi egb", WakeDetectionProfile.BALANCED)
    near = score_wake_phrase("hi egx", "hi egb", WakeDetectionProfile.BALANCED)
    assert exact.total_score > near.total_score
    assert exact.accepted is True


def test_profiles_change_detection_thresholds() -> None:
    strict_score = score_wake_phrase("hai e g p", "e g p", WakeDetectionProfile.STRICT)
    dev_score = score_wake_phrase("hai e g p", "e g p", WakeDetectionProfile.DEVELOPMENT)
    assert strict_score.decision_threshold > dev_score.decision_threshold
    assert dev_score.total_score >= strict_score.total_score


def test_detector_exposes_telemetry_hook_and_feedback() -> None:
    events: list[dict] = []
    detector = WakeWordDetector(telemetry_hook=events.append)

    assert detector.detect("hi egb") is not None
    assert detector.detect("hello everyone") is None
    snapshot = detector.report_detection_feedback(expected_wake=True, detected=False)

    assert snapshot.attempts == 2
    assert snapshot.false_rejects == 1
    assert any(event.get("event") == "wake_detection" for event in events)
    assert any(event.get("event") == "wake_feedback" for event in events)


def test_detect_wake_returns_structured_decision() -> None:
    decision = detect_wake("hi hgb", profile=WakeDetectionProfile.BALANCED)
    assert decision.accepted is True
    assert decision.best_score >= decision.decision_threshold
    assert decision.matched_alias is not None


def test_detect_wake_accepts_common_stt_distortions_for_egb() -> None:
    agency_decision = detect_wake("hi agency", profile=WakeDetectionProfile.BALANCED)
    yi_decision = detect_wake("hi yi the p", profile=WakeDetectionProfile.BALANCED)
    high_decision = detect_wake("high e g b", profile=WakeDetectionProfile.BALANCED)
    assert agency_decision.accepted is True
    assert yi_decision.accepted is True
    assert high_decision.accepted is True


def test_development_profile_rejects_short_greeting_non_wake_phrase() -> None:
    decision = detect_wake("hello assistant", profile=WakeDetectionProfile.DEVELOPMENT)
    assert decision.accepted is False


def test_profiles_reject_command_only_transcript_without_canonical_wake() -> None:
    balanced = detect_wake("open navigation now", profile=WakeDetectionProfile.BALANCED)
    strict = detect_wake("open navigation now", profile=WakeDetectionProfile.STRICT)
    assert balanced.accepted is False
    assert strict.accepted is False
