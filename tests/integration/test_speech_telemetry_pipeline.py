"""Integration tests for Phase 15 speech telemetry persistence and resilience."""

from __future__ import annotations

from core.release_metrics import (
    build_runtime_metric_payload,
    get_speech_telemetry_events,
    record_speech_telemetry_event,
    summarize_command_confidence_distribution,
)
from core.runtime_diagnostics import attach_speech_telemetry_fields


def test_telemetry_event_persists_locally_when_external_sink_fails() -> None:
    session_id = "session-phase15-telemetry-failed-sink"
    interaction_id = "interaction-1"
    event = attach_speech_telemetry_fields(
        {
            "payload": {
                "wake_mode": "keyword_low_power",
                "artifact_bucket": "artifacts/run-15/speech",
            }
        },
        event_id="evt-1",
        scenario_label="noisy-wake-cycle",
        event_type="wake_to_listen_latency",
        session_id=session_id,
        interaction_id=interaction_id,
        event_source="assistant_runtime",
        outcome_status="within_target",
        evidence_scope="qualification",
        persisted_locally=True,
        external_sink_status="failed",
        latency_ms=930,
        metric_value=930,
    )
    recorded = record_speech_telemetry_event(session_id=session_id, event=event)

    assert recorded["external_sink_status"] == "failed"
    assert recorded["persisted_locally"] is True
    assert recorded["event_type"] == "wake_to_listen_latency"
    assert recorded["evidence_scope"] == "qualification"


def test_replay_events_are_queryable_and_confidence_summary_is_aggregated() -> None:
    session_id = "session-phase15-replay"

    command_distribution = attach_speech_telemetry_fields(
        {
            "payload": {
                "distribution": {"high": 4, "medium": 2, "low": 1, "missing_confidence": 0},
                "artifact_bucket": "artifacts/run-15/speech",
            }
        },
        event_id="evt-2",
        scenario_label="replay-confidence",
        event_type="command_confidence_distribution",
        session_id=session_id,
        interaction_id="interaction-2",
        event_source="replay_harness",
        outcome_status="captured",
        evidence_scope="replay",
        persisted_locally=True,
        external_sink_status="not_configured",
    )
    wake_reject = attach_speech_telemetry_fields(
        {"payload": {"wake_mode": "keyword_low_power"}},
        event_id="evt-3",
        scenario_label="replay-noisy-wake",
        event_type="wake_rejected",
        session_id=session_id,
        interaction_id="interaction-3",
        event_source="replay_harness",
        outcome_status="rejected",
        evidence_scope="replay",
        persisted_locally=True,
        external_sink_status="not_configured",
    )
    live_event = attach_speech_telemetry_fields(
        {"payload": {"wake_mode": "keyword_low_power"}},
        event_id="evt-4",
        scenario_label="live-wake",
        event_type="wake_accepted",
        session_id=session_id,
        interaction_id="interaction-4",
        event_source="assistant_runtime",
        outcome_status="accepted",
        evidence_scope="live",
        persisted_locally=True,
        external_sink_status="not_configured",
    )

    record_speech_telemetry_event(session_id=session_id, event=command_distribution)
    record_speech_telemetry_event(session_id=session_id, event=wake_reject)
    record_speech_telemetry_event(session_id=session_id, event=live_event)

    replay_events = get_speech_telemetry_events(session_id, evidence_scope="replay")
    assert len(replay_events) == 2
    assert {event["event_type"] for event in replay_events} == {
        "command_confidence_distribution",
        "wake_rejected",
    }

    summary = summarize_command_confidence_distribution(session_id)
    assert summary == {"high": 4, "medium": 2, "low": 1, "missing_confidence": 0}


def test_runtime_metric_payload_includes_speech_telemetry_event_log() -> None:
    session_id = "session-phase15-runtime-payload"
    event = attach_speech_telemetry_fields(
        {"payload": {"reset_reason": "ordinary_fault_budget_reached"}},
        event_id="evt-5",
        scenario_label="recovery-reset",
        event_type="recovery_reset",
        session_id=session_id,
        interaction_id="interaction-5",
        event_source="assistant_runtime",
        outcome_status="reset",
        evidence_scope="live",
        persisted_locally=True,
        external_sink_status="not_configured",
    )
    record_speech_telemetry_event(session_id=session_id, event=event)

    payload = build_runtime_metric_payload(session_id)

    assert payload["session_id"] == session_id
    assert "speech_telemetry_events" in payload
    assert payload["speech_telemetry_events"]
    assert payload["speech_telemetry_events"][-1]["event_type"] == "recovery_reset"


def test_wake_telemetry_pipeline_records_source_markers_and_miss_classification() -> None:
    session_id = "session-phase19-wake-telemetry"
    accepted = attach_speech_telemetry_fields(
        {"payload": {"source_classification": "cloud_primary", "canonical_wake_alias": "hi egb"}},
        event_id="evt-6",
        scenario_label="phase19-cloud-wake-success",
        event_type="wake_accepted",
        session_id=session_id,
        interaction_id="interaction-6",
        event_source="assistant_runtime",
        outcome_status="accepted",
        evidence_scope="qualification",
        persisted_locally=True,
        external_sink_status="not_configured",
    )
    fallback_used = attach_speech_telemetry_fields(
        {"payload": {"source_classification": "wake_strict_vosk_fallback", "cloud_failure_reason": "cloud_network_timeout"}},
        event_id="evt-7",
        scenario_label="phase19-fallback-used",
        event_type="wake_fallback_used",
        session_id=session_id,
        interaction_id="interaction-7",
        event_source="assistant_runtime",
        outcome_status="accepted",
        evidence_scope="qualification",
        persisted_locally=True,
        external_sink_status="not_configured",
    )
    missed = attach_speech_telemetry_fields(
        {"payload": {"source_classification": "wake_strict_vosk_fallback", "reason_code": "strict_grammar_no_match"}},
        event_id="evt-8",
        scenario_label="phase19-fallback-miss",
        event_type="wake_missed",
        session_id=session_id,
        interaction_id="interaction-8",
        event_source="assistant_runtime",
        outcome_status="missed",
        evidence_scope="qualification",
        persisted_locally=True,
        external_sink_status="not_configured",
    )
    record_speech_telemetry_event(session_id=session_id, event=accepted)
    record_speech_telemetry_event(session_id=session_id, event=fallback_used)
    record_speech_telemetry_event(session_id=session_id, event=missed)

    events = get_speech_telemetry_events(session_id, evidence_scope="qualification")
    assert len(events) == 3
    assert {item["event_type"] for item in events} == {"wake_accepted", "wake_fallback_used", "wake_missed"}
    assert events[-1]["payload"]["source_classification"] == "wake_strict_vosk_fallback"
