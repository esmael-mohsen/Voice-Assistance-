"""Release quality gate orchestration and baseline comparison logic."""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import replace
from typing import Callable

from core.release_journey_checks import run_journey_validation
from core.release_lifecycle_checks import run_lifecycle_validation
from core.release_localization import run_localization_validation
from core.release_models import (
    GateExecutionResult,
    LatencyComparisonResult,
    PiQualificationMetrics,
    PiQualificationRunRecord,
    ReleaseChecklistRecord,
    SpeechReleaseGateResult,
    SttReleaseGateResult,
    SttRolloutModeState,
    ReleaseValidationRun,
    REQUIRED_LATENCY_METRICS,
    utc_now,
)
from core.release_override import OverrideGovernanceService

RELEASE_GATE_ORDER: tuple[str, ...] = (
    "compile",
    "unit_tests",
    "integration_tests",
    "smoke_tests",
    "lint",
    "lifecycle_validation",
    "journey_validation",
    "localization_validation",
    "baseline_compare",
    "checklist_validation",
)

BLOCKING_GATES: frozenset[str] = frozenset(RELEASE_GATE_ORDER)
GateHandler = Callable[[ReleaseValidationRun], GateExecutionResult]
ROLLOUT_MODE_ORDER: dict[str, int] = {
    "shadow": 0,
    "wake_only": 1,
    "commands_low_risk": 2,
    "full_cloud_primary": 3,
    "rollback": 4,
}


def _threshold_float(policy: dict[str, float], *keys: str) -> float | None:
    for key in keys:
        if key in policy:
            return float(policy[key])
    return None


def evaluate_metric_breach(
    *,
    current_p95_ms: float,
    baseline_p95_ms: float,
    threshold_ms: float,
    threshold_pct: float,
) -> tuple[bool, float, float]:
    delta_ms = float(current_p95_ms) - float(baseline_p95_ms)
    if baseline_p95_ms <= 0:
        delta_pct = 100.0 if current_p95_ms > 0 else 0.0
    else:
        delta_pct = (delta_ms / baseline_p95_ms) * 100.0
    breached = delta_ms > float(threshold_ms) or delta_pct > float(threshold_pct)
    return breached, round(delta_ms, 3), round(delta_pct, 3)


def compare_latency_metrics(
    *,
    run_id: str,
    current_metrics: dict[str, float],
    baseline_metrics: dict[str, float],
    threshold_policy: dict[str, dict[str, float]],
) -> list[LatencyComparisonResult]:
    comparisons: list[LatencyComparisonResult] = []
    for metric_name in REQUIRED_LATENCY_METRICS:
        policy = threshold_policy.get(metric_name, {})
        threshold_ms = float(policy.get("threshold_ms", 0.0))
        threshold_pct = float(policy.get("threshold_pct", 0.0))
        if metric_name not in current_metrics or metric_name not in baseline_metrics:
            comparisons.append(
                LatencyComparisonResult(
                    comparison_id=f"{run_id}-{metric_name}",
                    run_id=run_id,
                    metric_name=metric_name,
                    current_p95_ms=float(current_metrics.get(metric_name, 0.0)),
                    baseline_p95_ms=float(baseline_metrics.get(metric_name, 0.0)),
                    delta_ms=0.0,
                    delta_pct=0.0,
                    threshold_ms=threshold_ms,
                    threshold_pct=threshold_pct,
                    breached=True,
                    decision_reason="Missing required metric or baseline value.",
                )
            )
            continue

        breached, delta_ms, delta_pct = evaluate_metric_breach(
            current_p95_ms=float(current_metrics[metric_name]),
            baseline_p95_ms=float(baseline_metrics[metric_name]),
            threshold_ms=threshold_ms,
            threshold_pct=threshold_pct,
        )
        comparisons.append(
            LatencyComparisonResult(
                comparison_id=f"{run_id}-{metric_name}",
                run_id=run_id,
                metric_name=metric_name,
                current_p95_ms=float(current_metrics[metric_name]),
                baseline_p95_ms=float(baseline_metrics[metric_name]),
                delta_ms=delta_ms,
                delta_pct=delta_pct,
                threshold_ms=threshold_ms,
                threshold_pct=threshold_pct,
                breached=breached,
                decision_reason=(
                    "Exceeded approved per-metric threshold."
                    if breached
                    else "Within approved per-metric threshold."
                ),
            )
        )
    return comparisons


def build_baseline_gate_result(comparisons: list[LatencyComparisonResult]) -> GateExecutionResult:
    breached = [item for item in comparisons if item.breached]
    if breached:
        names = ", ".join(item.metric_name for item in breached)
        return GateExecutionResult(
            gate_name="baseline_compare",
            status="failed",
            is_blocking=True,
            duration_ms=0,
            summary=f"Threshold breached for: {names}",
            failure_code="baseline_threshold_breach",
        )
    return GateExecutionResult(
        gate_name="baseline_compare",
        status="passed",
        is_blocking=True,
        duration_ms=0,
        summary="All required latency metrics are within approved thresholds.",
    )


def validate_release_checklist(checklist: ReleaseChecklistRecord) -> GateExecutionResult:
    if checklist.is_passed:
        return GateExecutionResult(
            gate_name="checklist_validation",
            status="passed",
            is_blocking=True,
            duration_ms=0,
            summary="Release checklist is complete.",
        )
    failed_items = ", ".join(checklist.failed_items())
    return GateExecutionResult(
        gate_name="checklist_validation",
        status="failed",
        is_blocking=True,
        duration_ms=0,
        summary=f"Checklist has failed items: {failed_items}",
        failure_code="checklist_incomplete",
    )


def evaluate_pi_qualification_run(
    *,
    run_id: str,
    candidate_build_id: str,
    qualification_profile_id: str,
    metrics: PiQualificationMetrics | dict[str, float | int],
    threshold_policy: dict[str, float] | None = None,
    evidence_refs: dict[str, str] | None = None,
) -> PiQualificationRunRecord:
    metric_payload: PiQualificationMetrics
    if isinstance(metrics, PiQualificationMetrics):
        metric_payload = metrics
    else:
        metric_payload = PiQualificationMetrics(**metrics)

    policy = dict(threshold_policy or {})
    blocked_thresholds: list[str] = []

    standby_cpu_budget = _threshold_float(policy, "standby_cpu_budget_pct", "standby_cpu_median_pct_max")
    if standby_cpu_budget is not None and metric_payload.standby_cpu_median_pct > standby_cpu_budget:
        blocked_thresholds.append("standby_cpu_budget")

    wake_cpu_budget = _threshold_float(policy, "wake_cpu_peak_pct_max")
    if wake_cpu_budget is not None and metric_payload.wake_cpu_peak_pct > wake_cpu_budget:
        blocked_thresholds.append("wake_cpu_budget")

    listen_cpu_budget = _threshold_float(policy, "listen_cpu_peak_pct_max")
    if listen_cpu_budget is not None and metric_payload.listen_cpu_peak_pct > listen_cpu_budget:
        blocked_thresholds.append("listen_cpu_budget")

    speak_cpu_budget = _threshold_float(policy, "speak_cpu_peak_pct_max")
    if speak_cpu_budget is not None and metric_payload.speak_cpu_peak_pct > speak_cpu_budget:
        blocked_thresholds.append("speak_cpu_budget")

    startup_latency_budget = _threshold_float(policy, "startup_latency_ms_max")
    if startup_latency_budget is not None and metric_payload.startup_latency_ms > startup_latency_budget:
        blocked_thresholds.append("startup_latency_budget")
    wake_latency_budget = _threshold_float(policy, "wake_latency_p95_ms_max")
    if wake_latency_budget is not None and metric_payload.wake_latency_p95_ms > wake_latency_budget:
        blocked_thresholds.append("wake_latency_p95")
    command_latency_budget = _threshold_float(policy, "command_recognition_latency_p95_ms_max")
    if (
        command_latency_budget is not None
        and metric_payload.command_recognition_latency_p95_ms > command_latency_budget
    ):
        blocked_thresholds.append("command_recognition_latency_p95")
    fallback_latency_budget = _threshold_float(policy, "fallback_latency_p95_ms_max")
    if fallback_latency_budget is not None and metric_payload.fallback_latency_p95_ms > fallback_latency_budget:
        blocked_thresholds.append("fallback_latency_p95")
    cloud_memory_budget = _threshold_float(policy, "cloud_path_memory_mb_max")
    if cloud_memory_budget is not None and metric_payload.cloud_path_memory_mb > cloud_memory_budget:
        blocked_thresholds.append("cloud_path_memory")
    fallback_memory_budget = _threshold_float(policy, "fallback_path_memory_mb_max")
    if fallback_memory_budget is not None and metric_payload.fallback_path_memory_mb > fallback_memory_budget:
        blocked_thresholds.append("fallback_path_memory")

    thermal_limit = _threshold_float(policy, "peak_temp_c_max", "thermal_limit_c")
    if thermal_limit is not None and metric_payload.peak_temp_c > thermal_limit:
        blocked_thresholds.append("thermal_limit")

    unexpected_shutdown_budget = _threshold_float(policy, "unexpected_shutdown_count_max")
    if (
        unexpected_shutdown_budget is not None
        and metric_payload.unexpected_shutdown_count > unexpected_shutdown_budget
    ):
        blocked_thresholds.append("unexpected_shutdown_budget")

    telemetry_min = _threshold_float(policy, "telemetry_completeness_ratio_min")
    if telemetry_min is not None and metric_payload.telemetry_completeness_ratio < telemetry_min:
        blocked_thresholds.append("telemetry_completeness")

    wake_cycles_min = _threshold_float(policy, "repeated_wake_cycles_min")
    if wake_cycles_min is not None and metric_payload.repeated_wake_cycles < wake_cycles_min:
        blocked_thresholds.append("repeated_wake_cycles")

    status = "failed" if blocked_thresholds else "passed"
    return PiQualificationRunRecord(
        run_id=run_id,
        candidate_build_id=candidate_build_id,
        qualification_profile_id=qualification_profile_id,
        metrics=metric_payload,
        status=status,
        blocked_thresholds=blocked_thresholds,
        evidence_refs=dict(evidence_refs or {}),
    )


def evaluate_speech_release_gate(
    *,
    candidate_build_id: str,
    ci_replay_status: str,
    pi_qualification_run: PiQualificationRunRecord | None,
    required_artifacts: list[str] | tuple[str, ...] | None = None,
    available_artifacts: list[str] | tuple[str, ...] | None = None,
    telemetry_complete: bool = True,
    success_criteria_failures: list[str] | tuple[str, ...] | None = None,
) -> SpeechReleaseGateResult:
    blocked_reasons: list[str] = []
    replay_status = str(ci_replay_status or "failed")
    criteria_failures = list(success_criteria_failures or ())

    if replay_status != "passed":
        blocked_reasons.append("ci_replay_failed")

    pi_hardware_status = "missing"
    latest_pi_run_id: str | None = None
    if pi_qualification_run is None:
        blocked_reasons.append("missing_pi4_qualification")
    else:
        latest_pi_run_id = pi_qualification_run.run_id
        pi_hardware_status = "passed" if pi_qualification_run.status == "passed" else "failed"
        if pi_hardware_status != "passed":
            blocked_reasons.append("pi4_qualification_failed")

    required = list(required_artifacts or ())
    available = set(available_artifacts or ())
    missing_artifacts = sorted(item for item in required if item not in available)
    if missing_artifacts:
        blocked_reasons.extend(f"missing_artifact:{name}" for name in missing_artifacts)

    if not telemetry_complete:
        blocked_reasons.append("telemetry_incomplete")

    if criteria_failures:
        blocked_reasons.append("success_criteria_failed")

    approved_for_pilot = len(blocked_reasons) == 0 and pi_hardware_status == "passed"
    approved_for_field = approved_for_pilot
    gate_status = "approved" if approved_for_pilot else "blocked"

    return SpeechReleaseGateResult(
        candidate_build_id=candidate_build_id,
        ci_replay_status=replay_status,
        pi_hardware_status=pi_hardware_status,
        latest_pi_run_id=latest_pi_run_id,
        gate_status=gate_status,
        approved_for_pilot=approved_for_pilot,
        approved_for_field=approved_for_field,
        blocked_reasons=blocked_reasons,
        payload={
            "telemetry_complete": bool(telemetry_complete),
            "required_artifacts": required,
            "missing_artifacts": missing_artifacts,
            "success_criteria_failures": criteria_failures,
        },
    )


def evaluate_rollout_mode_state(
    *,
    requested_mode: str,
    effective_mode: str,
    rollback_override_active: bool,
    rollback_reason_code: str | None = None,
    field_validation_complete: bool = False,
    user_visible_behavior_changed: bool = False,
) -> SttRolloutModeState:
    state = SttRolloutModeState(
        requested_mode=requested_mode,  # type: ignore[arg-type]
        effective_mode=effective_mode,  # type: ignore[arg-type]
        rollback_override_active=rollback_override_active,
        rollback_reason_code=rollback_reason_code,
        field_validation_complete=field_validation_complete,
        user_visible_behavior_changed=user_visible_behavior_changed,
    )
    if not rollback_override_active and effective_mode != "rollback":
        requested_rank = ROLLOUT_MODE_ORDER.get(requested_mode, -1)
        effective_rank = ROLLOUT_MODE_ORDER.get(effective_mode, -1)
        if effective_rank < requested_rank:
            raise ValueError("effective rollout mode cannot regress below requested mode without rollback")
    return state


def evaluate_stt_rollout_release_gate(
    *,
    candidate_run_id: str,
    rollout_state: SttRolloutModeState,
    cloud_configuration_ok: bool,
    strict_fallback_ok: bool,
    wake_fallback_ok: bool,
    protected_command_ok: bool,
    bilingual_regression_ok: bool,
    bounded_recovery_ok: bool,
    pi4_qualification_ok: bool,
    pocketsphinx_default_candidate_count: int,
    pocketsphinx_default_invocation_count: int,
    required_evidence_refs: list[str] | None = None,
) -> SttReleaseGateResult:
    blocked_reasons: list[str] = []
    if not cloud_configuration_ok:
        blocked_reasons.append("missing_cloud_configuration")
    if not strict_fallback_ok:
        blocked_reasons.append("missing_strict_fallback")
    if not wake_fallback_ok:
        blocked_reasons.append("unsafe_wake_fallback")
    if not protected_command_ok:
        blocked_reasons.append("protected_command_regression")
    if not bilingual_regression_ok:
        blocked_reasons.append("bilingual_regression")
    if not bounded_recovery_ok:
        blocked_reasons.append("bounded_recovery_regression")
    if not pi4_qualification_ok:
        blocked_reasons.append("pi4_qualification_failed_or_missing")
    if pocketsphinx_default_candidate_count > 0:
        blocked_reasons.append("default_pocketsphinx_candidates_detected")
    if pocketsphinx_default_invocation_count > 0:
        blocked_reasons.append("default_pocketsphinx_invocations_detected")
    if rollout_state.requested_mode == "shadow" and rollout_state.user_visible_behavior_changed:
        blocked_reasons.append("shadow_mode_user_visible_regression")

    approved = len(blocked_reasons) == 0
    return SttReleaseGateResult(
        candidate_run_id=candidate_run_id,
        gate_status="approved" if approved else "blocked",
        approved_for_pilot=approved,
        approved_for_field=approved,
        blocked_reasons=blocked_reasons,
        payload={
            "requested_mode": rollout_state.requested_mode,
            "effective_mode": rollout_state.effective_mode,
            "rollback_override_active": rollout_state.rollback_override_active,
            "rollback_reason_code": rollout_state.rollback_reason_code,
            "required_evidence_refs": list(required_evidence_refs or ()),
            "pocketsphinx_default_candidate_count": pocketsphinx_default_candidate_count,
            "pocketsphinx_default_invocation_count": pocketsphinx_default_invocation_count,
        },
    )


def _command_gate_result(
    *,
    gate_name: str,
    command: list[str],
) -> GateExecutionResult:
    start = time.perf_counter()
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    duration_ms = int((time.perf_counter() - start) * 1000)
    if completed.returncode == 0:
        return GateExecutionResult(
            gate_name=gate_name,
            status="passed",
            is_blocking=True,
            duration_ms=duration_ms,
            summary=f"{gate_name} succeeded.",
        )
    return GateExecutionResult(
        gate_name=gate_name,
        status="failed",
        is_blocking=True,
        duration_ms=duration_ms,
        summary=completed.stdout[-400:] if completed.stdout else completed.stderr[-400:],
        failure_code=f"{gate_name}_failed",
    )


def default_command_gate_handlers() -> dict[str, GateHandler]:
    python_executable = sys.executable
    return {
        "compile": lambda _run: _command_gate_result(
            gate_name="compile",
            command=[python_executable, "-m", "compileall", "main.py", "core", "settings", "tts", "ui", "tests"],
        ),
        "unit_tests": lambda _run: _command_gate_result(
            gate_name="unit_tests",
            command=[python_executable, "-m", "pytest", "tests/unit", "-q"],
        ),
        "integration_tests": lambda _run: _command_gate_result(
            gate_name="integration_tests",
            command=[python_executable, "-m", "pytest", "tests/integration", "-q"],
        ),
        "smoke_tests": lambda _run: _command_gate_result(
            gate_name="smoke_tests",
            command=[python_executable, "-m", "pytest", "tests/smoke", "-q"],
        ),
        "lint": lambda _run: _command_gate_result(
            gate_name="lint",
            command=[python_executable, "-m", "ruff", "check", "."],
        ),
    }


def build_release_story_gate_handlers(
    *,
    observed_lifecycle_states: list[str] | None = None,
    journey_results: dict[str, bool] | None = None,
    localization_catalog: dict[str, dict[str, str]] | None = None,
    localization_surface_bindings: list[dict[str, object]] | None = None,
    baseline_comparisons: list[LatencyComparisonResult] | None = None,
    checklist: ReleaseChecklistRecord | None = None,
) -> dict[str, GateHandler]:
    lifecycle_states = list(observed_lifecycle_states or [])
    journeys = dict(journey_results or {})
    catalog = dict(localization_catalog or {})
    surface_bindings_override = list(localization_surface_bindings or [])
    comparisons = list(baseline_comparisons or [])
    handlers: dict[str, GateHandler] = {
        "lifecycle_validation": lambda _run: run_lifecycle_validation(lifecycle_states),
        "journey_validation": lambda _run: run_journey_validation(journeys),
        "localization_validation": lambda _run: run_localization_validation(
            catalog=catalog,
            surface_bindings_override=surface_bindings_override,
        )[0],
        "baseline_compare": lambda _run: build_baseline_gate_result(comparisons),
    }
    if checklist is not None:
        handlers["checklist_validation"] = lambda _run: validate_release_checklist(checklist)
    return handlers


class ReleaseGateRunner:
    """Executes ordered release gates and applies blocking/override semantics."""

    def __init__(
        self,
        *,
        gate_handlers: dict[str, GateHandler] | None = None,
        governance: OverrideGovernanceService | None = None,
    ) -> None:
        self.gate_handlers: dict[str, GateHandler] = dict(gate_handlers or {})
        self.governance = governance

    def run(
        self,
        run: ReleaseValidationRun,
        *,
        requested_gates: list[str] | tuple[str, ...] | None = None,
        fail_fast: bool = True,
    ) -> ReleaseValidationRun:
        gate_order = tuple(requested_gates or RELEASE_GATE_ORDER)

        for gate_name in gate_order:
            result = self._execute_gate(run, gate_name)

            if (
                result.status == "failed"
                and result.is_blocking
                and self.governance
                and self.governance.is_override_active(run.override_record)
            ):
                result = replace(
                    result,
                    status="overridden",
                    summary=f"{result.summary} (approved emergency override applied)",
                )
                run.status = "override_pending"

            run.add_gate_result(result)

            if result.status == "failed" and result.is_blocking:
                if fail_fast:
                    break

        completed_at = utc_now()
        if run.status == "failed":
            run.finalize(status="failed", completed_at=completed_at)
            return run
        if run.status == "override_pending":
            run.finalize(status="approved_with_override", completed_at=completed_at)
            return run
        run.finalize(status="passed", completed_at=completed_at)
        return run

    def _execute_gate(self, run: ReleaseValidationRun, gate_name: str) -> GateExecutionResult:
        handler = self.gate_handlers.get(gate_name)
        if handler is None:
            return GateExecutionResult(
                gate_name=gate_name,
                status="failed",
                is_blocking=gate_name in BLOCKING_GATES,
                duration_ms=0,
                summary=f"No gate handler registered for '{gate_name}'.",
                failure_code="missing_gate_handler",
            )
        start = time.perf_counter()
        try:
            result = handler(run)
        except Exception as exc:  # noqa: BLE001
            duration_ms = int((time.perf_counter() - start) * 1000)
            return GateExecutionResult(
                gate_name=gate_name,
                status="failed",
                is_blocking=gate_name in BLOCKING_GATES,
                duration_ms=duration_ms,
                summary=f"{gate_name} raised an exception: {exc}",
                failure_code="gate_exception",
            )

        if result.gate_name != gate_name:
            result = replace(result, gate_name=gate_name)
        if result.duration_ms == 0:
            result = replace(result, duration_ms=int((time.perf_counter() - start) * 1000))
        return result
