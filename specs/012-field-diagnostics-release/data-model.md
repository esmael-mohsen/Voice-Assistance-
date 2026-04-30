# Data Model: Field Diagnostics and Release Consistency

## ReleaseValidationContext

- **Purpose**: Captures the execution context that makes a release validation
  run reproducible and reviewable.
- **Fields**:
  - `run_id`
  - `candidate_id`
  - `commit_sha`
  - `trigger`
  - `python_executable`
  - `working_directory`
  - `invoked_command`
  - `started_at`
  - `completed_at`
- **Validation Rules**:
  - `python_executable` must resolve to the active interpreter used for gate
    execution.
  - `working_directory` must point to the repository root or the effective run
    root used for artifact resolution.
  - `completed_at` must be present once the run reaches a terminal state.
- **Relationships**:
  - owned by `ReleaseValidationOutcome`
  - referenced by `PilotTroubleshootingStep`

## DiagnosticArtifactReference

- **Purpose**: Standardizes how release summaries and workflows point to
  related evidence.
- **Fields**:
  - `kind`
  - `path`
  - `checksum`
  - `available`
  - `source`: `generated | linked | missing`
  - `notes`
- **Validation Rules**:
  - `kind` must match one expected artifact category for the run.
  - `available=false` requires `source=missing` and a non-empty `notes`
    explaining the gap.
  - `checksum` is required whenever `available=true`.
- **Relationships**:
  - belongs to `ReleaseValidationOutcome`
  - consumed by `PilotTroubleshootingStep`

## ReleaseValidationOutcome

- **Purpose**: Represents the operator-facing result for one release
  validation run, including final decision and artifact completeness.
- **Fields**:
  - `run_id`
  - `status`: `passed | failed | approved_with_override`
  - `execution_context`: `ReleaseValidationContext`
  - `executed_checks`
  - `failed_blocking_gates`
  - `expected_artifact_kinds`
  - `artifact_references`: list of `DiagnosticArtifactReference`
  - `missing_artifact_kinds`
  - `final_decision_reason`
  - `artifact_manifest_id`
- **Validation Rules**:
  - `executed_checks` must contain every gate actually attempted by the run.
  - `expected_artifact_kinds` must include run summary and per-gate results for
    every run.
  - `missing_artifact_kinds` must match any expected category whose artifact
    reference is not available.
  - Failed runs must still preserve summary-level information and artifact
    references.
- **Relationships**:
  - aggregates `ReleaseValidationContext`
  - aggregates `DiagnosticArtifactReference`
  - linked from `PilotTroubleshootingStep`

## RuntimeDiagnosticEvent

- **Purpose**: Provides one canonical structured record for a provider
  selection, offline-policy decision, or interrupt outcome.
- **Fields**:
  - `event_id`
  - `timestamp`
  - `session_or_run_id`
  - `event_category`: `provider_selection | offline_policy | interrupt`
  - `status_or_decision`
  - `reason_code`
  - `provider_id`
  - `provider_availability`
  - `degraded_mode`
  - `degraded_reason`
  - `next_state`
  - `latency_ms`
  - `user_outcome`
  - `field_safe`: boolean
  - `raw_user_content_present`: boolean
- **Validation Rules**:
  - `event_category` must be one of the approved diagnostic categories.
  - `field_safe=true` requires `raw_user_content_present=false`.
  - `latency_ms` is required when `event_category=interrupt` and a preemption
    measurement is available.
  - `degraded_mode=true` requires a non-empty `degraded_reason`.
  - Provider-selection events must identify the active provider context when a
    provider is chosen or degraded.
- **Relationships**:
  - emitted by shared runtime boundaries under `core/`
  - referenced by `PilotTroubleshootingStep`

## PilotTroubleshootingStep

- **Purpose**: Encodes the documented review sequence operators follow during
  pilot triage.
- **Fields**:
  - `step_order`
  - `focus_area`
  - `primary_artifact_kind`
  - `event_categories`
  - `questions_answered`
  - `next_action`
- **Validation Rules**:
  - `step_order` must be unique and start at `1`.
  - The first step must target the run summary.
  - Provider or degraded diagnostics must appear before offline-policy events.
  - Interrupt outcomes and latency review must appear before linked supporting
    artifacts.
- **Relationships**:
  - consumes `ReleaseValidationOutcome`
  - consumes `RuntimeDiagnosticEvent`

## State Transitions

- `validation_requested -> gates_running -> validation_completed`
- `validation_completed -> artifact_references_verified -> review_ready`
- `validation_completed -> artifact_gap_identified -> review_ready_with_gaps`
- `runtime_decision_made -> diagnostic_event_emitted -> troubleshooting_reviewed`
- `troubleshooting_reviewed -> linked_artifact_followup` is valid only after
  the ordered review steps have been applied
