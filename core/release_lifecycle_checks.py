"""Lifecycle validation checks for release gating."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from core.release_models import GateExecutionResult

REQUIRED_LIFECYCLE_STATES: tuple[str, ...] = (
    "startup",
    "standby",
    "wake",
    "listening",
    "speaking",
    "error",
    "offline",
)


@dataclass(frozen=True)
class LifecycleValidationSummary:
    observed_states: list[str]
    missing_states: list[str]
    passed: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def summarize_lifecycle_validation(observed_states: list[str]) -> LifecycleValidationSummary:
    normalized = [str(item).strip().lower() for item in observed_states]
    missing = [state for state in REQUIRED_LIFECYCLE_STATES if state not in normalized]
    return LifecycleValidationSummary(
        observed_states=normalized,
        missing_states=missing,
        passed=not missing,
    )


def run_lifecycle_validation(observed_states: list[str]) -> GateExecutionResult:
    summary = summarize_lifecycle_validation(observed_states)
    if summary.passed:
        return GateExecutionResult(
            gate_name="lifecycle_validation",
            status="passed",
            is_blocking=True,
            duration_ms=0,
            summary="All required lifecycle states were observed.",
        )

    return GateExecutionResult(
        gate_name="lifecycle_validation",
        status="failed",
        is_blocking=True,
        duration_ms=0,
        summary=f"Missing lifecycle states: {', '.join(summary.missing_states)}",
        failure_code="missing_lifecycle_states",
    )
