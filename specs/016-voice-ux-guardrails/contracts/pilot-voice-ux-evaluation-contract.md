# Pilot Voice UX Evaluation Contract

## Purpose

Define the machine-readable evidence recorded for one pilot-style spoken-journey
validation run.

## Output Shape

```json
{
  "run_id": "pilot-ux-20260423-01",
  "scenario_label": "mixed-language-onboarding-early-answer",
  "journey_type": "onboarding",
  "completion_status": "completed",
  "retries_used": 1,
  "accepted_barge_in_count": 2,
  "prompt_echo_suppression_count": 1,
  "out_of_domain_rejection_count": 1,
  "fallback_or_exit_reason": null,
  "raw_utterance_present": false,
  "artifact_path": "artifacts/pilot-ux-20260423-01/voice-ux-summary.json"
}
```

## Rules

- `completion_status` must be one of:
  `completed`, `safe_default_continuation`, `graceful_exit`, or `failed`.
- `raw_utterance_present` must remain `false` for default field-safe evidence.
- `fallback_or_exit_reason` is required when the run does not complete
  normally.
- `accepted_barge_in_count`, `prompt_echo_suppression_count`, and
  `out_of_domain_rejection_count` must be non-negative integers.
- `artifact_path` must point to a local evidence location when persisted.

## Required Observability Fields

- `run_id`
- `scenario_label`
- `journey_type`
- `completion_status`
- `retries_used`
- `accepted_barge_in_count`
- `prompt_echo_suppression_count`
- `out_of_domain_rejection_count`
- `fallback_or_exit_reason`
- `raw_utterance_present`
- `artifact_path`

## Validation Expectations

- Integration coverage for mixed-language onboarding, early-answer capture,
  repeated invalid answers, prompt-echo suppression, and name confirmation
  recovery.
- Validation scripts or smoke checks that confirm evidence bundles remain
  field-safe and locally readable.
- Review guidance that ties recorded evidence back to the Phase 16 success
  criteria.
