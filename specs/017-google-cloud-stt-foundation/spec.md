# Feature Specification: Google Cloud STT Foundation and Strict Fallback Contracts

**Feature Branch**: `[018-google-cloud-stt-foundation]`  
**Created**: 2026-04-24  
**Status**: Draft  
**Input**: User description: "Read Phase 17 from docs\implementationPlan.md to do spec number 17 with best practis"

## Clarifications

### Session 2026-04-24

- Q: What should the default rollout posture be for the new STT controls? -> A: Cloud primary off by default, strict Vosk fallback opt-in independently, and PocketSphinx compatibility off.
- Q: What happens if cloud recognition fails while strict Vosk fallback is disabled? -> A: Return no usable transcript and use existing recovery; never fall through to PocketSphinx or unrestricted local recognition.
- Q: What default cloud attempt bound should planning and tests assume? -> A: A 3-second cloud timeout with at most one transient retry inside the existing listen window.
- Q: How should cloud-detected language affect the user's active language setting? -> A: Report detected language as metadata only; the selected profile language remains authoritative until the user changes it.
- Q: What privacy boundary should apply to cloud credentials and recognition content? -> A: Do not persist cloud credentials or raw utterances in the user profile, logs, or release artifacts by default.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Use Cloud-Grade Recognition When Available (Priority: P1)

As a blind or low-vision user, I want the assistant to understand short spoken
commands more reliably in Arabic, English, and noisy wearable conditions when
cloud recognition is explicitly available, so high-value commands are less
likely to be missed or misheard.

**Why this priority**: Speech recognition quality directly affects whether the
assistant can be trusted in headless assistive use, especially for Arabic and
mixed-language commands.

**Independent Test**: Enable cloud-primary recognition in a controlled run with
valid availability, submit representative short wake and command utterances,
and verify the assistant receives structured candidate results without changing
the normal command flow.

**Acceptance Scenarios**:

1. **Given** cloud recognition is enabled and available, **When** the user gives
   a short command, **Then** the assistant receives a structured recognition
   candidate with transcript, confidence when available, language context, and
   provider source.
2. **Given** cloud recognition returns multiple likely transcripts, **When** the
   assistant evaluates the utterance, **Then** the alternatives remain available
   for downstream confidence and recovery decisions.
3. **Given** cloud recognition is not explicitly enabled, **When** the assistant
   starts or listens, **Then** existing local-compatible behavior remains
   available without forcing cloud usage.
4. **Given** cloud recognition detects a language different from the selected
   profile language, **When** recognition results are reported, **Then** the
   detected language is available as metadata only and the user's active
   language setting remains unchanged.

---

### User Story 2 - Fail Safely When Cloud Recognition Cannot Be Used (Priority: P2)

As a user depending on a wearable assistant, I want missing credentials, weak
network, quota limits, timeouts, or empty cloud responses to degrade into a
safe bounded fallback instead of crashing, hanging, or guessing arbitrary text.

**Why this priority**: Cloud recognition improves quality only if unavailable
states are predictable and safe for field use.

**Independent Test**: Exercise credential-missing, timeout, auth, quota,
service-unavailable, empty-result, and unknown-failure cases, then verify each
case produces a stable reason code and a safe fallback or recovery path.

**Acceptance Scenarios**:

1. **Given** credentials are missing, **When** the assistant starts and listens,
   **Then** startup succeeds and recognition reports a credential-related
   unavailable state instead of crashing.
2. **Given** the network stalls or the cloud provider times out, **When** a
   short utterance is captured, **Then** listening remains bounded by the
   configured timeout expectation, including no more than one transient retry,
   and proceeds to the approved fallback path.
3. **Given** cloud recognition returns no usable speech, **When** the assistant
   evaluates the turn, **Then** the result is classified as empty rather than
   treated as a valid command.
4. **Given** cloud recognition fails and strict Vosk fallback is disabled,
   **When** the assistant evaluates the turn, **Then** it returns no usable
   transcript and uses existing recovery rather than trying PocketSphinx or
   unrestricted local recognition.

---

### User Story 3 - Constrain Local Fallbacks to Safe Vocabularies (Priority: P3)

As a maintainer preparing the assistant for pilot use, I want Vosk fallback
recognition to use strict wake, command, confirmation, and closed-choice
vocabularies, so local recognition cannot invent unsupported command text when
cloud recognition is unavailable.

**Why this priority**: Strict fallback contracts protect command safety while
still allowing offline or degraded operation for bounded interaction modes.

**Independent Test**: Run wake, command, confirmation, and onboarding
closed-choice turns with valid phrases, near misses, unrelated speech, and
silence, then verify only vocabulary-approved utterances become usable
transcripts.

**Acceptance Scenarios**:

1. **Given** the assistant is in standby wake mode, **When** Vosk fallback
   recognition is used, **Then** only approved wake aliases can produce a usable
   wake transcript.
2. **Given** the assistant is waiting for a command or confirmation, **When**
   unrelated speech is heard by Vosk fallback, **Then** the fallback
   returns no usable transcript instead of producing arbitrary command text.
3. **Given** the assistant is in a closed-choice onboarding turn, **When** the
   user gives an unsupported answer, **Then** the assistant preserves the guided
   context and recovers rather than treating the answer as free dictation.

---

### User Story 4 - Keep Recognition Hints Deterministic and Rollback-Friendly (Priority: P4)

As a release owner, I want phrase hints, provider selection, Vosk fallback
behavior, and PocketSphinx compatibility to be deterministic and configurable, so
the team can validate changes, diagnose issues, and roll back safely.

**Why this priority**: This phase is foundational; it must make later command
recognition improvements safer without forcing a one-way migration.

**Independent Test**: Generate phrase hints repeatedly for wake, command,
confirmation, and onboarding modes, then verify the same approved hints and
fallback contracts are produced across runs and PocketSphinx compatibility stays
inactive unless explicitly enabled.

**Acceptance Scenarios**:

1. **Given** phrase hints are generated for a recognition mode, **When** the same
   catalog and closed-vocabulary inputs are used, **Then** the generated hints
   are repeatable and include expected English, Arabic, bilingual, phonetic, and
   common misrecognition variants.
2. **Given** PocketSphinx is not explicitly enabled for compatibility,
   **When** wake or command recognition runs, **Then** it is not considered part
   of the production accuracy path.
3. **Given** a rollback configuration disables cloud-primary behavior, **When**
   the assistant starts, **Then** the existing runtime architecture remains
   usable without changing user-facing command flows.
4. **Given** recognition diagnostics or release artifacts are produced,
   **When** they describe provider behavior, **Then** they include field-safe
   metadata without storing cloud credentials or raw utterances by default.

### Edge Cases

- Cloud credentials are absent, malformed, expired, or not readable at startup.
- Cloud recognition is enabled but the network is offline, slow, or
  intermittently unavailable during a short utterance.
- Cloud recognition returns alternatives with low or missing confidence values.
- The selected language, detected language, and user utterance language do not
  fully match, especially for Arabic-English mixed speech; detected language
  must not silently overwrite the selected profile language.
- The user speaks a safety-critical command in noisy wearable conditions and
  fallback recognition must prefer safe non-resolution over guessing.
- A Vosk fallback grammar does not contain the heard phrase and must return no
  usable transcript rather than unrestricted text.
- Strict Vosk fallback is disabled during rollback, and the system must use
  existing recovery instead of trying PocketSphinx or free-form local fallback.
- Closed-choice onboarding answers overlap with command words or wake aliases.
- PocketSphinx is accidentally available in the environment but
  has not been explicitly enabled for compatibility debugging.
- Headless operation must expose enough spoken feedback and safe recovery
  behavior without requiring GUI inspection.
- Logging and diagnostics must remain field-safe and avoid retaining raw user
  utterances by default.
- Cloud credential material must never be stored in the user profile, logs, or
  release artifacts by default.

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: Blind and low-vision users receive a stronger speech
  recognition foundation for short assistive commands while retaining safe
  behavior when cloud recognition is unavailable.
- **Audio UX**: Recognition failures must lead to short, clear recovery prompts
  or bounded fallback behavior rather than silence, crashes, or confusing
  command execution.
- **Non-Visual Operation**: Provider availability, fallback decisions, and
  recovery outcomes must remain understandable through voice-first behavior and
  field-safe logs without relying on the GUI.
- **Failure Handling**: Credential, network, timeout, quota, service, empty
  result, and unknown failures must be classified consistently and must not
  produce arbitrary command text. Cloud attempts should remain bounded by a
  3-second default timeout and at most one transient retry inside the existing
  listen window.
- **Risk Controls**: Wake, command, confirmation, and closed-choice Vosk
  fallback modes must use strict allowed vocabularies; unsupported speech must
  resolve to no usable transcript or guided recovery rather than unsafe
  guessing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide an optional production-grade cloud speech
  recognition foundation for short utterances behind the existing
  provider-aware speech recognition boundary.
- **FR-002**: Cloud recognition MUST NOT be mandatory for startup, local
  development, tests, or field use when credentials or network access are
  unavailable.
- **FR-003**: Recognition results from the cloud path MUST be represented as
  structured candidates that include transcript text, provider source,
  confidence when available, alternatives when available, language context, and
  status metadata.
- **FR-004**: Cloud recognition failures MUST be classified into stable reason
  codes covering missing credentials, network timeout, authentication failure,
  quota failure, service unavailability, empty result, and unknown failure. The
  required codes are `cloud_credentials_missing`, `cloud_network_timeout`,
  `cloud_auth_error`, `cloud_quota_error`, `cloud_service_unavailable`,
  `cloud_empty_result`, and `cloud_unknown_failure`.
- **FR-005**: The system MUST expose configuration controls for cloud-primary
  enablement, strict Vosk fallback enablement, PocketSphinx compatibility,
  cloud timeout, and maximum candidate alternatives. The required controls are
  `EGB_STT_CLOUD_PRIMARY_ENABLED`, `EGB_STT_STRICT_VOSK_FALLBACK_ENABLED`,
  `EGB_STT_ENABLE_SPHINX_COMPAT`, `EGB_STT_CLOUD_TIMEOUT_S`, and
  `EGB_STT_CLOUD_MAX_ALTERNATIVES`.
- **FR-006**: New recognition behavior MUST default conservatively so cloud
  primary recognition and strict local fallback can be enabled independently.
- **FR-006a**: The default rollout posture MUST keep cloud primary recognition
  off, strict Vosk fallback independently opt-in, and PocketSphinx compatibility
  off unless explicit configuration enables each behavior.
- **FR-007**: Existing public listening interactions MUST remain compatible for
  free listening, command listening, command-result listening, and bounded
  command-window listening.
- **FR-008**: The runtime-facing command recognition result contract MUST remain
  compatible with existing downstream confidence, rescue, parser, resolver, and
  dispatcher behavior.
- **FR-009**: The system MUST generate deterministic phrase hints from the
  command inventory, closed-vocabulary dialog contexts, canonical wake aliases,
  curated assistive wearable phrases, and safety-critical commands.
- **FR-010**: Phrase hints MUST be mode-specific for wake, command,
  confirmation, and onboarding recognition contexts.
- **FR-011**: Phrase hints MUST include supported English, Arabic, bilingual,
  phonetic, and common speech-recognition mistake variants.
- **FR-011a**: Phrase hints and diagnostics MUST be generated from approved
  catalogs and curated variants, not from persisted raw user utterances by
  default.
- **FR-012**: Vosk fallback recognition MUST support explicit strict modes for
  wake grammar, command inventory, and closed-choice interactions.
- **FR-013**: Strict Vosk fallback modes MUST only return usable transcripts
  that match the active grammar or inventory for the current interaction mode.
- **FR-014**: In command mode, Vosk fallback recognition MUST NOT produce
  arbitrary free-form command text as a production command candidate.
- **FR-015**: When strict Vosk fallback cannot match the active grammar, it
  MUST return no usable transcript and allow existing recovery behavior to
  decide the next user-facing prompt.
- **FR-015a**: When cloud recognition fails and strict Vosk fallback is
  disabled, the system MUST return no usable transcript and use existing
  recovery behavior instead of falling through to PocketSphinx or unrestricted
  local recognition.
- **FR-016**: PocketSphinx MUST be excluded from the default production wake and
  command accuracy path unless an explicit compatibility control enables it for
  debugging.
- **FR-017**: Rollback controls MUST allow cloud-primary behavior and strict
  fallback behavior to be disabled without changing the assistant's public
  command flow.
- **FR-018**: Diagnostics MUST identify recognition source, failure reason,
  fallback decision, and latency category while remaining field-safe and
  avoiding raw user utterance retention by default.
- **FR-019**: Cloud-detected language MUST be reported as recognition metadata
  only and MUST NOT change the user's selected profile language unless the user
  explicitly changes language settings.
- **FR-020**: Cloud credential material MUST NOT be persisted in the user
  profile, logs, or release artifacts by default.

### Operational & Quality Requirements

- **OQ-001**: The affected runtime layer is the speech recognition/provider
  boundary; the feature MUST NOT redesign the assistant runtime loop, parser,
  dispatcher, resolver, or provider identity model.
- **OQ-002**: The external speech-provider boundary MUST own credential
  availability checks, short-utterance recognition, timeout handling, transient
  retry policy, candidate extraction, and language metadata reporting.
- **OQ-003**: Runtime-affecting behavior MUST define field-safe logging, smoke
  validation, and bounded latency expectations for cloud and fallback paths.
- **OQ-003a**: The default cloud recognition attempt MUST use a 3-second timeout
  and no more than one retry for transient failures within the existing listen
  window.
- **OQ-004**: Recognition outcomes MUST preserve structured result fields
  needed by downstream policy, including spoken text or transcript, status,
  provider/source, confidence when available, payload metadata, and error code
  when applicable.
- **OQ-005**: Validation MUST cover successful cloud candidate extraction with
  fake responses, missing credentials, timeout, empty result, and each stable
  cloud failure reason without requiring real cloud credentials.
- **OQ-006**: Validation MUST prove strict fallback grammars are deterministic
  for wake, command, confirmation, and closed-choice contexts.
- **OQ-007**: Validation MUST prove PocketSphinx is not used in default
  production wake or command decisions.
- **OQ-008**: Validation MUST prove cloud language metadata does not silently
  mutate the selected profile language.
- **OQ-009**: Validation MUST prove diagnostics and release artifacts do not
  persist cloud credentials or raw utterances by default.

### Key Entities *(include if feature involves data)*

- **Recognition Candidate**: A structured result representing a possible
  transcript, its source, confidence when available, alternatives, language
  context, and status metadata.
- **Provider Availability State**: The current readiness of the cloud or local
  recognition path, including whether credentials, network, quota, or service
  availability allow recognition.
- **Failure Reason Code**: A stable category explaining why a recognition path
  could not produce a usable result.
- **Phrase Hint Set**: A deterministic collection of phrases for one
  recognition context, including approved variants and safety-critical terms.
- **Fallback Grammar Contract**: The allowed vocabulary and no-match behavior
  for a strict Vosk fallback mode.
- **Recognition Configuration**: User or environment-controlled settings that
  enable or disable cloud primary recognition, strict Vosk fallback, PocketSphinx
  compatibility, timeouts, and maximum alternatives.
- **Language Metadata**: The selected and detected language values associated
  with a recognition attempt, where detected language is informational unless
  the user explicitly changes their language setting.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With cloud recognition explicitly enabled and available, at least
  one representative command-recognition flow produces a structured cloud
  candidate without changing the existing user-facing command journey.
- **SC-002**: In environments with no cloud credentials, startup and automated
  validation complete successfully 100% of the time without requiring cloud
  access.
- **SC-003**: Every defined cloud failure category maps to one stable reason
  code and a safe fallback or recovery outcome in validation.
- **SC-004**: Wake, command, confirmation, and closed-choice fallback grammars
  produce deterministic outputs across repeated validation runs.
- **SC-005**: Default production wake and command recognition decisions include
  zero PocketSphinx candidates unless compatibility is explicitly enabled.
- **SC-006**: Phrase-hint validation confirms expected English, Arabic,
  bilingual, phonetic, and common misrecognition variants for wake and command
  contexts.
- **SC-007**: Cloud timeout validation shows unavailable or stalled cloud
  recognition resolves through a bounded failure or fallback path within the
  existing listen window using the 3-second default timeout and at most one
  transient retry.
- **SC-008**: Language-mismatch validation shows cloud-detected language is
  reported without changing the selected profile language in 100% of covered
  cases.
- **SC-009**: Privacy validation shows no cloud credential material or raw user
  utterances are written to the user profile, logs, or release artifacts by
  default.

## Assumptions

- Phase 17 is a foundation phase and intentionally does not change the public
  runtime loop, command parser, dispatcher, resolver, or provider IDs.
- Cloud recognition is valuable for quality but remains optional because field
  devices may lack credentials, network access, or quota.
- Strict Vosk fallback remains necessary for safe wake, command,
  confirmation, and closed-choice behavior when cloud recognition is disabled
  or unavailable.
- Existing recovery and confidence policies will consume structured
  recognition outcomes rather than being replaced in this phase.
- Phrase hints and diagnostics are intended to improve recognition quality and
  validation without storing raw user utterances by default.
- Cloud credential configuration is supplied outside the user profile and is
  checked at runtime without being copied into project-managed release
  artifacts.
