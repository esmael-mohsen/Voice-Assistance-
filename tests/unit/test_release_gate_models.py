"""Unit tests for release gate data models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.release_gates import evaluate_pi_qualification_run, evaluate_speech_release_gate
from core.release_models import (
    ArtifactEntry,
    GateExecutionResult,
    PiQualificationMetrics,
    ReleaseChecklistRecord,
    ReleaseValidationRun,
    SpeechReleaseGateResult,
    ValidationArtifactManifest,
)


def test_gate_result_requires_failure_code_when_failed() -> None:
    with pytest.raises(ValueError):
        GateExecutionResult(
            gate_name="compile",
            status="failed",
            is_blocking=True,
            duration_ms=10,
            summary="compile failed",
            failure_code=None,
        )


def test_release_validation_run_marks_failed_on_blocking_failure() -> None:
    run = ReleaseValidationRun(
        run_id="run-001",
        candidate_id="candidate-001",
        commit_sha="abc1234",
        trigger="ci",
        started_at=datetime.now(timezone.utc),
    )

    run.add_gate_result(
        GateExecutionResult(
            gate_name="compile",
            status="failed",
            is_blocking=True,
            duration_ms=100,
            summary="compile failed",
            failure_code="compile_failed",
        )
    )

    assert run.status == "failed"
    assert run.executed_checks == ["compile"]


def test_release_validation_run_requires_completion_timestamp_for_finalization() -> None:
    run = ReleaseValidationRun(
        run_id="run-002",
        candidate_id="candidate-002",
        commit_sha="def5678",
        trigger="manual",
        started_at=datetime.now(timezone.utc),
    )

    with pytest.raises(ValueError):
        run.finalize(status="passed", completed_at=None)


def test_release_checklist_passes_only_when_all_required_items_pass() -> None:
    checklist = ReleaseChecklistRecord(
        checklist_id="chk-001",
        run_id="run-003",
        offline_behavior_status="pass",
        emergency_control_status="pass",
        audio_permission_status="pass",
        crash_recovery_status="pass",
        completed_by="qa-owner",
        completed_at=datetime.now(timezone.utc),
    )

    assert checklist.is_passed is True


def test_validation_manifest_requires_retention_after_creation() -> None:
    created_at = datetime.now(timezone.utc)
    retention_until = created_at.replace(year=created_at.year + 1)
    manifest = ValidationArtifactManifest(
        manifest_id="manifest-001",
        run_id="run-004",
        created_at=created_at,
        storage_root="artifacts/run-004",
        artifact_entries=[
            ArtifactEntry(kind="gate_summary", path="summary.json", checksum="sha256:abc")
        ],
        retention_until=retention_until,
    )

    assert manifest.retention_until > manifest.created_at


def test_artifact_entry_supports_missing_artifact_reference() -> None:
    entry = ArtifactEntry(
        kind="baseline_comparison",
        path="",
        checksum="",
        available=False,
        source="missing",
        notes="Baseline comparison was not produced for this run.",
    )

    assert entry.available is False
    assert entry.source == "missing"


def test_validation_manifest_reports_missing_base_artifact_kinds() -> None:
    created_at = datetime.now(timezone.utc)
    retention_until = created_at.replace(year=created_at.year + 1)
    manifest = ValidationArtifactManifest(
        manifest_id="manifest-002",
        run_id="run-005",
        created_at=created_at,
        storage_root="artifacts/run-005",
        artifact_entries=[
            ArtifactEntry(kind="gate_summary", path="summary.json", checksum="sha256:abc")
        ],
        retention_until=retention_until,
    )

    assert manifest.missing_required_kinds(include_override=False) == [
        "diagnostic_artifact_index",
        "test_results",
    ]


def test_pi_qualification_run_fails_when_thresholds_are_exceeded() -> None:
    metrics = PiQualificationMetrics(
        duration_minutes=30,
        standby_cpu_median_pct=30.0,
        wake_cpu_peak_pct=68.0,
        listen_cpu_peak_pct=63.0,
        listen_memory_mb=214.0,
        speak_cpu_peak_pct=61.0,
        speak_memory_mb=220.0,
        startup_latency_ms=6200,
        peak_temp_c=86.0,
        repeated_wake_cycles=40,
        unexpected_shutdown_count=1,
        telemetry_completeness_ratio=0.82,
    )
    outcome = evaluate_pi_qualification_run(
        run_id="pi-run-001",
        candidate_build_id="candidate-001",
        qualification_profile_id="wake.default",
        metrics=metrics,
        threshold_policy={
            "standby_cpu_budget_pct": 25.0,
            "wake_cpu_peak_pct_max": 55.0,
            "listen_cpu_peak_pct_max": 60.0,
            "speak_cpu_peak_pct_max": 60.0,
            "startup_latency_ms_max": 5000.0,
            "peak_temp_c_max": 80.0,
            "unexpected_shutdown_count_max": 0.0,
            "telemetry_completeness_ratio_min": 0.95,
            "repeated_wake_cycles_min": 60.0,
        },
    )

    assert outcome.status == "failed"
    assert "standby_cpu_budget" in outcome.blocked_thresholds
    assert "thermal_limit" in outcome.blocked_thresholds
    assert "telemetry_completeness" in outcome.blocked_thresholds


def test_speech_release_gate_blocks_when_pi_evidence_missing() -> None:
    gate = evaluate_speech_release_gate(
        candidate_build_id="candidate-002",
        ci_replay_status="passed",
        pi_qualification_run=None,
        required_artifacts=["telemetry-summary.json", "pi-qualification.json"],
        available_artifacts=["telemetry-summary.json"],
    )
    assert isinstance(gate, SpeechReleaseGateResult)
    assert gate.gate_status == "blocked"
    assert "missing_pi4_qualification" in gate.blocked_reasons


def test_speech_release_gate_approves_when_ci_and_pi_are_green() -> None:
    pi_run = evaluate_pi_qualification_run(
        run_id="pi-run-002",
        candidate_build_id="candidate-003",
        qualification_profile_id="wake.default",
        metrics=PiQualificationMetrics(
            duration_minutes=30,
            standby_cpu_median_pct=18.0,
            wake_cpu_peak_pct=43.0,
            listen_cpu_peak_pct=39.0,
            listen_memory_mb=214.0,
            speak_cpu_peak_pct=36.0,
            speak_memory_mb=220.0,
            startup_latency_ms=3900,
            peak_temp_c=72.0,
            repeated_wake_cycles=120,
            unexpected_shutdown_count=0,
            telemetry_completeness_ratio=0.99,
        ),
        threshold_policy={
            "standby_cpu_budget_pct": 25.0,
            "wake_cpu_peak_pct_max": 55.0,
            "listen_cpu_peak_pct_max": 60.0,
            "speak_cpu_peak_pct_max": 60.0,
            "startup_latency_ms_max": 5000.0,
            "peak_temp_c_max": 80.0,
            "unexpected_shutdown_count_max": 0.0,
            "telemetry_completeness_ratio_min": 0.95,
            "repeated_wake_cycles_min": 60.0,
        },
    )
    gate = evaluate_speech_release_gate(
        candidate_build_id="candidate-003",
        ci_replay_status="passed",
        pi_qualification_run=pi_run,
        required_artifacts=["telemetry-summary.json", "pi-qualification.json"],
        available_artifacts=["telemetry-summary.json", "pi-qualification.json"],
    )

    assert gate.gate_status == "approved"
    assert gate.approved_for_pilot is True
    assert gate.approved_for_field is True
    assert gate.blocked_reasons == []
