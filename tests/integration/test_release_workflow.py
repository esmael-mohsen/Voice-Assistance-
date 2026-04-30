"""Integration tests for release workflow artifacts and checklist enforcement."""

from __future__ import annotations

from datetime import datetime, timezone

from core.critical_prompts import build_default_critical_prompt_catalog, surface_binding_payloads
from core.release_artifacts import build_validation_manifest
from core.release_gates import (
    ReleaseGateRunner,
    build_baseline_gate_result,
    build_release_story_gate_handlers,
    compare_latency_metrics,
    validate_release_checklist,
)
from core.release_models import ArtifactEntry, GateExecutionResult, ReleaseChecklistRecord, ReleaseValidationRun


def test_release_workflow_checklist_gate_fails_when_required_item_fails() -> None:
    checklist = ReleaseChecklistRecord(
        checklist_id="chk-001",
        run_id="run-001",
        offline_behavior_status="pass",
        emergency_control_status="fail",
        audio_permission_status="pass",
        crash_recovery_status="pass",
        completed_by="qa-owner",
        completed_at=datetime.now(timezone.utc),
    )

    gate_result = validate_release_checklist(checklist)

    assert gate_result.status == "failed"
    assert gate_result.failure_code == "checklist_incomplete"


def test_release_workflow_manifest_sets_180_day_retention() -> None:
    approved_at = datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc)
    manifest = build_validation_manifest(
        run_id="run-001",
        storage_root="artifacts/run-001",
        entries=[ArtifactEntry(kind="gate_summary", path="summary.json", checksum="sha256:abc")],
        approved_at=approved_at,
        include_override=False,
    )

    assert (manifest.retention_until - approved_at).days == 180


def test_release_workflow_manifest_requires_base_artifact_index() -> None:
    approved_at = datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc)
    manifest = build_validation_manifest(
        run_id="run-001a",
        storage_root="artifacts/run-001a",
        entries=[
            ArtifactEntry(kind="gate_summary", path="summary.json", checksum="sha256:abc"),
            ArtifactEntry(kind="test_results", path="gate-results.json", checksum="sha256:def"),
        ],
        approved_at=approved_at,
        include_override=False,
    )

    assert manifest.missing_required_kinds(include_override=False) == ["diagnostic_artifact_index"]


def test_release_workflow_baseline_compare_fails_when_required_metric_missing() -> None:
    comparisons = compare_latency_metrics(
        run_id="run-002",
        current_metrics={"wake_to_listen": 700.0, "listen_to_result": 900.0},
        baseline_metrics={
            "wake_to_listen": 680.0,
            "listen_to_result": 880.0,
            "result_to_speech_start": 600.0,
        },
        threshold_policy={
            "wake_to_listen": {"threshold_ms": 100.0, "threshold_pct": 15.0},
            "listen_to_result": {"threshold_ms": 100.0, "threshold_pct": 15.0},
            "result_to_speech_start": {"threshold_ms": 80.0, "threshold_pct": 15.0},
        },
    )
    baseline_gate = build_baseline_gate_result(comparisons)

    assert baseline_gate.status == "failed"
    assert baseline_gate.failure_code == "baseline_threshold_breach"


def test_release_workflow_reruns_keep_deterministic_failure_result() -> None:
    def _compile_fail(_run: ReleaseValidationRun) -> GateExecutionResult:
        return GateExecutionResult(
            gate_name="compile",
            status="failed",
            is_blocking=True,
            duration_ms=10,
            summary="compile failed",
            failure_code="compile_failed",
        )

    runner = ReleaseGateRunner(gate_handlers={"compile": _compile_fail})
    run_1 = ReleaseValidationRun(
        run_id="run-rerun-1",
        candidate_id="candidate-1",
        commit_sha="sha-1",
        trigger="ci",
        started_at=datetime.now(timezone.utc),
    )
    run_2 = ReleaseValidationRun(
        run_id="run-rerun-2",
        candidate_id="candidate-2",
        commit_sha="sha-2",
        trigger="ci",
        started_at=datetime.now(timezone.utc),
    )

    result_1 = runner.run(run_1, requested_gates=["compile"])
    result_2 = runner.run(run_2, requested_gates=["compile"])

    assert result_1.status == "failed"
    assert result_2.status == "failed"
    assert result_1.failed_blocking_gates() == ["compile"]
    assert result_2.failed_blocking_gates() == ["compile"]


def test_release_workflow_checklist_detects_startup_audio_permission_drift() -> None:
    checklist = ReleaseChecklistRecord(
        checklist_id="chk-audio-drift",
        run_id="run-audio-drift",
        offline_behavior_status="pass",
        emergency_control_status="pass",
        audio_permission_status="fail",
        crash_recovery_status="pass",
        completed_by="qa-owner",
        completed_at=datetime.now(timezone.utc),
        notes="audio input permission denied on startup",
    )

    gate_result = validate_release_checklist(checklist)

    assert gate_result.status == "failed"
    assert "audio_permission" in gate_result.summary


def test_release_workflow_localization_gate_blocks_on_binding_drift() -> None:
    catalog = build_default_critical_prompt_catalog()
    bindings = surface_binding_payloads()
    bindings[0]["prompt_key"] = "embedded_startup_text"
    runner = ReleaseGateRunner(
        gate_handlers=build_release_story_gate_handlers(
            localization_catalog=catalog,
            localization_surface_bindings=bindings,
        )
    )
    run = ReleaseValidationRun(
        run_id="run-localization-drift",
        candidate_id="candidate-localization-drift",
        commit_sha="sha-localization-drift",
        trigger="ci",
        started_at=datetime.now(timezone.utc),
    )

    result = runner.run(run, requested_gates=["localization_validation"])

    assert result.status == "failed"
    assert result.failed_blocking_gates() == ["localization_validation"]
    assert result.gate_results[-1].failure_code == "critical_prompt_integrity_failed"
