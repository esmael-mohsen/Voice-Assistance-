# Runtime Service Contract

## Purpose

Define the observer-facing runtime contract used by both GUI and console paths
after extraction to the shared `core/assistant_runtime.py` service.

## Runtime Control Surface

### Create Runtime

- **Factory**: `AssistantRuntime(mode, observer, default_language=None, ...)`
- **Inputs**:
  - `mode`: `gui` or `console`
  - `observer`: callback that receives `RuntimeEvent`
  - `default_language` (optional): startup language override
  - dependency overrides for listener/TTS/wake/dispatcher (for tests/integration)

### Start Runtime

- **Method**: `start_in_background()` or `run_forever(max_cycles=None)`
- **Behavior**:
  - loads profile/settings snapshot
  - attaches listener and TTS runtime dependencies
  - emits initial `status=standby`, `system`, and `config` events
  - begins standby/wake/active command loop

### Request Stop

- **Method**: `request_stop()`
- **Behavior**:
  - marks runtime stop requested
  - loop exits safely at next checkpoint
  - finalization emits assistant shutdown message and `status=offline`

### Shutdown

- **Method**: `shutdown(join_timeout_s=2.0)`
- **Behavior**:
  - requests stop and joins worker thread when background mode is used
  - ensures runtime ends in `offline` state

## Runtime Event Envelope

Every emitted event includes:

- `type`: `status | system | config | user | assistant | error`
- `session_id`: runtime session identifier
- `payload`: event-specific data
- `timestamp`: ISO-8601 UTC timestamp

## Event Types

### `status`

- **Payload**: `{ "state": "<lifecycle-state>" }`
- **Canonical lifecycle vocabulary**:
  - `standby`
  - `wake`
  - `setup`
  - `listening`
  - `thinking`
  - `speaking`
  - `error`
  - `offline`
- **Compatibility mapping**:
  - input `online` -> canonical output `listening`
  - input `stopping` -> canonical output `offline`
  - when mapped, `raw_state` is included in payload

### `system`

- **Payload**: `{ "text": "<system-message>" }`
- **Usage**: startup prompts, onboarding notices, runtime guidance

### `config`

- **Payload**:

```json
{
  "language": "ar-EG",
  "gender": "female",
  "speed": 1.0
}
```

- **Usage**: startup config and runtime setting changes

### `user`

- **Payload**: `{ "text": "<recognized-command>" }`
- **Usage**: observer display of recognized user input

### `assistant`

- **Payload**: `{ "text": "<assistant-output>" }`
- **Usage**: spoken/runtime response for observers

### `error`

- **Payload**:

```json
{
  "message": "human-readable error",
  "recoverable": true,
  "next_state": "standby"
}
```

- **Rules**:
  - recoverable failures MUST set `next_state` to `standby`
  - startup/init failures and `UnrecoverableRuntimeError` MUST set `next_state`
    to `offline`

## Transition Guarantees

- Wake flow: `standby -> wake -> listening` (or `setup` before `listening` when
  first-run onboarding is required)
- Recoverable failure flow: `... -> error -> standby`
- Unrecoverable/startup failure flow: `... -> error -> offline` or direct
  startup failure to `offline`
- Shutdown flow: `... -> offline`

## Observer Responsibilities

- consume runtime events only; never own runtime control flow
- map/display canonical lifecycle states consistently
- preserve error payload fields (`message`, `recoverable`, `next_state`)
- tolerate repeated `config` updates during onboarding and settings changes

## Feature Guarantees

- GUI and console mode consume the same runtime service
- first-run onboarding is runtime-owned and mode-neutral
- protected close/stop voice intents do not terminate runtime flow
- runtime logging is emitted for lifecycle transitions and observer-facing events
