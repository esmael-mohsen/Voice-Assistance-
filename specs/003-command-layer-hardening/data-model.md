# Data Model: Command Layer Hardening

## CommandCatalogEntry

- **Purpose**: Defines one supported command intent and the validation rules
  needed to recognize and route it safely.
- **Fields**:
  - `intent_id`: canonical command key such as `enable_obstacle_detection`
  - `category`: `capability | settings | system`
  - `risk_level`: `normal | elevated | protected`
  - `keywords`: supported Arabic, English, and mixed utterance variants
  - `base_threshold`: minimum fuzzy-match score for initial acceptance
  - `ambiguity_margin`: minimum lead over competing matches
  - `requires_parameters`: boolean
  - `requires_confirmation`: boolean
  - `follow_up_source`: boolean indicating the command may seed one-turn context
  - `follow_up_target`: optional intent allowed to consume that context
  - `route_target`: `controller | settings_manager | resolver_internal`
- **Validation Rules**:
  - `intent_id` must be unique
  - `risk_level=protected` implies `category=system`
  - `requires_confirmation=true` only for high-consequence system commands in
    this phase
  - `ambiguity_margin` must be non-negative
- **Relationships**:
  - produces `ParsedCommandIntent`
  - informs `CommandResolution`

## ParsedCommandIntent

- **Purpose**: Captures the parser's best normalized interpretation of the raw
  utterance before execution routing.
- **Fields**:
  - `raw_text`
  - `normalized_text`
  - `intent_id`
  - `category`
  - `risk_level`
  - `matched_keyword`
  - `score`
  - `threshold`
  - `runner_up_intent` (optional)
  - `runner_up_score` (optional)
  - `accepted`: boolean
  - `rejection_reason`: optional code such as `below_threshold` or `ambiguous`
  - `metadata`: optional parse hints for parameter extraction
- **Validation Rules**:
  - `accepted=true` requires `score >= threshold`
  - ambiguous matches require a `rejection_reason`
  - `intent_id` must map to an existing `CommandCatalogEntry`
- **Relationships**:
  - input to `CommandResolution`

## CommandResolution

- **Purpose**: Represents the resolver's execution decision after parameter
  extraction, follow-up context, and safety checks are applied.
- **Fields**:
  - `intent_id`
  - `category`
  - `route_target`
  - `validation_status`: `ready | clarification_required | confirmation_required | rejected | failed`
  - `params`: normalized parameter map
  - `used_session_context`: boolean
  - `session_context_updates`: set of changes to apply after resolution
  - `spoken_text`
  - `error_code`: optional machine-readable failure or rejection code
  - `controller_result`: optional raw downstream return value
- **Validation Rules**:
  - `validation_status=ready` requires a route target and resolved parameters
    sufficient for execution
  - `validation_status=clarification_required` or
    `confirmation_required` must include `spoken_text`
  - `used_session_context=true` requires a valid `SessionCommandContext`
- **Relationships**:
  - consumes `ParsedCommandIntent`
  - produces `CommandExecutionResult`
  - reads and updates `SessionCommandContext`

## CommandExecutionResult

- **Purpose**: Normalized structured outcome returned by dispatcher to runtime
  consumers.
- **Fields**:
  - `intent_id`: optional for rejected no-match cases
  - `category`: optional for unmatched input
  - `status`: `success | clarification_required | confirmation_required | rejected | failed`
  - `spoken_text`
  - `payload`: optional structured data for downstream consumers
  - `error_code`: optional machine-readable code
  - `metadata`: optional debugging and observability fields such as score,
    threshold, route, or follow-up usage
- **Validation Rules**:
  - every result must include `status` and `spoken_text`
  - `payload` must be JSON-serializable or safely representable
  - `error_code` is required for `rejected` and `failed` states
- **Relationships**:
  - returned by `core.dispatcher`
  - consumed by `core.assistant_runtime` and tests

### Execution Result State Transitions

- `parsed accepted + resolver ready -> success`
- `parsed accepted + params missing -> clarification_required`
- `protected system matched + confirmation pending -> confirmation_required`
- `weak or ambiguous match -> rejected`
- `controller or resolver failure -> failed`

## SessionCommandContext

- **Purpose**: Holds the short-lived command context that may affect exactly one
  immediate follow-up command.
- **Fields**:
  - `last_face_id`: optional identifier from `recognize_face`
  - `follow_up_source_intent`: optional originating intent
  - `follow_up_target_intent`: optional allowed consuming intent
  - `remaining_follow_ups`: integer, capped at `1`
  - `pending_confirmation_intent`: optional protected system intent awaiting
    explicit confirmation
  - `pending_confirmation_payload`: optional route data needed if confirmed
  - `pending_clarification_intent`: optional intent awaiting one clarification
  - `clarification_attempts`: integer, capped at `1`
- **Validation Rules**:
  - `remaining_follow_ups` must be `0` or `1`
  - protected confirmation state expires after one response turn
  - clarification attempts must not exceed `1`
  - context must be cleared after successful consumption or expiry
- **Relationships**:
  - referenced by `CommandResolution`

### Session Context Transitions

- `recognize_face success -> store last_face_id and allow one follow-up`
- `recognize_emotion consumes face context -> clear follow-up state`
- `protected system command matched -> set pending confirmation`
- `confirmation received -> execute stored protected action and clear state`
- `unrelated or expired next turn -> clear stored follow-up or confirmation`
