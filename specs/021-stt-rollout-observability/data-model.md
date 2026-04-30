# Data Model: STT Observability, Rollout Gates, and PocketSphinx Decommission

## SttTelemetryEvent

**Purpose**: Represents one field-safe recognition, fallback, retry, clipping,
timeout, Arabic-failure, or language-mismatch event.

**Fields**:
- `event_id`
- `session_id`
- `candidate_run_id`
- `event_type`: `cloud_attempt | cloud_failure | strict_fallback |
  rescue_recognition | retry | clipping | timeout | arabic_failure |
  language_mismatch | confidence_policy`
- `source`: `cloud | strict_vosk | rescue | local |
  compatibility | none`
- `rollout_mode`: `shadow | wake_only | commands_low_risk |
  full_cloud_primary | rollback`
- `status`: `started | succeeded | failed | recovered | blocked`
- `confidence_bucket`: `high | medium | low | missing | unavailable`
- `failure_category`: `none | network | credentials | quota_or_rate |
  cloud_timeout | fallback_missing | microphone_timeout | clipping |
  language_mismatch | confidence_policy | unknown`
- `recovery_outcome`: `none | fallback | retry | safe_refusal | standby`
- `latency_bucket`: `within_target | baseline_regression |
  threshold_breach | unavailable`
- `reason_code`
- `field_safe`: `true`
- `raw_audio_present`: `false`
- `raw_utterance_present`: `false`

**Validation Rules**:
- `field_safe` must be true in default evidence.
- Raw audio and raw utterance flags must be false in default evidence.
- Failed events require a non-`none` `failure_category` and `reason_code`.
- Recovered events require a non-`none` `recovery_outcome`.

**Relationships**:
- Aggregated into `SttTelemetryRollup`.
- May provide evidence for `FailureScenarioResult` and `ReleaseGateResult`.

## SttTelemetryRollup

**Purpose**: Summarizes field-safe STT behavior for one session or release
candidate run.

**Fields**:
- `rollup_id`
- `candidate_run_id`
- `session_count`
- `event_count`
- `rollout_mode_counts`
- `source_counts`
- `status_counts`
- `confidence_bucket_counts`
- `failure_category_counts`
- `recovery_outcome_counts`
- `latency_bucket_counts`
- `fallback_frequency`
- `cloud_failure_frequency`
- `retry_rate`
- `clipping_rate`
- `timeout_rate`
- `arabic_failure_count`
- `language_mismatch_rate`
- `field_safe`
- `retention_days`

**Validation Rules**:
- `retention_days` defaults to `180`.
- Rollup counts must be derived from field-safe events only.
- Missing or incomplete telemetry must be explicitly represented rather than
  silently omitted.

**Relationships**:
- Consumes many `SttTelemetryEvent` records.
- Feeds `ReleaseGateResult` and quickstart evidence.

## RolloutModeState

**Purpose**: Captures the effective rollout mode after rollback controls are
applied.

**Fields**:
- `state_id`
- `requested_mode`: `shadow | wake_only | commands_low_risk |
  full_cloud_primary`
- `effective_mode`: `shadow | wake_only | commands_low_risk |
  full_cloud_primary | rollback`
- `rollback_override_active`
- `rollback_reason_code`
- `field_validation_complete`
- `user_visible_behavior_changed`
- `field_safe_metadata`

**Validation Rules**:
- If rollback override is active, `effective_mode` must be `rollback`.
- `shadow` mode must not change user-visible behavior.
- Rollback controls must remain available until field validation is complete.

**Relationships**:
- Annotates `SttTelemetryEvent`.
- Feeds rollout release gates and documentation.

## FailureScenarioResult

**Purpose**: Records how a covered STT failure scenario was classified and
recovered without an unhandled crash.

**Fields**:
- `scenario_id`
- `failure_category`
- `source`
- `rollout_mode`
- `bounded_outcome`: `fallback | retry | safe_refusal | standby`
- `crash_free`
- `spoken_guidance_surface`
- `diagnostic_reason_code`
- `field_safe_metadata`

**Validation Rules**:
- `crash_free` must be true for passing scenarios.
- Every scenario must resolve to one bounded outcome.
- Diagnostic metadata must exclude raw audio and raw utterance content.

**Relationships**:
- May be generated from one or more `SttTelemetryEvent` records.
- Blocking release gates consume failure scenario results.

## ReleaseGateResult

**Purpose**: Defines one machine-readable readiness gate for pilot or field
approval.

**Fields**:
- `gate_id`
- `gate_name`
- `gate_status`: `passed | failed | skipped`
- `blocking_level`: `none | pilot | field | pilot_and_field`
- `reason_code`
- `evidence_refs`
- `cloud_configuration_status`
- `strict_fallback_status`
- `wake_fallback_status`
- `protected_command_status`
- `bilingual_regression_status`
- `bounded_recovery_status`
- `pi4_qualification_status`
- `pocketsphinx_default_usage_count`
- `field_safe_payload`

**Validation Rules**:
- Blocking safety gates with `failed` status must block pilot and field
  approval.
- Default PocketSphinx usage count must be zero for production readiness.
- Missing or failed Pi 4 qualification blocks pilot and field approval.

**Relationships**:
- Consumes `SttTelemetryRollup`, `FailureScenarioResult`,
  `Pi4QualificationSnapshot`, and `PocketSphinxDecommissionEvidence`.

## Pi4QualificationSnapshot

**Purpose**: Captures recognition latency and resource evidence from Raspberry
Pi 4 validation.

**Fields**:
- `snapshot_id`
- `candidate_run_id`
- `environment`: `raspberry_pi_4`
- `wake_latency_p95_ms`
- `command_recognition_latency_p95_ms`
- `fallback_latency_p95_ms`
- `standby_cpu_median_pct`
- `recognition_cpu_peak_pct`
- `cloud_path_memory_mb`
- `fallback_path_memory_mb`
- `peak_temp_c`
- `repeated_wake_cycles`
- `unexpected_shutdown_count`
- `telemetry_completeness_ratio`
- `threshold_policy_ref`
- `status`: `passed | failed`
- `blocked_thresholds`
- `evidence_refs`

**Validation Rules**:
- Environment must be Raspberry Pi 4 for pilot or field approval.
- Status is failed when any approved threshold is breached.
- Missing real-hardware evidence blocks pilot and field approval.

**Relationships**:
- Extends existing Pi qualification release-gate evidence.
- Feeds `ReleaseGateResult`.

## PocketSphinxDecommissionEvidence

**Purpose**: Proves PocketSphinx is outside the default production STT path and
the required production accuracy baseline.

**Fields**:
- `evidence_id`
- `candidate_run_id`
- `default_candidate_count`
- `default_invocation_count`
- `compatibility_flag_status`
- `accuracy_baseline_includes_sphinx`
- `compatibility_tests_present`
- `documentation_status`
- `status`: `passed | failed`
- `evidence_refs`

**Validation Rules**:
- `default_candidate_count` must be zero.
- `default_invocation_count` must be zero.
- `accuracy_baseline_includes_sphinx` must be false.
- Compatibility tests may exist only to prove non-default behavior.

**Relationships**:
- Feeds `ReleaseGateResult`.
- Links to STT documentation and required baseline evidence.

## State Transitions

- `requested rollout mode -> RolloutModeState(effective_mode)` after rollback
  controls are applied.
- `recognition attempt -> SttTelemetryEvent` for every cloud, fallback, retry,
  clipping, timeout, Arabic-failure, and language-mismatch outcome.
- `SttTelemetryEvent[] -> SttTelemetryRollup` at session or candidate-run
  boundaries.
- `recognized failure -> FailureScenarioResult` after the failure taxonomy is
  mapped to fallback, retry, safe refusal, or standby.
- `Pi 4 evidence -> Pi4QualificationSnapshot(passed|failed)` after threshold
  evaluation.
- `PocketSphinx evidence -> PocketSphinxDecommissionEvidence(passed|failed)`
  after candidate, invocation, baseline, and documentation checks.
- `rollups + failure results + Pi 4 snapshot + PocketSphinx evidence ->
  ReleaseGateResult(passed|failed)` for pilot and field readiness.
