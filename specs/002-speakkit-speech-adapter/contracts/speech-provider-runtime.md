# Speech Provider Runtime Contract

## Purpose

Define runtime-facing provider interfaces and selection/fallback behavior for
legacy and SpeakKit speech paths.

## Provider Modes

- `legacy`: current baseline speech path
- `speakkit`: new provider path introduced via adapters

## Provider Selection Rules

1. Runtime loads `persisted_provider` from settings/profile.
2. If persisted provider is available at startup, it becomes
   `session_provider`.
3. If persisted provider is unavailable at startup:
   - runtime uses `legacy` for this session
   - persisted provider value remains unchanged
   - degraded-mode notification is emitted
4. Provider-switch requests during active session are deferred until restart.

## Service Interface Contracts

### WakeService

- **Responsibility**: detect wake intent from recognized text or provider wake
  pipeline output.
- **Required Operations**:
  - `detect(input_text) -> WakeResult | None`
  - optional startup health check: `is_available() -> bool`
- **WakeResult shape**:

```json
{
  "action": "start",
  "phrase": "normalized wake phrase"
}
```

### SpeechToTextService

- **Responsibility**: capture and transcribe user speech.
- **Required Operations**:
  - `listen_command() -> string | null`
  - `listen_any(languages, prompt, timeout, phrase_time_limit) -> string | null`
  - `set_language(language_code) -> void`
  - optional startup health check: `is_available() -> bool`

### TextToSpeechService

- **Responsibility**: speak assistant output.
- **Required Operations**:
  - `speak(text) -> void`
  - `set_language(language_code) -> void`
  - `set_voice_gender(gender) -> void`
  - `set_speech_speed(speed) -> void`
  - optional startup health check: `is_available() -> bool`

## Fallback Contract

- Recoverable failure in active `speakkit` mode MAY fallback to `legacy`.
- Active `legacy` mode MUST NOT auto-switch to `speakkit`.
- If both providers are unavailable, runtime MUST transition to `offline` and
  require manual restart.

## Runtime Event Compatibility

Existing runtime event types remain unchanged: `status`, `system`, `config`,
`user`, `assistant`, `error`.

Provider-aware payload extensions:

- `config` event MAY include:

```json
{
  "speech_provider": "legacy|speakkit",
  "degraded_mode": true,
  "degraded_reason": "provider_unavailable_at_startup"
}
```

- `error` event MAY include:

```json
{
  "provider": "legacy|speakkit",
  "stage": "startup|wake|listening|speaking",
  "recoverable": true,
  "fallback_applied": true,
  "next_state": "standby|offline"
}
```

## Validation Expectations

- Provider-selection behavior is deterministic across restarts.
- Startup degraded-mode path preserves persisted provider value.
- Directional fallback policy is enforced.
- Dual-provider unavailability path transitions to offline.
- Runtime logs and observer events expose provider-selection and fallback
  decisions.

## Implementation Notes

- Persisted profile fields:
  - `speech_provider`
  - `pending_speech_provider`
  - `deferred_provider_switch`
- Runtime startup applies deferred provider changes before provider resolution.
- Runtime-level provider-switch requests made during an active process are
  deferred to restart and persisted in `pending_speech_provider`.
- Observer payload compatibility is preserved:
  - Existing `config` keys (`language`, `gender`, `speed`) remain intact.
  - Provider metadata is additive (`speech_provider`,
    `persisted_speech_provider`, degraded/fallback context).
