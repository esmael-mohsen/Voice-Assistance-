"""Runtime latency metric capture helpers for release baseline gating."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from core.release_models import (
    PilotVoiceUXSummary,
    SttFailureScenarioResult,
    SttTelemetryEventRecord,
    SttTelemetryRollupRecord,
)

_METRIC_LOCK = threading.Lock()

SPEECH_TELEMETRY_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "wake_accepted",
        "wake_rejected",
        "wake_missed",
        "wake_fallback_used",
        "false_accept_review",
        "false_reject_review",
        "command_confidence_distribution",
        "clarification_loop",
        "prompt_echo_suppressed",
        "clipped_retry",
        "wake_to_listen_latency",
        "listen_to_result_latency",
        "result_to_speech_start_latency",
        "recovery_reset",
    }
)
LATENCY_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "wake_to_listen_latency",
        "listen_to_result_latency",
        "result_to_speech_start_latency",
    }
)
SPEECH_TELEMETRY_SCOPES: frozenset[str] = frozenset({"live", "replay", "qualification"})
EXTERNAL_SINK_STATUSES: frozenset[str] = frozenset(
    {"not_configured", "sent", "failed", "skipped"}
)


@dataclass
class RuntimeMetricTracker:
    """Collects key runtime timing checkpoints for one session."""

    session_id: str
    wake_started_s: float | None = None
    listen_started_s: float | None = None
    result_ready_s: float | None = None
    speak_started_s: float | None = None
    metrics_ms: dict[str, float] = field(default_factory=dict)

    def record_state(self, state: str, *, timestamp_s: float) -> None:
        state_name = str(state or "").strip().lower()
        if state_name == "wake":
            self.wake_started_s = timestamp_s
        elif state_name == "listening":
            if self.wake_started_s is not None and "wake_to_listen" not in self.metrics_ms:
                self.metrics_ms["wake_to_listen"] = (timestamp_s - self.wake_started_s) * 1000.0
            if self.listen_started_s is None:
                self.listen_started_s = timestamp_s
        elif state_name == "thinking":
            if self.listen_started_s is not None and "listen_to_result" not in self.metrics_ms:
                self.metrics_ms["listen_to_result"] = (timestamp_s - self.listen_started_s) * 1000.0
            self.result_ready_s = timestamp_s
        elif state_name == "speaking":
            if self.result_ready_s is not None and "result_to_speech_start" not in self.metrics_ms:
                self.metrics_ms["result_to_speech_start"] = (timestamp_s - self.result_ready_s) * 1000.0
            if self.speak_started_s is None:
                self.speak_started_s = timestamp_s

    def snapshot(self) -> dict[str, float]:
        return {key: round(value, 3) for key, value in self.metrics_ms.items()}


@dataclass(frozen=True)
class InterruptLatencyRecord:
    measurement_id: str
    interrupt_signal_type: str
    preemption_latency_ms: int
    latency_target_bucket: str
    runtime_load_profile: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "measurement_id": self.measurement_id,
            "interrupt_signal_type": self.interrupt_signal_type,
            "preemption_latency_ms": self.preemption_latency_ms,
            "latency_target_bucket": self.latency_target_bucket,
            "runtime_load_profile": self.runtime_load_profile,
        }


@dataclass(frozen=True)
class SpeechTelemetryEventRecord:
    event_id: str
    scenario_label: str
    event_type: str
    session_id: str
    interaction_id: str
    timestamp_ms: int
    event_source: str
    outcome_status: str
    latency_ms: int | None = None
    metric_value: float | None = None
    evidence_scope: str = "live"
    persisted_locally: bool = True
    external_sink_status: str = "not_configured"
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id is required")
        if not self.scenario_label:
            raise ValueError("scenario_label is required")
        if self.event_type not in SPEECH_TELEMETRY_EVENT_TYPES:
            raise ValueError("event_type must be a supported Phase 15 telemetry event")
        if not self.session_id:
            raise ValueError("session_id is required")
        if not self.interaction_id:
            raise ValueError("interaction_id is required")
        if self.timestamp_ms < 0:
            raise ValueError("timestamp_ms must be non-negative")
        if not self.event_source:
            raise ValueError("event_source is required")
        if not self.outcome_status:
            raise ValueError("outcome_status is required")
        if self.evidence_scope not in SPEECH_TELEMETRY_SCOPES:
            raise ValueError("evidence_scope must be live, replay, or qualification")
        if self.external_sink_status not in EXTERNAL_SINK_STATUSES:
            raise ValueError("external_sink_status must be supported")
        if self.event_type in LATENCY_EVENT_TYPES:
            if self.latency_ms is None:
                raise ValueError("latency_ms is required for latency event types")
            if self.metric_value is None:
                raise ValueError("metric_value is required for latency event types")
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        if self.event_type == "command_confidence_distribution":
            if not isinstance(self.payload, dict) or not any(
                key in self.payload for key in ("distribution", "buckets", "histogram")
            ):
                raise ValueError("command_confidence_distribution requires aggregate payload data")
        if self.external_sink_status == "failed" and not self.persisted_locally:
            raise ValueError("failed external sink must retain local persistence")

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "scenario_label": self.scenario_label,
            "event_type": self.event_type,
            "session_id": self.session_id,
            "interaction_id": self.interaction_id,
            "timestamp_ms": self.timestamp_ms,
            "event_source": self.event_source,
            "outcome_status": self.outcome_status,
            "latency_ms": self.latency_ms,
            "metric_value": self.metric_value,
            "evidence_scope": self.evidence_scope,
            "persisted_locally": self.persisted_locally,
            "external_sink_status": self.external_sink_status,
            "payload": dict(self.payload),
        }


_SESSION_TRACKERS: dict[str, RuntimeMetricTracker] = {}
_INTERRUPT_LATENCY_TRACKERS: dict[str, list[InterruptLatencyRecord]] = {}
_AUDIO_QUALIFICATION_RUNS: dict[str, list[dict[str, Any]]] = {}
_SPEECH_TELEMETRY_EVENTS: dict[str, list[SpeechTelemetryEventRecord]] = {}
_STT_OBSERVABILITY_EVENTS: dict[str, list[SttTelemetryEventRecord]] = {}
_STT_FAILURE_SCENARIO_RESULTS: dict[str, list[SttFailureScenarioResult]] = {}


def classify_preemption_latency(latency_ms: int) -> str:
    if latency_ms <= 500:
        return "within_target"
    if latency_ms <= 1000:
        return "over_target"
    return "over_ceiling"


def record_runtime_state_transition(
    *,
    session_id: str,
    state: str,
    timestamp_s: float | None = None,
) -> None:
    now_s = float(timestamp_s if timestamp_s is not None else time.perf_counter())
    with _METRIC_LOCK:
        tracker = _SESSION_TRACKERS.get(session_id)
        if tracker is None:
            tracker = RuntimeMetricTracker(session_id=session_id)
            _SESSION_TRACKERS[session_id] = tracker
        tracker.record_state(state, timestamp_s=now_s)


def get_runtime_latency_metrics(session_id: str) -> dict[str, float]:
    with _METRIC_LOCK:
        tracker = _SESSION_TRACKERS.get(session_id)
        if tracker is None:
            return {}
        return tracker.snapshot()


def clear_runtime_latency_metrics(session_id: str) -> None:
    with _METRIC_LOCK:
        _SESSION_TRACKERS.pop(session_id, None)
        _INTERRUPT_LATENCY_TRACKERS.pop(session_id, None)
        _AUDIO_QUALIFICATION_RUNS.pop(session_id, None)
        _SPEECH_TELEMETRY_EVENTS.pop(session_id, None)
        _STT_OBSERVABILITY_EVENTS.pop(session_id, None)
        _STT_FAILURE_SCENARIO_RESULTS.pop(session_id, None)


def record_interrupt_preemption(
    *,
    session_id: str,
    interrupt_signal_type: str,
    preemption_latency_ms: int,
    runtime_load_profile: str = "normal",
) -> InterruptLatencyRecord:
    record = InterruptLatencyRecord(
        measurement_id=f"{session_id}-{len(_INTERRUPT_LATENCY_TRACKERS.get(session_id, [])) + 1}",
        interrupt_signal_type=str(interrupt_signal_type or "none"),
        preemption_latency_ms=max(0, int(preemption_latency_ms)),
        latency_target_bucket=classify_preemption_latency(max(0, int(preemption_latency_ms))),
        runtime_load_profile=str(runtime_load_profile or "normal"),
    )
    with _METRIC_LOCK:
        _INTERRUPT_LATENCY_TRACKERS.setdefault(session_id, []).append(record)
    return record


def get_interrupt_latency_records(session_id: str) -> list[dict[str, Any]]:
    with _METRIC_LOCK:
        records = list(_INTERRUPT_LATENCY_TRACKERS.get(session_id, ()))
    return [item.to_dict() for item in records]


def build_runtime_metric_payload(session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "metrics": get_runtime_latency_metrics(session_id),
        "interrupt_latency_records": get_interrupt_latency_records(session_id),
        "audio_qualification_runs": list(_AUDIO_QUALIFICATION_RUNS.get(session_id, ())),
        "speech_telemetry_events": get_speech_telemetry_events(session_id),
        "stt_observability_events": get_stt_observability_events(session_id),
        "stt_failure_scenarios": get_stt_failure_scenario_results(session_id),
    }


def record_audio_qualification_run(
    *,
    session_id: str,
    qualification_profile_id: str,
    capture_profile_id: str,
    recognition_path: str,
    capture_complete: bool,
    latency_ms: int,
    accuracy: float | None = None,
    demoted_enhancements: list[str] | None = None,
) -> dict[str, Any]:
    payload = {
        "qualification_profile_id": str(qualification_profile_id or "default"),
        "capture_profile_id": str(capture_profile_id or "command.default"),
        "recognition_path": str(recognition_path or "local_first"),
        "capture_complete": bool(capture_complete),
        "latency_ms": max(0, int(latency_ms)),
        "accuracy": float(accuracy) if accuracy is not None else None,
        "demoted_enhancements": list(demoted_enhancements or ()),
        "field_safe": True,
        "raw_user_content_present": False,
    }
    with _METRIC_LOCK:
        _AUDIO_QUALIFICATION_RUNS.setdefault(session_id, []).append(payload)
    return payload


def record_speech_telemetry_event(
    *,
    session_id: str,
    event: SpeechTelemetryEventRecord | dict[str, Any],
) -> dict[str, Any]:
    if isinstance(event, SpeechTelemetryEventRecord):
        record = event
    else:
        payload = dict(event)
        payload.pop("field_safe", None)
        payload.pop("raw_user_content_present", None)
        payload.setdefault("session_id", session_id)
        payload.setdefault("timestamp_ms", int(time.time() * 1000))
        record = SpeechTelemetryEventRecord(**payload)
    with _METRIC_LOCK:
        _SPEECH_TELEMETRY_EVENTS.setdefault(session_id, []).append(record)
    return record.to_dict()


def get_speech_telemetry_events(
    session_id: str,
    *,
    evidence_scope: str | None = None,
) -> list[dict[str, Any]]:
    scope_filter = str(evidence_scope).strip().lower() if evidence_scope is not None else None
    with _METRIC_LOCK:
        events = list(_SPEECH_TELEMETRY_EVENTS.get(session_id, ()))
    if scope_filter is not None:
        events = [event for event in events if event.evidence_scope == scope_filter]
    return [event.to_dict() for event in events]


def summarize_command_confidence_distribution(session_id: str) -> dict[str, int]:
    summary: dict[str, int] = {"high": 0, "medium": 0, "low": 0, "missing_confidence": 0}
    events = get_speech_telemetry_events(session_id)
    for event in events:
        if event.get("event_type") != "command_confidence_distribution":
            continue
        payload = dict(event.get("payload") or {})
        distribution = payload.get("distribution")
        if isinstance(distribution, dict):
            for key in summary:
                summary[key] += int(distribution.get(key, 0) or 0)
    return summary


def build_pilot_voice_ux_summary(
    *,
    run_id: str,
    scenario_label: str,
    journey_type: str,
    completion_status: str,
    retries_used: int,
    accepted_barge_in_count: int,
    prompt_echo_suppression_count: int,
    out_of_domain_rejection_count: int,
    fallback_or_exit_reason: str | None,
    artifact_path: str,
) -> dict[str, Any]:
    summary = PilotVoiceUXSummary(
        run_id=run_id,
        scenario_label=scenario_label,
        journey_type=journey_type,
        completion_status=completion_status,
        retries_used=max(0, int(retries_used)),
        accepted_barge_in_count=max(0, int(accepted_barge_in_count)),
        prompt_echo_suppression_count=max(0, int(prompt_echo_suppression_count)),
        out_of_domain_rejection_count=max(0, int(out_of_domain_rejection_count)),
        fallback_or_exit_reason=fallback_or_exit_reason,
        raw_utterance_present=False,
        artifact_path=str(artifact_path or ""),
    )
    return summary.to_dict()


def classify_stt_confidence_bucket(
    *,
    confidence_available: bool,
    confidence_score: float | None,
) -> str:
    if not confidence_available or confidence_score is None:
        return "missing"
    value = float(confidence_score)
    if value >= 0.82:
        return "high"
    if value >= 0.55:
        return "medium"
    return "low"


def classify_stt_latency_bucket(*, latency_ms: int) -> str:
    value = max(0, int(latency_ms))
    if value <= 1400:
        return "within_target"
    if value <= 2200:
        return "over_baseline"
    return "threshold_breach"


def classify_stt_failure_category(reason_code: str | None) -> str:
    reason = str(reason_code or "").strip().lower()
    if not reason:
        return "none"
    if "network" in reason:
        return "network"
    if "credential" in reason or "auth" in reason:
        return "credentials"
    if "quota" in reason or "rate" in reason:
        return "quota_or_rate"
    if "timeout" in reason:
        return "cloud_timeout"
    if "strict_vosk_unavailable" in reason or "fallback_unavailable" in reason:
        return "fallback_missing"
    if "microphone" in reason:
        return "microphone_timeout"
    if "clip" in reason:
        return "clipping"
    if "language_mismatch" in reason:
        return "language_mismatch"
    if "confidence" in reason or "parser_rejected" in reason:
        return "confidence_policy"
    return "unknown"


def classify_stt_recovery_outcome(decision_outcome: str | None) -> str:
    decision = str(decision_outcome or "").strip().lower()
    if decision in {"fallback", "retry", "safe_refusal", "standby"}:
        return decision
    if decision == "refuse":
        return "safe_refusal"
    if decision in {"execute", "confirm", ""}:
        return "none"
    return "standby"


def _bounded_outcome_for_event(event: SttTelemetryEventRecord) -> str:
    if event.recovery_outcome != "none":
        return event.recovery_outcome
    if event.status == "failed":
        return "standby"
    return "none"


def record_stt_observability_event(
    *,
    event: SttTelemetryEventRecord | dict[str, Any],
) -> dict[str, Any]:
    if isinstance(event, SttTelemetryEventRecord):
        record = event
    else:
        record = SttTelemetryEventRecord(**dict(event))
    with _METRIC_LOCK:
        _STT_OBSERVABILITY_EVENTS.setdefault(record.session_id, []).append(record)
    return record.to_dict()


def get_stt_observability_events(
    session_id: str,
    *,
    candidate_run_id: str | None = None,
) -> list[dict[str, Any]]:
    with _METRIC_LOCK:
        records = list(_STT_OBSERVABILITY_EVENTS.get(session_id, ()))
    if candidate_run_id is not None:
        run_id = str(candidate_run_id)
        records = [record for record in records if record.candidate_run_id == run_id]
    return [record.to_dict() for record in records]


def build_stt_telemetry_rollup(
    *,
    session_id: str,
    candidate_run_id: str,
    retention_days: int = 180,
) -> dict[str, Any]:
    records = [
        SttTelemetryEventRecord(**payload)
        for payload in get_stt_observability_events(session_id, candidate_run_id=candidate_run_id)
    ]
    event_count = len(records)
    if event_count == 0:
        rollup = SttTelemetryRollupRecord(
            rollup_id=f"{candidate_run_id}-rollup",
            candidate_run_id=candidate_run_id,
            session_count=1,
            event_count=0,
            rollout_mode_counts={},
            source_counts={},
            status_counts={},
            confidence_bucket_counts={},
            failure_category_counts={},
            recovery_outcome_counts={},
            latency_bucket_counts={},
            fallback_frequency=0.0,
            cloud_failure_frequency=0.0,
            retry_rate=0.0,
            clipping_rate=0.0,
            timeout_rate=0.0,
            arabic_failure_count=0,
            language_mismatch_rate=0.0,
            retention_days=retention_days,
        )
        return rollup.to_dict()

    def _count_by(get_key: Any) -> dict[str, int]:
        counter: dict[str, int] = {}
        for record in records:
            key = str(get_key(record))
            counter[key] = counter.get(key, 0) + 1
        return counter

    rollout_mode_counts = _count_by(lambda item: item.rollout_mode)
    source_counts = _count_by(lambda item: item.source)
    status_counts = _count_by(lambda item: item.status)
    confidence_bucket_counts = _count_by(lambda item: item.confidence_bucket)
    failure_category_counts = _count_by(lambda item: item.failure_category)
    recovery_outcome_counts = _count_by(lambda item: item.recovery_outcome)
    latency_bucket_counts = _count_by(lambda item: item.latency_bucket)

    fallback_count = sum(1 for item in records if item.recovery_outcome == "fallback")
    cloud_failures = sum(
        1
        for item in records
        if item.source == "google_cloud" and item.failure_category not in {"none"}
    )
    retry_count = sum(1 for item in records if item.recovery_outcome == "retry")
    clipping_count = sum(1 for item in records if item.failure_category == "clipping")
    timeout_count = sum(1 for item in records if item.failure_category == "cloud_timeout")
    arabic_failure_count = sum(1 for item in records if item.event_type == "arabic_failure")
    language_mismatch_count = sum(1 for item in records if item.failure_category == "language_mismatch")

    rollup = SttTelemetryRollupRecord(
        rollup_id=f"{candidate_run_id}-rollup",
        candidate_run_id=candidate_run_id,
        session_count=1,
        event_count=event_count,
        rollout_mode_counts=rollout_mode_counts,
        source_counts=source_counts,
        status_counts=status_counts,
        confidence_bucket_counts=confidence_bucket_counts,
        failure_category_counts=failure_category_counts,
        recovery_outcome_counts=recovery_outcome_counts,
        latency_bucket_counts=latency_bucket_counts,
        fallback_frequency=round(fallback_count / event_count, 4),
        cloud_failure_frequency=round(cloud_failures / event_count, 4),
        retry_rate=round(retry_count / event_count, 4),
        clipping_rate=round(clipping_count / event_count, 4),
        timeout_rate=round(timeout_count / event_count, 4),
        arabic_failure_count=arabic_failure_count,
        language_mismatch_rate=round(language_mismatch_count / event_count, 4),
        retention_days=max(1, int(retention_days)),
    )
    return rollup.to_dict()


def record_stt_failure_scenario_result(
    *,
    result: SttFailureScenarioResult | dict[str, Any],
    session_id: str | None = None,
) -> dict[str, Any]:
    if isinstance(result, SttFailureScenarioResult):
        record = result
    else:
        record = SttFailureScenarioResult(**dict(result))
    key = str(session_id or record.scenario_id.split("-", 1)[0] or "default")
    with _METRIC_LOCK:
        _STT_FAILURE_SCENARIO_RESULTS.setdefault(key, []).append(record)
    return record.to_dict()


def get_stt_failure_scenario_results(session_id: str) -> list[dict[str, Any]]:
    with _METRIC_LOCK:
        records = list(_STT_FAILURE_SCENARIO_RESULTS.get(session_id, ()))
    return [record.to_dict() for record in records]


def build_failure_scenario_from_event(
    *,
    event: SttTelemetryEventRecord,
    spoken_guidance_surface: str | None = None,
) -> dict[str, Any]:
    result = SttFailureScenarioResult(
        scenario_id=f"{event.session_id}-{event.event_id}",
        failure_category=event.failure_category,
        source=event.source,
        rollout_mode=event.rollout_mode,
        bounded_outcome=_bounded_outcome_for_event(event),
        crash_free=True,
        spoken_guidance_surface=spoken_guidance_surface,
        diagnostic_reason_code=event.reason_code,
        field_safe_metadata={
            "raw_audio_present": False,
            "raw_utterance_present": False,
            "latency_bucket": event.latency_bucket,
        },
    )
    return result.to_dict()
