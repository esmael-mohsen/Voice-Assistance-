# Turn-Taking Window Contract

## Purpose

Define the structured runtime decision emitted when the assistant opens,
updates, or closes a guided turn-taking window.

## Output Shape

```json
{
  "trigger": "turn_taking",
  "status": "speaking_with_barge_in",
  "spoken_text": "Choose a language: Arabic or English.",
  "error_code": null,
  "next_runtime_state": "speaking",
  "prompt_surface_id": "runtime.onboarding.language",
  "prompt_class": "onboarding_choice",
  "barge_in_allowed": true,
  "closed_vocabulary_id": "onboarding.language_choice",
  "payload": {
    "window_id": "turn-window-01",
    "global_safety_only_preemption": false,
    "retry_count": 0,
    "prompt_echo_guard_enabled": true,
    "recent_prompt_text_present": true
  }
}
```

## Rules

- `status` must be one of:
  `speaking_only`, `speaking_with_barge_in`, `listening`,
  `closed_vocabulary_listening`, `waiting_confirmation`, or `recovering`.
- `status=speaking_with_barge_in` requires `barge_in_allowed=true`.
- `status=closed_vocabulary_listening` requires `closed_vocabulary_id`.
- Protected confirmations, shutdown prompts, and destructive prompts must set
  `global_safety_only_preemption=true` until the first protected prompt pass is
  complete.
- `prompt_echo_guard_enabled=true` is required for guided spoken prompts.

## Required Observability Fields

- `trigger`
- `status`
- `spoken_text`
- `error_code`
- `next_runtime_state`
- `prompt_surface_id`
- `prompt_class`
- `barge_in_allowed`
- `closed_vocabulary_id`
- `payload.window_id`
- `payload.global_safety_only_preemption`
- `payload.retry_count`
- `payload.prompt_echo_guard_enabled`
- `payload.recent_prompt_text_present`

## Validation Expectations

- Unit coverage for eligible barge-in windows, protected windows, and retry
  windows.
- Integration coverage for early answers during prompt playback and protected
  prompt blocking.
- Smoke validation for guided turn transitions in headless runtime mode.
