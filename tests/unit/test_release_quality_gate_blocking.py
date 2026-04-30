"""Unit tests for release quality gate blocking semantics."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from types import SimpleNamespace

from core.release_gates import ReleaseGateRunner, default_command_gate_handlers
from core.release_models import GateExecutionResult, ReleaseValidationRun
from core.release_override import OverrideGovernanceService


def test_blocking_gate_failure_stops_execution_without_override() -> None:
    call_order: list[str] = []

    def _pass(_run: ReleaseValidationRun) -> GateExecutionResult:
        call_order.append("compile")
        return GateExecutionResult(
            gate_name="compile",
            status="passed",
            is_blocking=True,
            duration_ms=10,
            summary="ok",
        )

    def _fail(_run: ReleaseValidationRun) -> GateExecutionResult:
        call_order.append("unit_tests")
        return GateExecutionResult(
            gate_name="unit_tests",
            status="failed",
            is_blocking=True,
            duration_ms=20,
            summary="tests failed",
            failure_code="tests_failed",
        )

    def _should_not_run(_run: ReleaseValidationRun) -> GateExecutionResult:
        call_order.append("lint")
        return GateExecutionResult(
            gate_name="lint",
            status="passed",
            is_blocking=True,
            duration_ms=10,
            summary="ok",
        )

    runner = ReleaseGateRunner(
        gate_handlers={
            "compile": _pass,
            "unit_tests": _fail,
            "lint": _should_not_run,
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

    assert result.status == "failed"
    assert call_order == ["compile", "unit_tests"]


def test_approved_override_allows_release_completion() -> None:
    governance = OverrideGovernanceService()
    override = governance.request_override(
        run_id="run-002",
        requested_by="release-manager",
        reason="emergency release required",
        failed_blocking_gates=["lint"],
    )
    override = governance.approve_override(
        override=override,
        engineering_lead_approver="eng-lead",
        qa_safety_approver="qa-owner",
    )

    runner = ReleaseGateRunner(
        gate_handlers={
            "lint": lambda _run: GateExecutionResult(
                gate_name="lint",
                status="failed",
                is_blocking=True,
                duration_ms=15,
                summary="lint failed",
                failure_code="lint_failed",
            )
        },
        governance=governance,
    )
    run = ReleaseValidationRun(
        run_id="run-002",
        candidate_id="candidate-002",
        commit_sha="def5678",
        trigger="manual",
        started_at=datetime.now(timezone.utc),
    )
    run.override_record = override

    result = runner.run(run, requested_gates=["lint"])

    assert result.status == "approved_with_override"


def test_default_gate_handlers_use_active_python_interpreter(monkeypatch) -> None:
    captured: list[list[str]] = []

    def _fake_run(command, capture_output, text, check):  # noqa: ANN001
        captured.append(list(command))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("core.release_gates.subprocess.run", _fake_run)
    handlers = default_command_gate_handlers()
    run = ReleaseValidationRun(
        run_id="run-003",
        candidate_id="candidate-003",
        commit_sha="ghi9012",
        trigger="manual",
        started_at=datetime.now(timezone.utc),
    )

    handlers["compile"](run)
    handlers["unit_tests"](run)
    handlers["lint"](run)

    assert captured
    assert all(command[0] == sys.executable for command in captured)
    assert captured[0][:3] == [sys.executable, "-m", "compileall"]
    assert captured[1][:3] == [sys.executable, "-m", "pytest"]
    assert captured[2][:4] == [sys.executable, "-m", "ruff", "check"]
