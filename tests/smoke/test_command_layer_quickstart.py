"""Smoke validation for command layer hardening quickstart paths."""

from __future__ import annotations

import time

from core import resolver
from core.dispatcher import dispatch


def setup_function() -> None:
    resolver.reset_session_context()


def test_curated_regression_success_rate_and_safe_failures() -> None:
    curated = [
        ("start obstacle detection", "success"),
        ("stop obstacle detection", "success"),
        ("start ocr", "success"),
        ("recognize face", "success"),
        ("recognize emotion", "success"),
        ("start money detection", "success"),
        ("switch to english", "success"),
        ("male voice", "success"),
        ("stop system", "confirmation_required"),
        ("set language", "clarification_required"),
        ("random unrelated phrase", "rejected"),
    ]

    passed = 0
    for text, expected in curated:
        result = dispatch(text)
        if result.status == expected:
            passed += 1

    success_rate = passed / len(curated)
    assert success_rate >= 0.9


def test_protected_near_match_has_zero_unintended_activation() -> None:
    risky_near_matches = [
        "stop assistant now",
        "reset my mood",
        "stob systm",
    ]
    for text in risky_near_matches:
        result = dispatch(text)
        assert not (result.intent_id in {"stop_system", "reset_settings"} and result.status == "success")


def test_dispatch_baseline_capture_regression_smoke() -> None:
    start = time.perf_counter()
    result = dispatch("start obstacle detection")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result.status == "success"
    assert elapsed_ms > 0
    # Generous smoke threshold to catch catastrophic regressions only.
    assert elapsed_ms < 1000


def test_phase9_protected_confirmation_phrase_families_smoke() -> None:
    confirmation = dispatch("stop system")
    assert confirmation.status == "confirmation_required"

    affirmative = dispatch("yes please")
    assert affirmative.status == "success"
    assert affirmative.intent_id == "stop_system"

    second_confirmation = dispatch("reset settings")
    assert second_confirmation.status == "confirmation_required"
    cancelled = dispatch("yes cancel")
    assert cancelled.status == "rejected"
    assert cancelled.error_code == "confirmation_declined"


def test_phase9_clarification_bounded_retry_smoke() -> None:
    first = dispatch("set language")
    second = dispatch("unknown option")
    third = dispatch("still unknown")

    assert first.status == "clarification_required"
    assert second.status == "clarification_required"
    assert third.status == "failed"
    assert third.error_code == "clarification_failed"


def test_phase13_dispatch_accepts_canonicalized_command_text_smoke() -> None:
    result = dispatch(
        "reed txt",
        canonical_command_text="read text",
        recognition_metadata={"recognition_path": "local_first"},
    )
    assert result.metadata["canonical_command_text"] == "read text"
