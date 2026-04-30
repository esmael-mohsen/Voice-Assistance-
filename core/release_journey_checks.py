"""Primary journey validation checks for release gating."""

from __future__ import annotations

from core.release_models import GateExecutionResult

REQUIRED_PRIMARY_JOURNEYS: tuple[str, ...] = (
    "startup_to_ready",
    "wake_to_command",
    "command_to_spoken_response",
)


def run_journey_validation(journey_results: dict[str, bool]) -> GateExecutionResult:
    normalized = {str(key): bool(value) for key, value in journey_results.items()}
    missing = [journey for journey in REQUIRED_PRIMARY_JOURNEYS if journey not in normalized]
    failed = [journey for journey in REQUIRED_PRIMARY_JOURNEYS if journey in normalized and not normalized[journey]]

    if not missing and not failed:
        return GateExecutionResult(
            gate_name="journey_validation",
            status="passed",
            is_blocking=True,
            duration_ms=0,
            summary="All critical primary journeys passed.",
        )

    details = []
    if missing:
        details.append(f"missing: {', '.join(missing)}")
    if failed:
        details.append(f"failed: {', '.join(failed)}")
    return GateExecutionResult(
        gate_name="journey_validation",
        status="failed",
        is_blocking=True,
        duration_ms=0,
        summary="; ".join(details),
        failure_code="journey_regression_detected",
    )
