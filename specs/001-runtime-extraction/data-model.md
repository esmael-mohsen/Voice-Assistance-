# Data Model: Runtime Extraction

## Runtime Session

- **Purpose**: Represents one active assistant lifecycle from startup through
  standby, interaction, onboarding, recovery, and shutdown.
- **Fields**:
  - `session_id`: unique identifier for the active runtime instance
  - `mode`: `gui` or `console`
  - `state`: lifecycle state for the current session
  - `configured`: whether a saved user profile already exists
  - `active`: whether the assistant is actively processing post-wake commands
  - `language`: current active language code
  - `voice_gender`: current active voice selection
  - `speech_speed`: current speaking-speed multiplier
  - `stop_requested`: whether shutdown has been requested
  - `last_error`: latest runtime error classification, if any
- **Validation Rules**:
  - `mode` must be one of the supported runtime entry modes
  - `state` must follow the allowed lifecycle transitions below
  - `speech_speed` must remain within the bounds enforced by settings
- **Relationships**:
  - emits many `RuntimeEvent` records
  - references one current `SettingsSnapshot`
  - may own one `OnboardingState` while first-run setup is incomplete

### Runtime Session State Transitions

- `offline -> standby`: successful startup and dependency attachment
- `standby -> wake`: wake phrase recognized
- `wake -> setup`: first-run onboarding required
- `wake -> listening`: configured user is ready for commands
- `setup -> listening`: onboarding completed successfully
- `listening -> thinking`: command accepted for dispatch
- `thinking -> speaking`: assistant is producing a spoken outcome
- `speaking -> listening`: interactive session continues
- `speaking -> standby`: session returns to passive state after response
- `any active state -> error`: recoverable failure detected
- `error -> standby`: recoverable failure handled
- `startup/init -> offline`: unrecoverable startup or initialization failure
- `any state -> offline`: explicitly unrecoverable runtime exception or
  controlled shutdown completion

## Runtime Event

- **Purpose**: Mode-neutral notification emitted by the shared runtime to any
  observer.
- **Fields**:
  - `type`: one of `status`, `system`, `config`, `user`, `assistant`, `error`
  - `session_id`: identifier of the runtime session that produced the event
  - `payload`: event-specific data
  - `timestamp`: creation time for ordering and debugging
- **Payload Shapes**:
  - `status`: `{ state }`
  - `system`: `{ text }`
  - `config`: `{ language, gender, speed }`
  - `user`: `{ text }`
  - `assistant`: `{ text }`
  - `error`: `{ message, recoverable, next_state }`
- **Validation Rules**:
  - `status.state` must use the canonical lifecycle vocabulary
  - `error.next_state` must be `standby` for recoverable failures or `offline`
    for unrecoverable failures
  - `config` events must reflect the latest settings snapshot

## Settings Snapshot

- **Purpose**: Immutable view of settings the runtime uses for a single event or
  lifecycle step.
- **Fields**:
  - `language`
  - `voice_gender`
  - `speech_speed`
  - `username`
- **Validation Rules**:
  - `language` must be a supported language code
  - `voice_gender` must match a supported profile
  - `speech_speed` must stay within configured min and max values

## Onboarding State

- **Purpose**: Tracks progress through the first-run voice setup flow while the
  runtime remains mode neutral.
- **Fields**:
  - `required`: whether onboarding is still needed
  - `selected_language`
  - `selected_voice_gender`
  - `selected_speech_speed`
  - `proposed_username`
  - `confirmed_username`
  - `step`: current onboarding step (`language`, `voice`, `speed`, `name`,
    `confirmation`, `complete`)
- **Validation Rules**:
  - `step` must advance in a valid sequence or repeat the current step after a
    failed confirmation
  - `required` becomes `false` only when `confirmed_username` is present

## Runtime Observer

- **Purpose**: Consumer of runtime events, such as the GUI bridge or console
  output path.
- **Fields**:
  - `observer_id`
  - `mode`
  - `supported_event_types`
- **Responsibilities**:
  - subscribe to runtime events without owning runtime control flow
  - present lifecycle changes and messages for its mode
  - avoid mutating core runtime state directly
