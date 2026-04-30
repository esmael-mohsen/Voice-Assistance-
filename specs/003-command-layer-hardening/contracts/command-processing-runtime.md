# Command Processing Runtime Contract

## Purpose

Define the command-processing contract between parser, resolver, dispatcher,
and runtime consumers for the command-layer hardening feature.

## Supported Command Scope

This phase hardens the current supported command set only. No new commands are
introduced. Commands are classified into:

- `capability`: obstacle, OCR, face, emotion, money detection
- `settings`: language, voice, and speech-speed controls
- `system`: start, stop, status, and reset actions

## Risk Policy

- `protected` system commands require explicit confirmation before execution.
- `elevated` system commands use stricter intent validation but do not require
  confirmation.
- `normal` capability and settings commands use standard validation rules while
  still rejecting weak or ambiguous matches.

Protected commands for this phase:

- `stop_system`
- `reset_settings`

Elevated but non-confirmed system commands for this phase:

- `start_system`
- `get_system_status`

## Parse Contract

### Input

- Raw recognized user text from STT or scripted tests

### Output Shape

```json
{
  "intent_id": "enable_obstacle_detection",
  "category": "capability",
  "risk_level": "normal",
  "matched_keyword": "start obstacle detection",
  "score": 91.0,
  "threshold": 78.0,
  "accepted": true,
  "rejection_reason": null,
  "metadata": {
    "normalized_text": "start obstacle detection"
  }
}
```

### Parse Rules

1. Parser must evaluate command candidates against the existing supported
   command catalog.
2. Parser must reject input that is below the configured threshold or too close
   to a competing candidate.
3. Parser must classify accepted matches before resolver execution.
4. Parser must not execute commands or mutate runtime state.

## Resolution Contract

### Input

- Accepted or rejected parse result
- Raw command text
- Current `SessionCommandContext`

### Output Shape

```json
{
  "intent_id": "recognize_emotion",
  "validation_status": "ready",
  "route_target": "controller",
  "params": {
    "face_id": "Face_001"
  },
  "used_session_context": true,
  "spoken_text": "Detected a happy emotion for Face_001",
  "error_code": null
}
```

### Resolution Rules

1. Resolver must extract and normalize parameters in structured form.
2. Missing or unclear required parameters must produce one
   `clarification_required` outcome before failing safely.
3. One-turn follow-up context may be used only for the immediately relevant
   next command.
4. Protected system commands must resolve to `confirmation_required` until the
   user explicitly confirms them.
5. Resolver must keep system-command routing separate from capability-command
   routing, even though both remain inside the shared dispatch pipeline.

## Dispatch Contract

`core.dispatcher.dispatch(text)` must return a single structured
`CommandExecutionResult` for every outcome.

### Execution Result Shape

```json
{
  "intent_id": "stop_system",
  "category": "system",
  "status": "confirmation_required",
  "spoken_text": "Please confirm that you want to stop the system.",
  "payload": {
    "confirmation_required": true
  },
  "error_code": null,
  "metadata": {
    "risk_level": "protected"
  }
}
```

### Required Fields

- `status`
- `spoken_text`

### Optional Fields

- `intent_id`
- `category`
- `payload`
- `error_code`
- `metadata`

### Allowed Status Values

- `success`
- `clarification_required`
- `confirmation_required`
- `rejected`
- `failed`

## Runtime Consumer Expectations

- `core.assistant_runtime` may normalize structured results into assistant
  speech, but it must preserve the structured fields for logging and tests.
- GUI and console paths must observe equivalent command outcomes for the same
  regression scenario.
- A `rejected` or `clarification_required` result is a valid user-flow outcome,
  not a runtime exception.
- If network-backed speech providers degrade or fail, command outcomes must
  remain safe and explicit, reusing the existing runtime fallback/degraded-mode
  behavior instead of silently skipping failures.

## Session Context Rules

- Follow-up context may survive for one immediate next command only.
- Protected-command confirmation state may survive for one immediate next
  response only.
- Unrelated input or timeout-equivalent turnover clears pending context.

## Validation Expectations

- Protected system commands must show zero unintended activations in curated
  near-match coverage.
- Structured result shape must remain stable across parser, resolver,
  dispatcher, and runtime-facing tests.
- GUI and console paths must preserve parity for the high-priority regression
  suite.
- Validation must capture representative baseline timing samples for wake, STT,
  TTS start, command dispatch completion, and recoverable provider-failure
  handling to support non-regression checks.
