"""Shared data models for release quality gates and governance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

RunStatus = Literal["running", "passed", "failed", "override_pending", "approved_with_override"]
GateStatus = Literal["passed", "failed", "skipped", "overridden"]
ChecklistStatus = Literal["pass", "fail", "n/a"]
RemediationStatus = Literal["open", "closed", "breached", "rejected"]
PurgeStatus = Literal["active", "archived", "purged"]
PiQualificationStatus = Literal["passed", "failed"]
CIReplayStatus = Literal["passed", "failed"]
PiHardwareStatus = Literal["passed", "failed", "missing"]
SpeechGateStatus = Literal["approved", "blocked"]
SttRolloutMode = Literal["shadow", "wake_only", "commands_low_risk", "full_cloud_primary", "rollback"]
SttFailureCategory = Literal[
    "none",
    "network",
    "credentials",
    "quota_or_rate",
    "cloud_timeout",
    "fallback_missing",
    "microphone_timeout",
    "clipping",
    "language_mismatch",
    "confidence_policy",
    "unknown",
]
SttRecoveryOutcome = Literal["none", "fallback", "retry", "safe_refusal", "standby"]
SttReleaseGateStatus = Literal["approved", "blocked"]

VALID_RUN_STATUSES: frozenset[str] = frozenset(
    {"running", "passed", "failed", "override_pending", "approved_with_override"}
)
VALID_GATE_STATUSES: frozenset[str] = frozenset({"passed", "failed", "skipped", "overridden"})
VALID_PI_QUALIFICATION_STATUSES: frozenset[str] = frozenset({"passed", "failed"})
VALID_CI_REPLAY_STATUSES: frozenset[str] = frozenset({"passed", "failed"})
VALID_PI_HARDWARE_STATUSES: frozenset[str] = frozenset({"passed", "failed", "missing"})
VALID_SPEECH_GATE_STATUSES: frozenset[str] = frozenset({"approved", "blocked"})
VALID_STT_ROLLOUT_MODES: frozenset[str] = frozenset(
    {"shadow", "wake_only", "commands_low_risk", "full_cloud_primary", "rollback"}
)
VALID_STT_FAILURE_CATEGORIES: frozenset[str] = frozenset(
    {
        "none",
        "network",
        "credentials",
        "quota_or_rate",
        "cloud_timeout",
        "fallback_missing",
        "microphone_timeout",
        "clipping",
        "language_mismatch",
        "confidence_policy",
        "unknown",
    }
)
VALID_STT_RECOVERY_OUTCOMES: frozenset[str] = frozenset({"none", "fallback", "retry", "safe_refusal", "standby"})
VALID_STT_RELEASE_GATE_STATUSES: frozenset[str] = frozenset({"approved", "blocked"})
REQUIRED_LATENCY_METRICS: tuple[str, ...] = (
    "wake_to_listen",
    "listen_to_result",
    "result_to_speech_start",
)
VALID_PILOT_VOICE_UX_COMPLETION_STATUSES: frozenset[str] = frozenset(
    {"completed", "safe_default_continuation", "graceful_exit", "failed"}
)
BASE_REQUIRED_ARTIFACT_KINDS: tuple[str, ...] = (
    "gate_summary",
    "test_results",
    "diagnostic_artifact_index",
)
CONDITIONAL_ARTIFACT_KINDS: tuple[str, ...] = (
    "checklist_evidence",
    "baseline_comparison",
    "localization_results",
    "override_record",
)
REQUIRED_ARTIFACT_KINDS: tuple[str, ...] = BASE_REQUIRED_ARTIFACT_KINDS


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ArtifactEntry:
    kind: str
    path: str
    checksum: str
    available: bool = True
    source: Literal["generated", "linked", "missing"] = "generated"
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.kind:
            raise ValueError("artifact kind is required")
        if self.source not in {"generated", "linked", "missing"}:
            raise ValueError("unsupported artifact source")
        if self.available:
            if not self.path:
                raise ValueError("artifact path is required")
            if not self.checksum:
                raise ValueError("artifact checksum is required")
        else:
            if self.source != "missing":
                raise ValueError("unavailable artifacts must use source='missing'")
            if not self.notes:
                raise ValueError("notes are required when an artifact is unavailable")


@dataclass(frozen=True)
class ReleaseValidationContext:
    python_executable: str
    working_directory: str
    invoked_command: str
    started_at: datetime
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.python_executable:
            raise ValueError("python_executable is required")
        if not self.working_directory:
            raise ValueError("working_directory is required")
        if not self.invoked_command:
            raise ValueError("invoked_command is required")


@dataclass
class GateExecutionResult:
    gate_name: str
    status: GateStatus
    is_blocking: bool
    duration_ms: int
    summary: str
    failure_code: str | None = None
    evidence_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.gate_name:
            raise ValueError("gate_name is required")
        if self.status not in VALID_GATE_STATUSES:
            raise ValueError(f"unsupported gate status: {self.status}")
        if self.duration_ms < 0:
            raise ValueError("duration_ms must be non-negative")
        if self.status == "failed" and not self.failure_code:
            raise ValueError("failure_code is required when gate status is failed")


@dataclass
class LatencyComparisonResult:
    comparison_id: str
    run_id: str
    metric_name: str
    current_p95_ms: float
    baseline_p95_ms: float
    delta_ms: float
    delta_pct: float
    threshold_ms: float
    threshold_pct: float
    breached: bool
    decision_reason: str

    def __post_init__(self) -> None:
        if self.metric_name not in REQUIRED_LATENCY_METRICS:
            raise ValueError(f"unsupported metric name: {self.metric_name}")


@dataclass
class ReleaseChecklistRecord:
    checklist_id: str
    run_id: str
    offline_behavior_status: ChecklistStatus
    emergency_control_status: ChecklistStatus
    audio_permission_status: ChecklistStatus
    crash_recovery_status: ChecklistStatus
    completed_by: str
    completed_at: datetime
    notes: str | None = None

    def __post_init__(self) -> None:
        statuses = (
            self.offline_behavior_status,
            self.emergency_control_status,
            self.audio_permission_status,
            self.crash_recovery_status,
        )
        if any(status not in {"pass", "fail", "n/a"} for status in statuses):
            raise ValueError("invalid checklist status value")
        if not self.completed_by:
            raise ValueError("completed_by is required")

    @property
    def is_passed(self) -> bool:
        return (
            self.offline_behavior_status == "pass"
            and self.emergency_control_status == "pass"
            and self.audio_permission_status == "pass"
            and self.crash_recovery_status == "pass"
        )

    def failed_items(self) -> list[str]:
        failures: list[str] = []
        if self.offline_behavior_status != "pass":
            failures.append("offline_behavior")
        if self.emergency_control_status != "pass":
            failures.append("emergency_control")
        if self.audio_permission_status != "pass":
            failures.append("audio_permission")
        if self.crash_recovery_status != "pass":
            failures.append("crash_recovery")
        return failures


@dataclass
class EmergencyOverrideRecord:
    override_id: str
    run_id: str
    requested_by: str
    requested_at: datetime
    reason: str
    failed_blocking_gates: list[str]
    engineering_lead_approver: str | None = None
    qa_safety_approver: str | None = None
    approved_at: datetime | None = None
    remediation_due_at: datetime | None = None
    remediation_status: RemediationStatus = "open"
    remediation_closed_at: datetime | None = None
    closure_evidence_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.override_id:
            raise ValueError("override_id is required")
        if not self.run_id:
            raise ValueError("run_id is required")
        if not self.requested_by:
            raise ValueError("requested_by is required")
        if not self.reason:
            raise ValueError("reason is required")
        if not self.failed_blocking_gates:
            raise ValueError("failed_blocking_gates is required")
        if self.remediation_status not in {"open", "closed", "breached", "rejected"}:
            raise ValueError("unsupported remediation status")
        if self.approved_at and self.remediation_due_at and self.remediation_due_at < self.approved_at:
            raise ValueError("remediation_due_at must not be earlier than approved_at")

    @property
    def is_approved(self) -> bool:
        return bool(
            self.engineering_lead_approver
            and self.qa_safety_approver
            and self.approved_at
            and self.remediation_due_at
        )


@dataclass
class ValidationArtifactManifest:
    manifest_id: str
    run_id: str
    created_at: datetime
    storage_root: str
    artifact_entries: list[ArtifactEntry]
    retention_until: datetime
    purge_status: PurgeStatus = "active"

    def __post_init__(self) -> None:
        if not self.manifest_id:
            raise ValueError("manifest_id is required")
        if not self.run_id:
            raise ValueError("run_id is required")
        if not self.storage_root:
            raise ValueError("storage_root is required")
        if self.purge_status not in {"active", "archived", "purged"}:
            raise ValueError("unsupported purge_status")
        if self.retention_until <= self.created_at:
            raise ValueError("retention_until must be later than created_at")

    def missing_required_kinds(
        self,
        *,
        include_override: bool,
        expected_kinds: list[str] | tuple[str, ...] | None = None,
    ) -> list[str]:
        required = set(expected_kinds or REQUIRED_ARTIFACT_KINDS)
        if include_override and "override_record" not in required:
            required.add("override_record")
        present = {entry.kind for entry in self.artifact_entries}
        return sorted(required - present)


@dataclass(frozen=True)
class ReleaseValidationOutcome:
    run_id: str
    candidate_id: str
    commit_sha: str
    status: RunStatus
    execution_context: ReleaseValidationContext
    executed_checks: list[str]
    failed_blocking_gates: list[str]
    expected_artifact_kinds: list[str]
    artifact_references: list[ArtifactEntry]
    missing_artifact_kinds: list[str]
    final_decision_reason: str
    artifact_manifest_id: str | None = None

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id is required")
        if not self.candidate_id:
            raise ValueError("candidate_id is required")
        if not self.commit_sha:
            raise ValueError("commit_sha is required")
        if self.status not in VALID_RUN_STATUSES:
            raise ValueError(f"unsupported run status: {self.status}")
        if not self.executed_checks:
            raise ValueError("executed_checks is required")
        if not self.expected_artifact_kinds:
            raise ValueError("expected_artifact_kinds is required")
        if not self.final_decision_reason:
            raise ValueError("final_decision_reason is required")


@dataclass
class ReleaseValidationRun:
    run_id: str
    candidate_id: str
    commit_sha: str
    trigger: str
    started_at: datetime
    completed_at: datetime | None = None
    status: RunStatus = "running"
    execution_context: ReleaseValidationContext | None = None
    approved_by: str | None = None
    artifact_manifest_id: str | None = None
    gate_results: list[GateExecutionResult] = field(default_factory=list)
    latency_results: list[LatencyComparisonResult] = field(default_factory=list)
    executed_checks: list[str] = field(default_factory=list)
    expected_artifact_kinds: list[str] = field(default_factory=lambda: list(BASE_REQUIRED_ARTIFACT_KINDS))
    artifact_references: list[ArtifactEntry] = field(default_factory=list)
    missing_artifact_kinds: list[str] = field(default_factory=list)
    final_decision_reason: str | None = None
    checklist: ReleaseChecklistRecord | None = None
    override_record: EmergencyOverrideRecord | None = None

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id is required")
        if not self.candidate_id:
            raise ValueError("candidate_id is required")
        if not self.commit_sha:
            raise ValueError("commit_sha is required")
        if self.status not in VALID_RUN_STATUSES:
            raise ValueError(f"unsupported run status: {self.status}")

    def add_gate_result(self, gate_result: GateExecutionResult) -> None:
        self.gate_results.append(gate_result)
        if gate_result.gate_name not in self.executed_checks:
            self.executed_checks.append(gate_result.gate_name)
        if gate_result.status == "failed" and gate_result.is_blocking:
            self.status = "failed"

    def add_latency_result(self, comparison: LatencyComparisonResult) -> None:
        self.latency_results.append(comparison)

    def failed_blocking_gates(self) -> list[str]:
        return [
            item.gate_name
            for item in self.gate_results
            if item.is_blocking and item.status == "failed"
        ]

    def finalize(self, *, status: RunStatus, completed_at: datetime | None) -> None:
        if completed_at is None:
            raise ValueError("completed_at is required for finalization")
        if status not in VALID_RUN_STATUSES:
            raise ValueError(f"unsupported final status: {status}")
        self.status = status
        self.completed_at = completed_at
        if self.execution_context is not None:
            self.execution_context = ReleaseValidationContext(
                python_executable=self.execution_context.python_executable,
                working_directory=self.execution_context.working_directory,
                invoked_command=self.execution_context.invoked_command,
                started_at=self.execution_context.started_at,
                completed_at=completed_at,
            )
        if not self.final_decision_reason:
            failed = self.failed_blocking_gates()
            if failed:
                self.final_decision_reason = f"Blocking gate failure: {', '.join(failed)}"
            elif status == "approved_with_override":
                self.final_decision_reason = "Approved emergency override applied."
            else:
                self.final_decision_reason = "All requested release gates passed."

    def to_outcome(self) -> ReleaseValidationOutcome:
        if self.execution_context is None:
            raise ValueError("execution_context is required to build an outcome")
        return ReleaseValidationOutcome(
            run_id=self.run_id,
            candidate_id=self.candidate_id,
            commit_sha=self.commit_sha,
            status=self.status,
            execution_context=self.execution_context,
            executed_checks=list(self.executed_checks),
            failed_blocking_gates=self.failed_blocking_gates(),
            expected_artifact_kinds=list(self.expected_artifact_kinds),
            artifact_references=list(self.artifact_references),
            missing_artifact_kinds=list(self.missing_artifact_kinds),
            final_decision_reason=self.final_decision_reason or "Release run finished.",
            artifact_manifest_id=self.artifact_manifest_id,
        )


@dataclass(frozen=True)
class PiQualificationMetrics:
    duration_minutes: int
    standby_cpu_median_pct: float
    wake_cpu_peak_pct: float
    listen_cpu_peak_pct: float
    listen_memory_mb: float
    speak_cpu_peak_pct: float
    speak_memory_mb: float
    startup_latency_ms: int
    peak_temp_c: float
    repeated_wake_cycles: int
    unexpected_shutdown_count: int
    telemetry_completeness_ratio: float
    wake_latency_p95_ms: int = 0
    command_recognition_latency_p95_ms: int = 0
    fallback_latency_p95_ms: int = 0
    cloud_path_memory_mb: float = 0.0
    fallback_path_memory_mb: float = 0.0

    def __post_init__(self) -> None:
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        if self.startup_latency_ms < 0:
            raise ValueError("startup_latency_ms must be non-negative")
        if self.wake_latency_p95_ms < 0:
            raise ValueError("wake_latency_p95_ms must be non-negative")
        if self.command_recognition_latency_p95_ms < 0:
            raise ValueError("command_recognition_latency_p95_ms must be non-negative")
        if self.fallback_latency_p95_ms < 0:
            raise ValueError("fallback_latency_p95_ms must be non-negative")
        if self.repeated_wake_cycles < 0:
            raise ValueError("repeated_wake_cycles must be non-negative")
        if self.unexpected_shutdown_count < 0:
            raise ValueError("unexpected_shutdown_count must be non-negative")
        if self.telemetry_completeness_ratio < 0 or self.telemetry_completeness_ratio > 1:
            raise ValueError("telemetry_completeness_ratio must be between 0 and 1")
        non_negative_metrics = (
            self.standby_cpu_median_pct,
            self.wake_cpu_peak_pct,
            self.listen_cpu_peak_pct,
            self.listen_memory_mb,
            self.speak_cpu_peak_pct,
            self.speak_memory_mb,
            self.peak_temp_c,
            self.cloud_path_memory_mb,
            self.fallback_path_memory_mb,
        )
        if any(value < 0 for value in non_negative_metrics):
            raise ValueError("resource and thermal metrics must be non-negative")


@dataclass(frozen=True)
class PiQualificationRunRecord:
    run_id: str
    candidate_build_id: str
    qualification_profile_id: str
    metrics: PiQualificationMetrics
    status: PiQualificationStatus
    blocked_thresholds: list[str] = field(default_factory=list)
    evidence_refs: dict[str, str] = field(default_factory=dict)
    environment: str = "raspberry_pi_4"

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id is required")
        if not self.candidate_build_id:
            raise ValueError("candidate_build_id is required")
        if not self.qualification_profile_id:
            raise ValueError("qualification_profile_id is required")
        if self.environment != "raspberry_pi_4":
            raise ValueError("environment must be raspberry_pi_4")
        if self.status not in VALID_PI_QUALIFICATION_STATUSES:
            raise ValueError("status must be passed or failed")
        if self.status == "passed" and self.blocked_thresholds:
            raise ValueError("passed qualification cannot include blocked_thresholds")
        if self.status == "failed" and not self.blocked_thresholds:
            raise ValueError("failed qualification requires blocked_thresholds")

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "candidate_build_id": self.candidate_build_id,
            "qualification_profile_id": self.qualification_profile_id,
            "environment": self.environment,
            "status": self.status,
            "metrics": {
                "duration_minutes": self.metrics.duration_minutes,
                "standby_cpu_median_pct": self.metrics.standby_cpu_median_pct,
                "wake_cpu_peak_pct": self.metrics.wake_cpu_peak_pct,
                "listen_cpu_peak_pct": self.metrics.listen_cpu_peak_pct,
                "listen_memory_mb": self.metrics.listen_memory_mb,
                "speak_cpu_peak_pct": self.metrics.speak_cpu_peak_pct,
                "speak_memory_mb": self.metrics.speak_memory_mb,
                "startup_latency_ms": self.metrics.startup_latency_ms,
                "wake_latency_p95_ms": self.metrics.wake_latency_p95_ms,
                "command_recognition_latency_p95_ms": self.metrics.command_recognition_latency_p95_ms,
                "fallback_latency_p95_ms": self.metrics.fallback_latency_p95_ms,
                "peak_temp_c": self.metrics.peak_temp_c,
                "repeated_wake_cycles": self.metrics.repeated_wake_cycles,
                "unexpected_shutdown_count": self.metrics.unexpected_shutdown_count,
                "telemetry_completeness_ratio": self.metrics.telemetry_completeness_ratio,
                "cloud_path_memory_mb": self.metrics.cloud_path_memory_mb,
                "fallback_path_memory_mb": self.metrics.fallback_path_memory_mb,
            },
            "blocked_thresholds": list(self.blocked_thresholds),
            "evidence_refs": dict(self.evidence_refs),
        }


@dataclass(frozen=True)
class SpeechReleaseGateResult:
    candidate_build_id: str
    ci_replay_status: CIReplayStatus
    pi_hardware_status: PiHardwareStatus
    latest_pi_run_id: str | None
    gate_status: SpeechGateStatus
    approved_for_pilot: bool
    approved_for_field: bool
    blocked_reasons: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.candidate_build_id:
            raise ValueError("candidate_build_id is required")
        if self.ci_replay_status not in VALID_CI_REPLAY_STATUSES:
            raise ValueError("ci_replay_status must be passed or failed")
        if self.pi_hardware_status not in VALID_PI_HARDWARE_STATUSES:
            raise ValueError("pi_hardware_status must be passed, failed, or missing")
        if self.gate_status not in VALID_SPEECH_GATE_STATUSES:
            raise ValueError("gate_status must be approved or blocked")
        if self.approved_for_pilot and self.pi_hardware_status != "passed":
            raise ValueError("approved_for_pilot requires pi_hardware_status=passed")
        if self.approved_for_field and not self.approved_for_pilot:
            raise ValueError("approved_for_field requires approved_for_pilot=true")
        if self.gate_status == "blocked" and not self.blocked_reasons:
            raise ValueError("blocked gate_status requires blocked_reasons")
        if self.pi_hardware_status != "missing" and not self.latest_pi_run_id:
            raise ValueError("latest_pi_run_id is required when pi_hardware_status is not missing")


@dataclass(frozen=True)
class SttTelemetryEventRecord:
    event_id: str
    session_id: str
    candidate_run_id: str
    event_type: str
    source: str
    rollout_mode: SttRolloutMode
    status: str
    confidence_bucket: str
    failure_category: SttFailureCategory
    recovery_outcome: SttRecoveryOutcome
    latency_bucket: str
    reason_code: str
    field_safe: bool = True
    raw_audio_present: bool = False
    raw_utterance_present: bool = False

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id is required")
        if not self.session_id:
            raise ValueError("session_id is required")
        if not self.candidate_run_id:
            raise ValueError("candidate_run_id is required")
        if self.rollout_mode not in VALID_STT_ROLLOUT_MODES:
            raise ValueError("rollout_mode is unsupported")
        if self.failure_category not in VALID_STT_FAILURE_CATEGORIES:
            raise ValueError("failure_category is unsupported")
        if self.recovery_outcome not in VALID_STT_RECOVERY_OUTCOMES:
            raise ValueError("recovery_outcome is unsupported")
        if not self.field_safe:
            raise ValueError("field_safe telemetry events are required by default")
        if self.raw_audio_present or self.raw_utterance_present:
            raise ValueError("raw audio and raw utterances must not be present in default telemetry")
        if self.status == "failed" and self.failure_category == "none":
            raise ValueError("failed status requires a non-none failure_category")

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "candidate_run_id": self.candidate_run_id,
            "event_type": self.event_type,
            "source": self.source,
            "rollout_mode": self.rollout_mode,
            "status": self.status,
            "confidence_bucket": self.confidence_bucket,
            "failure_category": self.failure_category,
            "recovery_outcome": self.recovery_outcome,
            "latency_bucket": self.latency_bucket,
            "reason_code": self.reason_code,
            "field_safe": self.field_safe,
            "raw_audio_present": self.raw_audio_present,
            "raw_utterance_present": self.raw_utterance_present,
        }


@dataclass(frozen=True)
class SttTelemetryRollupRecord:
    rollup_id: str
    candidate_run_id: str
    session_count: int
    event_count: int
    rollout_mode_counts: dict[str, int]
    source_counts: dict[str, int]
    status_counts: dict[str, int]
    confidence_bucket_counts: dict[str, int]
    failure_category_counts: dict[str, int]
    recovery_outcome_counts: dict[str, int]
    latency_bucket_counts: dict[str, int]
    fallback_frequency: float
    cloud_failure_frequency: float
    retry_rate: float
    clipping_rate: float
    timeout_rate: float
    arabic_failure_count: int
    language_mismatch_rate: float
    retention_days: int = 180
    field_safe: bool = True
    evidence_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.rollup_id:
            raise ValueError("rollup_id is required")
        if not self.candidate_run_id:
            raise ValueError("candidate_run_id is required")
        if self.session_count < 0 or self.event_count < 0:
            raise ValueError("session_count and event_count must be non-negative")
        if self.retention_days <= 0:
            raise ValueError("retention_days must be positive")
        if not self.field_safe:
            raise ValueError("rollups must remain field-safe")

    def to_dict(self) -> dict[str, Any]:
        return {
            "rollup_id": self.rollup_id,
            "candidate_run_id": self.candidate_run_id,
            "session_count": self.session_count,
            "event_count": self.event_count,
            "rollout_mode_counts": dict(self.rollout_mode_counts),
            "source_counts": dict(self.source_counts),
            "status_counts": dict(self.status_counts),
            "confidence_bucket_counts": dict(self.confidence_bucket_counts),
            "failure_category_counts": dict(self.failure_category_counts),
            "recovery_outcome_counts": dict(self.recovery_outcome_counts),
            "latency_bucket_counts": dict(self.latency_bucket_counts),
            "fallback_frequency": self.fallback_frequency,
            "cloud_failure_frequency": self.cloud_failure_frequency,
            "retry_rate": self.retry_rate,
            "clipping_rate": self.clipping_rate,
            "timeout_rate": self.timeout_rate,
            "arabic_failure_count": self.arabic_failure_count,
            "language_mismatch_rate": self.language_mismatch_rate,
            "retention_days": self.retention_days,
            "field_safe": self.field_safe,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class SttRolloutModeState:
    requested_mode: SttRolloutMode
    effective_mode: SttRolloutMode
    rollback_override_active: bool
    rollback_reason_code: str | None = None
    field_validation_complete: bool = False
    user_visible_behavior_changed: bool = False

    def __post_init__(self) -> None:
        if self.requested_mode not in VALID_STT_ROLLOUT_MODES:
            raise ValueError("requested_mode is unsupported")
        if self.effective_mode not in VALID_STT_ROLLOUT_MODES:
            raise ValueError("effective_mode is unsupported")
        if self.rollback_override_active and self.effective_mode != "rollback":
            raise ValueError("rollback override requires effective_mode=rollback")
        if self.requested_mode == "shadow" and self.user_visible_behavior_changed:
            raise ValueError("shadow mode must not change user-visible behavior")

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_mode": self.requested_mode,
            "effective_mode": self.effective_mode,
            "rollback_override_active": self.rollback_override_active,
            "rollback_reason_code": self.rollback_reason_code,
            "field_validation_complete": self.field_validation_complete,
            "user_visible_behavior_changed": self.user_visible_behavior_changed,
        }


@dataclass(frozen=True)
class SttFailureScenarioResult:
    scenario_id: str
    failure_category: SttFailureCategory
    source: str
    rollout_mode: SttRolloutMode
    bounded_outcome: SttRecoveryOutcome
    crash_free: bool
    spoken_guidance_surface: str | None
    diagnostic_reason_code: str
    field_safe_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise ValueError("scenario_id is required")
        if self.failure_category not in VALID_STT_FAILURE_CATEGORIES:
            raise ValueError("failure_category is unsupported")
        if self.rollout_mode not in VALID_STT_ROLLOUT_MODES:
            raise ValueError("rollout_mode is unsupported")
        if self.bounded_outcome not in VALID_STT_RECOVERY_OUTCOMES:
            raise ValueError("bounded_outcome is unsupported")
        if self.bounded_outcome == "none":
            raise ValueError("failure scenarios must resolve to a bounded outcome")
        if not self.crash_free:
            raise ValueError("covered failure scenarios must be crash-free")
        if self.field_safe_metadata.get("raw_audio_present") or self.field_safe_metadata.get(
            "raw_utterance_present"
        ):
            raise ValueError("failure scenario metadata must stay field-safe")

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "failure_category": self.failure_category,
            "source": self.source,
            "rollout_mode": self.rollout_mode,
            "bounded_outcome": self.bounded_outcome,
            "crash_free": self.crash_free,
            "spoken_guidance_surface": self.spoken_guidance_surface,
            "diagnostic_reason_code": self.diagnostic_reason_code,
            "field_safe_metadata": dict(self.field_safe_metadata),
        }


@dataclass(frozen=True)
class PocketSphinxDecommissionEvidence:
    candidate_run_id: str
    default_candidate_count: int
    default_invocation_count: int
    compatibility_flag_status: str
    accuracy_baseline_includes_sphinx: bool
    compatibility_tests_present: bool = True
    documentation_status: str = "updated"

    def __post_init__(self) -> None:
        if not self.candidate_run_id:
            raise ValueError("candidate_run_id is required")
        if self.default_candidate_count < 0 or self.default_invocation_count < 0:
            raise ValueError("default counts must be non-negative")
        if self.accuracy_baseline_includes_sphinx:
            raise ValueError("production accuracy baseline must exclude PocketSphinx")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_run_id": self.candidate_run_id,
            "default_candidate_count": self.default_candidate_count,
            "default_invocation_count": self.default_invocation_count,
            "compatibility_flag_status": self.compatibility_flag_status,
            "accuracy_baseline_includes_sphinx": self.accuracy_baseline_includes_sphinx,
            "compatibility_tests_present": self.compatibility_tests_present,
            "documentation_status": self.documentation_status,
        }


@dataclass(frozen=True)
class SttReleaseGateResult:
    candidate_run_id: str
    gate_status: SttReleaseGateStatus
    approved_for_pilot: bool
    approved_for_field: bool
    blocked_reasons: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.candidate_run_id:
            raise ValueError("candidate_run_id is required")
        if self.gate_status not in VALID_STT_RELEASE_GATE_STATUSES:
            raise ValueError("gate_status is unsupported")
        if self.gate_status == "blocked" and not self.blocked_reasons:
            raise ValueError("blocked status requires blocked_reasons")
        if self.approved_for_field and not self.approved_for_pilot:
            raise ValueError("approved_for_field requires approved_for_pilot=true")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_run_id": self.candidate_run_id,
            "gate_status": self.gate_status,
            "approved_for_pilot": self.approved_for_pilot,
            "approved_for_field": self.approved_for_field,
            "blocked_reasons": list(self.blocked_reasons),
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class PilotVoiceUXSummary:
    run_id: str
    scenario_label: str
    journey_type: str
    completion_status: str
    retries_used: int
    accepted_barge_in_count: int
    prompt_echo_suppression_count: int
    out_of_domain_rejection_count: int
    fallback_or_exit_reason: str | None
    raw_utterance_present: bool
    artifact_path: str

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id is required")
        if not self.scenario_label:
            raise ValueError("scenario_label is required")
        if self.completion_status not in VALID_PILOT_VOICE_UX_COMPLETION_STATUSES:
            raise ValueError("completion_status is unsupported")
        if self.retries_used < 0:
            raise ValueError("retries_used must be non-negative")
        if self.accepted_barge_in_count < 0:
            raise ValueError("accepted_barge_in_count must be non-negative")
        if self.prompt_echo_suppression_count < 0:
            raise ValueError("prompt_echo_suppression_count must be non-negative")
        if self.out_of_domain_rejection_count < 0:
            raise ValueError("out_of_domain_rejection_count must be non-negative")
        if self.raw_utterance_present:
            raise ValueError("raw_utterance_present must remain false in default evidence")
        if self.completion_status != "completed" and not str(self.fallback_or_exit_reason or "").strip():
            raise ValueError("fallback_or_exit_reason is required when run is non-completing")
        if not self.artifact_path:
            raise ValueError("artifact_path is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "scenario_label": self.scenario_label,
            "journey_type": self.journey_type,
            "completion_status": self.completion_status,
            "retries_used": self.retries_used,
            "accepted_barge_in_count": self.accepted_barge_in_count,
            "prompt_echo_suppression_count": self.prompt_echo_suppression_count,
            "out_of_domain_rejection_count": self.out_of_domain_rejection_count,
            "fallback_or_exit_reason": self.fallback_or_exit_reason,
            "raw_utterance_present": self.raw_utterance_present,
            "artifact_path": self.artifact_path,
        }
