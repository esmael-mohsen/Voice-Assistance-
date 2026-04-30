# Release Troubleshooting

## Purpose

Provide a short artifact-first review workflow for release validation and field
runtime diagnostics so operators can classify failures quickly without a
debugger.

## Common Failure Patterns

- Startup/provider readiness failures
- Quality gate failures (`compile`, `pytest`, `ruff`)
- Missing or incomplete artifact evidence
- Offline-policy safe refusals or degraded execution
- Interrupt preemption regressions
- Localization integrity failures
- Baseline threshold breaches

## Pilot Review Order

1. Open `summary.json` first and identify run status, first failing blocking
   gate, and expected artifact kinds.
2. Review provider-selection or degraded diagnostics from
   `diagnostic-artifacts.json` to identify active provider, degraded state, and
   degraded reason.
3. Review offline-policy events to classify `allow_execution`,
   `on_device_fallback`, `safe_refusal`, or `provider_degraded`.
4. Review interrupt outcomes and preemption latency to confirm final runtime
   state and interruption behavior.
5. Follow linked supporting artifacts (`gate-results.json`, `manifest.json`,
   `checklist.json`, and optional baseline/localization/override artifacts).

## Artifact Checklist (Per Run)

- Base artifact kinds expected on every run:
  `gate_summary`, `test_results`, `diagnostic_artifact_index`.
- Conditional artifact kinds:
  `checklist_evidence`, `baseline_comparison`, `localization_results`,
  `override_record`.
- If any expected kind is missing, keep triage in artifact mode and classify
  the run as `review_ready_with_gaps` until evidence is restored.

## Runtime Diagnostic Signals

- Canonical diagnostic fields to verify:
  `timestamp`, `session_or_run_id`, `event_category`, `status_or_decision`,
  `reason_code`, `provider_context`, `next_state`, `latency_ms` (when present),
  `field_safe`, and `raw_user_content_present`.
- Default field evidence must stay metadata-first:
  `field_safe=true` and `raw_user_content_present=false`.

## Event-Specific Checks

### Provider Selection

- Check `provider_context.provider_id`, `provider_context.provider_availability`,
  `provider_context.degraded_mode`, `provider_context.degraded_reason`.
- Confirm degraded transitions remain consistent across headless and GUI runs.

### Offline Policy

- Confirm decision and truthfulness fields:
  `decision`, `override_mode`, `detected_status`,
  `effective_network_available`, `provider_availability`, `error_code`.
- Repeated offline-policy events should remain understandable and not lose
  decision context.

### Interrupt Outcomes

- Confirm interrupt records include `interrupt_signal_type`,
  `completion_status`, `next_state`, and `preemption_latency_ms` or
  `latency_ms`.
- Repeated interrupt events should remain readable and preserve final state.

## Scenario Coverage

- Successful run: verify no hidden artifact gaps and consistent diagnostic
  metadata.
- Failed run: identify first failing blocking gate and linked evidence quickly.
- Degraded run: classify provider/offline/interrupt reason path without a
  debugger.

## Phase 15 Release-Gate Triage

- If CI replay is green but pilot approval is still blocked, check for:
  `missing_pi4_qualification` or `pi4_qualification_failed`.
- If gate payload includes `missing_artifact:*`, restore required candidate
  artifacts before rerunning approval.
- If telemetry sink export fails, verify local telemetry still persisted and
  `external_sink_status=failed` is treated as recoverable.

## Phase 21 STT Rollout Triage

### Fast Path Checks

1. Open `stt-release-gate.json` and read `gate_status` and `blocked_reasons`.
2. Check `stt-rollup.json` for `cloud_failure_frequency`, `fallback_frequency`,
   `retry_rate`, `clipping_rate`, `timeout_rate`, and `language_mismatch_rate`.
3. Check `stt-events.json` to confirm each failed event has:
   `source`, `rollout_mode`, `failure_category`, `recovery_outcome`,
   `latency_bucket`, and `reason_code`.
4. Confirm `pi4-stt-qualification.json` exists for pilot/field decisions.
5. Confirm `pocketsphinx-decommission.json` reports zero default candidate and
   invocation counts.

### Common Blocking Reasons

- `missing_cloud_configuration`
- `missing_strict_fallback`
- `unsafe_wake_fallback`
- `protected_command_regression`
- `bilingual_regression`
- `bounded_recovery_regression`
- `pi4_qualification_failed_or_missing`
- `default_pocketsphinx_candidates_detected`
- `default_pocketsphinx_invocations_detected`

### Recovery Guidance

- If failure category is `network`, prioritize retry and fallback path health.
- If failure category is `credentials` or `quota_or_rate`, keep safe refusal
  enabled and verify cloud readiness separately from fallback readiness.
- If failure category is `fallback_missing`, block rollout progression until
  strict local fallback model evidence is restored.
- If `shadow` mode reports user-visible changes, treat as rollout policy
  regression and block promotion.
