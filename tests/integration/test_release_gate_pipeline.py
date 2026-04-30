"""Integration tests for release gate pipeline ordering and fail-fast flow."""

from __future__ import annotations

from datetime import datetime, timezone

from core.release_gates import ReleaseGateRunner
from core.release_models import GateExecutionResult, ReleaseValidationRun


def test_release_gate_pipeline_runs_in_requested_order() -> None:
    order: list[str] = []

    def _gate(name: str):
        def _handler(_run: ReleaseValidationRun) -> GateExecutionResult:
            order.append(name)
            return GateExecutionResult(
                gate_name=name,
                status="passed",
                is_blocking=True,
                duration_ms=5,
                summary="ok",
            )

        return _handler

    runner = ReleaseGateRunner(
        gate_handlers={
            "compile": _gate("compile"),
            "unit_tests": _gate("unit_tests"),
            "lint": _gate("lint"),
        }
    )
    run = ReleaseValidationRun(
        run_id="run-001",
        candidate_id="candidate-001",
        commit_sha="abc1234",
        trigger="ci",
        started_at=datetime.now(timezone.utc),
    )

    result = runner.run(run, requested_gates=["compile", "unit_tests", "lint"])

    assert result.status == "passed"
    assert order == ["compile", "unit_tests", "lint"]


def test_release_gate_pipeline_stops_after_first_blocking_failure() -> None:
    order: list[str] = []

    def _compile(_run: ReleaseValidationRun) -> GateExecutionResult:
        order.append("compile")
        return GateExecutionResult(
            gate_name="compile",
            status="passed",
            is_blocking=True,
            duration_ms=5,
            summary="ok",
        )

    def _tests(_run: ReleaseValidationRun) -> GateExecutionResult:
        order.append("unit_tests")
        return GateExecutionResult(
            gate_name="unit_tests",
            status="failed",
            is_blocking=True,
            duration_ms=10,
            summary="failed",
            failure_code="tests_failed",
        )

    def _lint(_run: ReleaseValidationRun) -> GateExecutionResult:
        order.append("lint")
        return GateExecutionResult(
            gate_name="lint",
            status="passed",
            is_blocking=True,
            duration_ms=5,
            summary="ok",
        )

    runner = ReleaseGateRunner(gate_handlers={"compile": _compile, "unit_tests": _tests, "lint": _lint})
    run = ReleaseValidationRun(
        run_id="run-002",
        candidate_id="candidate-002",
        commit_sha="def5678",
        trigger="ci",
        started_at=datetime.now(timezone.utc),
    )

    result = runner.run(run, requested_gates=["compile", "unit_tests", "lint"])

    assert result.status == "failed"
    assert order == ["compile", "unit_tests"]
