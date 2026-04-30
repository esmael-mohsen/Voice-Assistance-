"""Unit tests for release latency baseline comparison rules."""

from __future__ import annotations

from core.release_gates import compare_latency_metrics, evaluate_metric_breach


def test_evaluate_metric_breach_uses_ms_or_percentage_threshold() -> None:
    breached, delta_ms, delta_pct = evaluate_metric_breach(
        current_p95_ms=900.0,
        baseline_p95_ms=700.0,
        threshold_ms=150.0,
        threshold_pct=20.0,
    )

    assert breached is True
    assert delta_ms == 200.0
    assert round(delta_pct, 2) == 28.57


def test_compare_latency_metrics_returns_results_for_required_metrics() -> None:
    current = {
        "wake_to_listen": 780.0,
        "listen_to_result": 920.0,
        "result_to_speech_start": 610.0,
    }
    baseline = {
        "wake_to_listen": 760.0,
        "listen_to_result": 900.0,
        "result_to_speech_start": 600.0,
    }
    policy = {
        "wake_to_listen": {"threshold_ms": 100.0, "threshold_pct": 15.0},
        "listen_to_result": {"threshold_ms": 100.0, "threshold_pct": 15.0},
        "result_to_speech_start": {"threshold_ms": 80.0, "threshold_pct": 15.0},
    }

    comparisons = compare_latency_metrics(
        run_id="run-001",
        current_metrics=current,
        baseline_metrics=baseline,
        threshold_policy=policy,
    )

    assert len(comparisons) == 3
    assert all(item.run_id == "run-001" for item in comparisons)
    assert all(item.metric_name in current for item in comparisons)
