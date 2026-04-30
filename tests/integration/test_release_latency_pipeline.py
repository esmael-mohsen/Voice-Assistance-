"""Integration tests for latency baseline comparison gate."""

from __future__ import annotations

from core.release_gates import build_baseline_gate_result, compare_latency_metrics


def test_latency_pipeline_fails_when_any_metric_breaches_threshold() -> None:
    comparisons = compare_latency_metrics(
        run_id="run-001",
        current_metrics={
            "wake_to_listen": 910.0,
            "listen_to_result": 900.0,
            "result_to_speech_start": 620.0,
        },
        baseline_metrics={
            "wake_to_listen": 760.0,
            "listen_to_result": 880.0,
            "result_to_speech_start": 600.0,
        },
        threshold_policy={
            "wake_to_listen": {"threshold_ms": 80.0, "threshold_pct": 12.0},
            "listen_to_result": {"threshold_ms": 100.0, "threshold_pct": 20.0},
            "result_to_speech_start": {"threshold_ms": 80.0, "threshold_pct": 20.0},
        },
    )

    gate_result = build_baseline_gate_result(comparisons)

    assert gate_result.status == "failed"
    assert gate_result.failure_code == "baseline_threshold_breach"


def test_latency_pipeline_passes_when_all_metrics_within_threshold() -> None:
    comparisons = compare_latency_metrics(
        run_id="run-002",
        current_metrics={
            "wake_to_listen": 790.0,
            "listen_to_result": 910.0,
            "result_to_speech_start": 610.0,
        },
        baseline_metrics={
            "wake_to_listen": 760.0,
            "listen_to_result": 900.0,
            "result_to_speech_start": 600.0,
        },
        threshold_policy={
            "wake_to_listen": {"threshold_ms": 100.0, "threshold_pct": 15.0},
            "listen_to_result": {"threshold_ms": 100.0, "threshold_pct": 15.0},
            "result_to_speech_start": {"threshold_ms": 80.0, "threshold_pct": 15.0},
        },
    )

    gate_result = build_baseline_gate_result(comparisons)
    assert gate_result.status == "passed"
