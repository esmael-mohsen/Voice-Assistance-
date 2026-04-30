"""Integration tests for Phase 15 Raspberry Pi qualification release gates."""

from __future__ import annotations

import json
from pathlib import Path

from core.release_gates import evaluate_pi_qualification_run, evaluate_speech_release_gate
from core.release_models import PiQualificationMetrics

_THRESHOLDS_PATH = Path("settings/release_thresholds.json")


def _pi_threshold_policy() -> dict[str, float]:
    payload = json.loads(_THRESHOLDS_PATH.read_text(encoding="utf-8"))
    return dict(payload.get("pi_qualification", {}))


def _passing_metrics() -> PiQualificationMetrics:
    return PiQualificationMetrics(
        duration_minutes=30,
        standby_cpu_median_pct=17.2,
        wake_cpu_peak_pct=42.0,
        listen_cpu_peak_pct=38.5,
        listen_memory_mb=214.0,
        speak_cpu_peak_pct=35.1,
        speak_memory_mb=220.0,
        startup_latency_ms=3900,
        peak_temp_c=72.0,
        repeated_wake_cycles=120,
        unexpected_shutdown_count=0,
        telemetry_completeness_ratio=0.99,
    )


def test_release_gate_blocks_when_ci_replay_passes_but_pi_evidence_is_missing() -> None:
    gate = evaluate_speech_release_gate(
        candidate_build_id="candidate-15",
        ci_replay_status="passed",
        pi_qualification_run=None,
        required_artifacts=["telemetry-summary.json", "pi-qualification.json"],
        available_artifacts=["telemetry-summary.json"],
        telemetry_complete=True,
    )

    assert gate.gate_status == "blocked"
    assert gate.approved_for_pilot is False
    assert gate.approved_for_field is False
    assert "missing_pi4_qualification" in gate.blocked_reasons
    assert "missing_artifact:pi-qualification.json" in gate.blocked_reasons


def test_release_gate_blocks_when_pi_qualification_fails_thresholds() -> None:
    metrics = PiQualificationMetrics(
        duration_minutes=30,
        standby_cpu_median_pct=28.0,
        wake_cpu_peak_pct=65.0,
        listen_cpu_peak_pct=64.0,
        listen_memory_mb=214.0,
        speak_cpu_peak_pct=62.0,
        speak_memory_mb=220.0,
        startup_latency_ms=6200,
        peak_temp_c=84.0,
        repeated_wake_cycles=45,
        unexpected_shutdown_count=1,
        telemetry_completeness_ratio=0.80,
    )
    pi_run = evaluate_pi_qualification_run(
        run_id="pi-run-42",
        candidate_build_id="candidate-15",
        qualification_profile_id="wake.default",
        metrics=metrics,
        threshold_policy=_pi_threshold_policy(),
        evidence_refs={"telemetry_summary": "artifacts/run-42/speech/telemetry-summary.json"},
    )
    gate = evaluate_speech_release_gate(
        candidate_build_id="candidate-15",
        ci_replay_status="passed",
        pi_qualification_run=pi_run,
        required_artifacts=["telemetry-summary.json", "pi-qualification.json"],
        available_artifacts=["telemetry-summary.json", "pi-qualification.json"],
        telemetry_complete=True,
    )

    assert pi_run.status == "failed"
    assert gate.gate_status == "blocked"
    assert gate.pi_hardware_status == "failed"
    assert gate.latest_pi_run_id == "pi-run-42"
    assert "pi4_qualification_failed" in gate.blocked_reasons


def test_release_gate_approves_when_ci_and_pi_qualification_both_pass() -> None:
    pi_run = evaluate_pi_qualification_run(
        run_id="pi-run-43",
        candidate_build_id="candidate-16",
        qualification_profile_id="wake.default",
        metrics=_passing_metrics(),
        threshold_policy=_pi_threshold_policy(),
        evidence_refs={
            "telemetry_summary": "artifacts/run-43/speech/telemetry-summary.json",
            "startup_doc": "docs/release/startup.md",
        },
    )
    gate = evaluate_speech_release_gate(
        candidate_build_id="candidate-16",
        ci_replay_status="passed",
        pi_qualification_run=pi_run,
        required_artifacts=["telemetry-summary.json", "pi-qualification.json"],
        available_artifacts=["telemetry-summary.json", "pi-qualification.json"],
        telemetry_complete=True,
        success_criteria_failures=[],
    )

    assert pi_run.status == "passed"
    assert gate.gate_status == "approved"
    assert gate.approved_for_pilot is True
    assert gate.approved_for_field is True
    assert gate.pi_hardware_status == "passed"
    assert gate.blocked_reasons == []


def test_pi_qualification_blocks_when_stt_recognition_latency_or_memory_budgets_are_exceeded() -> None:
    metrics = PiQualificationMetrics(
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
        wake_latency_p95_ms=2000,
        command_recognition_latency_p95_ms=3400,
        fallback_latency_p95_ms=4100,
        cloud_path_memory_mb=400.0,
        fallback_path_memory_mb=420.0,
    )
    pi_run = evaluate_pi_qualification_run(
        run_id="pi-run-44",
        candidate_build_id="candidate-17",
        qualification_profile_id="wake.default",
        metrics=metrics,
        threshold_policy=_pi_threshold_policy(),
    )

    assert pi_run.status == "failed"
    assert "wake_latency_p95" in pi_run.blocked_thresholds
    assert "command_recognition_latency_p95" in pi_run.blocked_thresholds
    assert "fallback_latency_p95" in pi_run.blocked_thresholds
    assert "cloud_path_memory" in pi_run.blocked_thresholds
    assert "fallback_path_memory" in pi_run.blocked_thresholds
