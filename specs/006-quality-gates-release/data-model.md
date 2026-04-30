# Data Model: Quality Gates and Release Preparation

## ReleaseValidationRun

- **Purpose**: Represents one candidate release gate execution from start to
  final decision.
- **Fields**:
  - `run_id`: unique identifier
  - `candidate_id`: release candidate label/version
  - `commit_sha`: validated code revision
  - `trigger`: `manual | ci | scheduled`
  - `started_at`
  - `completed_at`: optional until finished
  - `status`: `running | passed | failed | override_pending | approved_with_override`
  - `approved_by`: optional release approver identity
  - `artifact_manifest_id`: foreign key to stored evidence
- **Validation Rules**:
  - `run_id` must be unique.
  - `completed_at` is required for any final status.
  - `approved_with_override` requires linked `EmergencyOverrideRecord`.
- **Relationships**:
  - has many `GateExecutionResult`
  - has many `LatencyComparisonResult`
  - has one `ReleaseChecklistRecord`
  - may have one `EmergencyOverrideRecord`
  - has one `ValidationArtifactManifest`

## GateExecutionResult

- **Purpose**: Captures outcome for one quality gate stage.
- **Fields**:
  - `gate_result_id`
  - `run_id`
  - `gate_name`: `compile | unit_tests | integration_tests | smoke_tests | lint | lifecycle_validation | journey_validation | localization_validation | baseline_compare | checklist_validation`
  - `status`: `passed | failed | skipped | overridden`
  - `is_blocking`: boolean
  - `duration_ms`
  - `failure_code`: optional
  - `summary`: short human-readable outcome
  - `evidence_ref`: link/path to detailed artifact
- **Validation Rules**:
  - `status=failed` on a blocking gate sets run status to `failed` unless an
    approved override exists.
  - `failure_code` is required when `status=failed`.
  - `duration_ms` must be non-negative.
- **Relationships**:
  - belongs to `ReleaseValidationRun`
  - referenced by `EmergencyOverrideRecord` when overridden

## LatencyBaselineRecord

- **Purpose**: Stores approved baseline values for required wearable metrics.
- **Fields**:
  - `baseline_id`
  - `metric_name`: `wake_to_listen | listen_to_result | result_to_speech_start`
  - `profile`: runtime/environment profile key
  - `sample_count`
  - `p50_ms`
  - `p95_ms`
  - `captured_at`
  - `approved_at`
  - `approved_by`
  - `source_run_id`
- **Validation Rules**:
  - `sample_count` must be > 0.
  - `p95_ms` must be >= `p50_ms`.
  - baseline is not eligible for comparison until approved.
- **Relationships**:
  - referenced by `LatencyComparisonResult`
  - derived from one `ReleaseValidationRun`

## LatencyThresholdPolicy

- **Purpose**: Defines approved per-metric degradation thresholds.
- **Fields**:
  - `policy_id`
  - `metric_name`: same enum as `LatencyBaselineRecord`
  - `degradation_limit_pct`
  - `degradation_limit_ms`
  - `effective_from`
  - `effective_to`: optional
  - `approved_by_engineering_lead`
  - `approved_by_qa_safety`
- **Validation Rules**:
  - policy values must be explicit per metric.
  - active comparison must use one effective policy per metric.
- **Relationships**:
  - used by `LatencyComparisonResult`

## LatencyComparisonResult

- **Purpose**: Stores per-metric candidate-vs-baseline comparison and breach
  decision.
- **Fields**:
  - `comparison_id`
  - `run_id`
  - `metric_name`
  - `current_p95_ms`
  - `baseline_p95_ms`
  - `delta_ms`
  - `delta_pct`
  - `threshold_ms`
  - `threshold_pct`
  - `breached`: boolean
  - `decision_reason`
- **Validation Rules**:
  - `breached=true` if candidate metric exceeds configured threshold for that
    metric.
  - any `breached=true` result must fail blocking baseline gate.
- **Relationships**:
  - belongs to `ReleaseValidationRun`
  - references one `LatencyBaselineRecord` and one `LatencyThresholdPolicy`

## CriticalPromptValidationResult

- **Purpose**: Captures regression check outcome for one critical prompt in one
  language.
- **Fields**:
  - `prompt_result_id`
  - `run_id`
  - `prompt_key`
  - `language`: `ar | en`
  - `expected_text`
  - `observed_text`
  - `status`: `passed | failed`
  - `failure_reason`: optional (`missing`, `garbled`, `mismatch`)
- **Validation Rules**:
  - every required prompt key must have both `ar` and `en` records.
  - any failed critical prompt must fail localization gate.
- **Relationships**:
  - belongs to `ReleaseValidationRun`
  - contributes to localization `GateExecutionResult`

## ReleaseChecklistRecord

- **Purpose**: Stores completion state for mandatory release checklist items.
- **Fields**:
  - `checklist_id`
  - `run_id`
  - `offline_behavior_status`: `pass | fail | n/a`
  - `emergency_control_status`: `pass | fail | n/a`
  - `audio_permission_status`: `pass | fail | n/a`
  - `crash_recovery_status`: `pass | fail | n/a`
  - `completed_by`
  - `completed_at`
  - `notes`: optional
- **Validation Rules**:
  - all mandatory items must be `pass` for checklist gate success.
  - completion metadata is required when checklist status is final.
- **Relationships**:
  - one-to-one with `ReleaseValidationRun`
  - evidence included in `ValidationArtifactManifest`

## EmergencyOverrideRecord

- **Purpose**: Audits emergency gate override approvals and remediation timing.
- **Fields**:
  - `override_id`
  - `run_id`
  - `requested_by`
  - `requested_at`
  - `reason`
  - `engineering_lead_approver`
  - `qa_safety_approver`
  - `approved_at`
  - `remediation_due_at`
  - `remediation_status`: `open | closed | breached`
  - `remediation_closed_at`: optional
  - `closure_evidence_ref`: optional
- **Validation Rules**:
  - both required approver roles are mandatory before override is active.
  - `remediation_due_at` must be <= `approved_at + 48h`.
  - if `remediation_closed_at` is after due time, status must be `breached`.
- **Relationships**:
  - belongs to `ReleaseValidationRun`
  - references overridden `GateExecutionResult` entries

### Override State Transitions

- `requested -> approved -> closed`
- `requested -> approved -> breached`
- `requested -> rejected`

## ValidationArtifactManifest

- **Purpose**: Defines retention and indexing for release evidence artifacts.
- **Fields**:
  - `manifest_id`
  - `run_id`
  - `created_at`
  - `storage_root`
  - `artifact_entries`: list of `{kind, path, checksum}`
  - `retention_until`
  - `purge_status`: `active | archived | purged`
- **Validation Rules**:
  - `retention_until` must equal release approval date + 180 days.
  - required artifact kinds: gate summary, test outputs, localization results,
    baseline comparisons, checklist evidence, and override record (if present).
- **Relationships**:
  - one-to-one with `ReleaseValidationRun`
  - referenced by release audit and compliance checks
