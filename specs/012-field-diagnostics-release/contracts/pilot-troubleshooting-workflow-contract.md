# Pilot Troubleshooting Workflow Contract

## Purpose

Define the ordered review structure operators follow when triaging a completed
release run or field issue bundle.

## Output Shape

```json
{
  "workflow_name": "pilot_log_review",
  "steps": [
    {
      "step_order": 1,
      "focus_area": "run_summary",
      "primary_artifact_kind": "gate_summary",
      "questions_answered": [
        "Did the run pass or fail?",
        "Which blocking gate failed first?",
        "Which artifact kinds are expected?"
      ]
    },
    {
      "step_order": 2,
      "focus_area": "provider_or_degraded_diagnostics",
      "primary_artifact_kind": "diagnostic_artifacts",
      "questions_answered": [
        "Which provider was active?",
        "Was the session degraded and why?"
      ]
    },
    {
      "step_order": 3,
      "focus_area": "offline_policy_events",
      "primary_artifact_kind": "diagnostic_artifacts",
      "questions_answered": [
        "Was the action allowed, downgraded, or refused?"
      ]
    },
    {
      "step_order": 4,
      "focus_area": "interrupt_outcomes_and_latency",
      "primary_artifact_kind": "diagnostic_artifacts",
      "questions_answered": [
        "Was work preempted?",
        "What state did the runtime enter?",
        "What was the preemption latency?"
      ]
    },
    {
      "step_order": 5,
      "focus_area": "linked_supporting_artifacts",
      "primary_artifact_kind": "manifest",
      "questions_answered": [
        "What deeper artifact should be opened next?"
      ]
    }
  ]
}
```

## Rules

- Review order must always begin with the run summary.
- Provider or degraded diagnostics must be reviewed before offline-policy
  events.
- Interrupt outcomes and preemption latency must be reviewed before linked
  supporting artifacts.
- The workflow must be usable for successful runs, failed runs, and degraded
  field sessions without assuming a debugger.

## Required Observability Fields

- `workflow_name`
- `steps.step_order`
- `steps.focus_area`
- `steps.primary_artifact_kind`
- `steps.questions_answered`

## Validation Expectations

- Documentation review confirms the workflow matches `docs/release/troubleshooting.md`.
- Integration or smoke validation confirms the required artifact kinds exist
  where the workflow expects them.
