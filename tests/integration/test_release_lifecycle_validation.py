"""Integration tests for release lifecycle validation."""

from __future__ import annotations

from core.release_lifecycle_checks import run_lifecycle_validation


def test_lifecycle_validation_passes_for_required_state_coverage() -> None:
    gate_result = run_lifecycle_validation(
        observed_states=[
            "startup",
            "standby",
            "wake",
            "listening",
            "speaking",
            "error",
            "offline",
        ]
    )

    assert gate_result.status == "passed"


def test_lifecycle_validation_fails_when_required_state_missing() -> None:
    gate_result = run_lifecycle_validation(observed_states=["startup", "standby", "wake", "listening"])

    assert gate_result.status == "failed"
    assert gate_result.failure_code == "missing_lifecycle_states"
