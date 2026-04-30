# Data Model: Wake Reliability, Telemetry, and Raspberry Pi Performance Qualification

## WakePolicyProfile

- **Purpose**: Defines the approved wake behavior for one deployment profile,
  including wake thresholds, confirmation-window rules, and barge-in policy.
- **Fields**:
  - `policy_id`
  - `runtime_environment`: `production_like | development`
  - `allowed_wake_modes`
  - `alias_catalog_id`
  - `accept_threshold`
  - `weak_accept_threshold`
  - `confirmation_window_enabled`
  - `confirmation_window_ms`
  - `confirmation_trigger_conditions`
  - `dev_fallback_allowed`
  - `safe_barge_in_prompt_classes`
  - `protected_prompt_classes`
- **Validation Rules**:
  - `policy_id` must be unique within the settings snapshot.
  - `allowed_wake_modes` must contain only supported wake adapter modes.
  - `weak_accept_threshold` must not exceed `accept_threshold`.
  - `confirmation_window_ms` is required when
    `confirmation_window_enabled=true`.
  - Protected prompt classes must include destructive, shutdown, and explicit
    confirmation surfaces.
- **Relationships**:
  - configures `WakeAttemptRecord`
  - referenced by `BenchmarkReplayScenario`
  - persisted through existing settings storage

## WakeAttemptRecord

- **Purpose**: Represents one evaluated wake signal, including scoring,
  confirmation-window handling, and latency to listening.
- **Fields**:
  - `attempt_id`
  - `session_id`
  - `wake_mode`
  - `heard_phrase`
  - `canonical_wake_alias`
  - `score`
  - `accepted`
  - `rejection_reason`
  - `weak_detection`
  - `confirmation_required`
  - `confirmation_outcome`: `promoted | rejected | bypassed`
  - `probable_false_accept_review`
  - `probable_false_reject_review`
  - `wake_to_listen_ms`
- **Validation Rules**:
  - `accepted=false` requires `rejection_reason` when a wake signal was
    observed.
  - `confirmation_required=true` requires `weak_detection=true` or a policy
    condition that triggered confirmation.
  - `confirmation_outcome=bypassed` is valid only when
    `confirmation_required=false`.
  - `wake_to_listen_ms` must be non-negative when the wake is accepted.
- **Relationships**:
  - evaluated under `WakePolicyProfile`
  - emits `SpeechTelemetryEvent`
  - contributes to `PiQualificationRun`

## InteractionRecoveryRecord

- **Purpose**: Captures how the speech loop recovered from ordinary wake, STT,
  provider, or telemetry faults.
- **Fields**:
  - `recovery_id`
  - `session_id`
  - `fault_sequence_count`
  - `fault_type`: `wake_miss | stt_failure | provider_timeout | telemetry_sink_fault`
  - `reset_triggered`
  - `recovery_prompt_class`
  - `returned_state`: `standby | listening | degraded_standby`
  - `degraded_mode`
  - `provider_status`
  - `occurred_at`
- **Validation Rules**:
  - `fault_sequence_count` must start at `1` and reset after a successful
    interaction or standby reset.
  - `reset_triggered=true` requires `returned_state=standby`.
  - `fault_sequence_count=3` requires a recovery decision that exits the retry
    loop.
  - `telemetry_sink_fault` must not force a runtime exit.
- **Relationships**:
  - summarized by `SpeechTelemetryEvent`
  - associated with `SpeechReleaseGateResult` when recovery reliability fails

## SpeechTelemetryEvent

- **Purpose**: Represents one lightweight structured runtime measurement or
  decision emitted during live usage, replay, or qualification.
- **Fields**:
  - `event_id`
  - `scenario_label`
  - `event_type`: `wake_accepted | wake_rejected | false_accept_review | false_reject_review | command_confidence_distribution | clarification_loop | prompt_echo_suppressed | clipped_retry | wake_to_listen_latency | listen_to_result_latency | result_to_speech_start_latency | recovery_reset`
  - `session_id`
  - `interaction_id`
  - `timestamp_ms`
  - `event_source`
  - `outcome_status`
  - `latency_ms`
  - `metric_value`
  - `evidence_scope`: `live | replay | qualification`
  - `persisted_locally`
  - `external_sink_status`: `not_configured | delivered | failed`
  - `metadata`
- **Validation Rules**:
  - `event_type` must come from the approved telemetry catalog for this phase.
  - Latency event types require `latency_ms`.
  - `command_confidence_distribution` events must include summary buckets or
    histogram metadata for the evaluated command results.
  - Review event types must identify the wake attempt or interaction under
    review.
  - `persisted_locally=true` is required for default qualification evidence.
- **Relationships**:
  - emitted from wake handling, runtime orchestration, or replay harnesses
  - stored in local candidate artifacts by default
  - summarized by `PiQualificationRun` and `SpeechReleaseGateResult`

## BenchmarkReplayScenario

- **Purpose**: Represents a repeatable replay case used to validate wake,
  recovery, telemetry, and degraded-mode behavior.
- **Fields**:
  - `scenario_id`
  - `scenario_type`: `quiet_wake | noisy_wake | bilingual_wake | prompt_echo | degraded_provider | repeated_fault`
  - `fixture_refs`
  - `wake_policy_id`
  - `expected_wake_result`
  - `expected_recovery_result`
  - `expected_latency_budget_ms`
  - `requires_pi_hardware`
  - `artifact_label`
- **Validation Rules**:
  - `fixture_refs` must point to curated local fixtures or deterministic replay
    inputs.
  - `expected_latency_budget_ms` must be non-negative.
  - `requires_pi_hardware=true` is reserved for scenarios whose evidence is
    only valid on the target device.
- **Relationships**:
  - executed under `WakePolicyProfile`
  - produces `SpeechTelemetryEvent`
  - contributes to `SpeechReleaseGateResult`

## PiQualificationRun

- **Purpose**: Captures one Raspberry Pi 4 validation session for a candidate
  build and deployment profile.
- **Fields**:
  - `run_id`
  - `candidate_build_id`
  - `qualification_profile_id`
  - `started_at`
  - `duration_minutes`
  - `standby_cpu_median_pct`
  - `wake_cpu_peak_pct`
  - `listen_cpu_peak_pct`
  - `listen_memory_mb`
  - `speak_cpu_peak_pct`
  - `speak_memory_mb`
  - `startup_latency_ms`
  - `peak_temp_c`
  - `repeated_wake_cycles`
  - `unexpected_shutdown_count`
  - `telemetry_completeness_ratio`
  - `status`: `candidate | passed | failed`
- **Validation Rules**:
  - `duration_minutes` must cover the declared repeated wake-cycle scenario for
    release approval.
  - CPU, memory, latency, and thermal values must be non-negative.
  - `status=passed` requires zero unexpected shutdowns and a telemetry
    completeness ratio that meets the defined threshold.
  - `repeated_wake_cycles` must match the executed qualification scenario.
- **Relationships**:
  - aggregates `SpeechTelemetryEvent`
  - referenced by `SpeechReleaseGateResult`

## SpeechReleaseGateResult

- **Purpose**: Records whether a candidate build is approved or blocked for
  pilot or field testing based on replay validation and Raspberry Pi evidence.
- **Fields**:
  - `gate_result_id`
  - `candidate_build_id`
  - `ci_replay_status`: `passed | failed | missing`
  - `pi_hardware_status`: `passed | failed | missing`
  - `latest_pi_run_id`
  - `blocked_reasons`
  - `approved_for_pilot`
  - `approved_for_field`
  - `decided_at`
- **Validation Rules**:
  - `approved_for_pilot=true` requires `pi_hardware_status=passed`.
  - `approved_for_field=true` requires `approved_for_pilot=true`.
  - Any failed or missing required evidence must appear in `blocked_reasons`.
  - `latest_pi_run_id` is required when `pi_hardware_status` is not `missing`.
- **Relationships**:
  - summarizes `BenchmarkReplayScenario` results and `PiQualificationRun`
  - published through release documentation and gate output

## State Transitions

- `standby_entered -> wake_signal_observed -> wake_accepted -> listening`
- `wake_signal_observed -> confirmation_required -> wake_accepted` when a weak
  detection is confirmed
- `wake_signal_observed -> confirmation_required -> wake_rejected -> standby_entered`
- `listening_or_speaking -> ordinary_fault_recorded -> retry_allowed`
- `ordinary_fault_recorded -> recovery_reset_announced -> standby_entered` when
  three consecutive faults are reached
- `telemetry_event_created -> persisted_locally -> exported_optionally`
- `replay_scenario_selected -> replay_executed -> telemetry_validated`
- `qualification_candidate -> qualification_measured -> passed | failed`
- `release_gate_pending -> replay_evidence_checked -> pi_hardware_evidence_checked -> pilot_approved | blocked`
