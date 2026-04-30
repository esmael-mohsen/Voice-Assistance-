# Wake Reliability Outcome Contract

## Purpose

Define the structured runtime outcome emitted when standby evaluates a wake
attempt, including bounded confirmation-window behavior.

## Output Shape

```json
{
  "trigger": "wake_reliability",
  "status": "confirmation_required",
  "spoken_text": "I heard the wake phrase. Please repeat it once.",
  "error_code": null,
  "next_runtime_state": "wake_confirmation",
  "selected_wake_mode": "keyword_low_power",
  "canonical_wake_alias": "hi egb",
  "weak_detection": true,
  "confirmation_required": true,
  "payload": {
    "score": 0.71,
    "wake_to_listen_ms": null,
    "prompt_class": "wake_ready",
    "degraded_reason": null,
    "probable_false_accept_review": false,
    "probable_false_reject_review": false
  }
}
```

## Rules

- `status` must be one of:
  `wake_accepted`, `wake_rejected`, `confirmation_required`, or
  `degraded_standby`.
- `wake_accepted` requires `next_runtime_state=listening`.
- `confirmation_required` is valid only for weak or noisy detections allowed by
  the active wake policy.
- `wake_rejected` and `degraded_standby` must preserve a safe standby state.
- `probable_false_accept_review` and `probable_false_reject_review` are review
  signals and must not by themselves change the runtime decision already taken.

## Required Observability Fields

- `trigger`
- `status`
- `spoken_text`
- `error_code`
- `next_runtime_state`
- `selected_wake_mode`
- `canonical_wake_alias`
- `weak_detection`
- `confirmation_required`
- `payload.score`
- `payload.wake_to_listen_ms`
- `payload.prompt_class`
- `payload.degraded_reason`
- `payload.probable_false_accept_review`
- `payload.probable_false_reject_review`

## Validation Expectations

- Unit coverage for clear acceptance, weak-detection confirmation, and safe
  rejection.
- Integration coverage for noisy wake scenarios and production wake guardrails.
- Smoke validation for headless wake-to-listen behavior.
