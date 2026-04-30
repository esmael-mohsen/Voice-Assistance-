# Feature Specification: Speech Abstraction and SpeakKit Adapter

**Feature Branch**: `[002-speakkit-speech-adapter]`  
**Created**: 2026-04-17  
**Status**: Draft  
**Input**: User description: "Phase 2 from docs/implementationPlan.md"

## Clarifications

### Session 2026-04-17

- Q: How should provider switching behave during an active session? -> A: Apply provider changes on next restart only.
- Q: What should happen if both primary and fallback providers fail? -> A: Transition to offline and require manual restart.
- Q: Should provider mode persist across restarts? -> A: Persist provider mode in user profile and reuse by default.
- Q: How should cross-provider fallback direction work? -> A: SpeakKit may fallback to legacy; legacy must not auto-switch to SpeakKit.
- Q: What if the persisted provider is unavailable at startup? -> A: Use legacy for this session, keep saved provider unchanged, and notify degraded mode.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preserve Stable Speech Experience (Priority: P1)

As an operator, I can keep using the assistant with the existing speech
behavior while the speech pipeline is reorganized behind a clear provider
boundary.

**Why this priority**: Current behavior must remain usable before introducing a
new provider path.

**Independent Test**: Start the assistant in normal mode and confirm wake,
recognition, and spoken responses still complete common flows without requiring
new provider setup.

**Acceptance Scenarios**:

1. **Given** a configured assistant using the existing speech path, **When**
   the user runs a standard wake-and-command flow, **Then** the assistant
   completes the interaction with expected spoken confirmation.
2. **Given** the speech abstraction layer is enabled, **When** no new provider
   is selected, **Then** the assistant continues to use legacy behavior without
   breaking baseline flows.

---

### User Story 2 - Enable SpeakKit as a Selectable Provider (Priority: P2)

As a product integrator, I can enable SpeakKit as the active speech provider so
the same assistant behavior works through an interchangeable provider model.

**Why this priority**: This delivers the phase goal of structured SpeakKit
integration while keeping architecture clean and replaceable.

**Independent Test**: Enable the SpeakKit provider and verify wake, speech
input, and speech output flows complete the same representative scenarios as
the legacy path.

**Acceptance Scenarios**:

1. **Given** provider selection is set to SpeakKit, **When** the assistant
   starts and handles user commands, **Then** speech interactions are processed
   through the SpeakKit provider path and user-visible outcomes remain
   consistent.
2. **Given** provider selection is changed between legacy and SpeakKit, **When**
   the assistant restarts, **Then** the selected provider is used without
   changing user-facing command semantics.
3. **Given** a provider mode was selected in a previous session, **When** the
   assistant starts again without a new selection request, **Then** the
   previously selected provider mode is reused by default.

---

### User Story 3 - Recover Safely from Provider Failures (Priority: P3)

As a reliability owner, I can rely on fallback behavior when the primary speech
provider fails so the assistant remains usable and does not enter unsafe loops.

**Why this priority**: Failure handling is required for assistive reliability
and aligns with constitution safety and degraded-mode requirements.

**Independent Test**: Simulate primary provider failures during wake, speech
input, and speech output, then confirm the assistant degrades safely using the
fallback path and clearly communicates degraded operation.

**Acceptance Scenarios**:

1. **Given** the primary provider is unavailable at startup, **When** the
   assistant initializes, **Then** it activates the fallback provider and emits
   a recoverable status message.
2. **Given** the primary provider fails during runtime, **When** a speech step
   cannot complete, **Then** the assistant transitions through a recoverable
   error flow and returns to an operable listening-ready state.
3. **Given** both primary and fallback providers fail, **When** no speech path
   remains operational, **Then** the assistant transitions to offline and
   requires manual restart.
4. **Given** SpeakKit is active and fails recoverably, **When** fallback is
   applied, **Then** legacy provider mode is used for continued operation.
5. **Given** legacy mode is active and fails recoverably, **When** recovery is
   attempted, **Then** the assistant does not auto-switch to SpeakKit.
6. **Given** persisted provider selection points to an unavailable provider at
   startup, **When** the assistant initializes, **Then** it uses legacy for the
   current session, keeps saved provider selection unchanged, and announces
   degraded mode.

### Edge Cases

- The selected provider is missing required credentials or initialization
  context.
- Wake detection succeeds but speech recognition fails repeatedly due to noisy
  input.
- Speech output provider times out after command completion, requiring a safe
  fallback response.
- Provider switching is requested while the assistant is already active; the
  change is deferred and applied on next restart.
- Both primary and fallback speech providers fail in the same session.
- Legacy mode fails and no same-mode recovery is possible; SpeakKit is not
  auto-enabled as fallback.
- Persisted provider is unavailable at startup; runtime uses temporary legacy
  fallback without overwriting saved provider preference.
- Headless usage requires full interaction continuity without any GUI dependency.

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: Users maintain consistent voice-first operation even
  when providers are switched or degraded.
- **Audio UX**: Spoken confirmations remain brief, clear, and state-aware during
  normal and fallback operation.
- **Non-Visual Operation**: All core flows remain fully operable without screen
  interaction.
- **Failure Handling**: Provider startup/runtime failures result in explicit,
  recoverable messaging and a usable fallback path.
- **Risk Controls**: Provider failures must not silently terminate the assistant
  runtime or block emergency-stop-safe behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST define a provider-agnostic speech contract covering
  wake detection, speech-to-text input, and text-to-speech output.
- **FR-002**: System MUST support a legacy provider mode that preserves current
  user-visible speech behavior.
- **FR-003**: System MUST support a SpeakKit provider mode that can be selected
  as the active speech path.
- **FR-004**: Users or operators MUST be able to select which speech provider
  mode is active before runtime interaction begins.
- **FR-005**: System MUST apply the selected provider consistently across wake,
  listening, and speaking stages in a single runtime session.
- **FR-006**: System MUST detect provider initialization and runtime failures
  and classify them as recoverable or unrecoverable.
- **FR-007**: System MUST execute a fallback speech path when the active
  provider fails in a recoverable way.
- **FR-008**: System MUST preserve command intent outcomes across provider modes
  so user commands produce equivalent results.
- **FR-009**: System MUST emit observable runtime events that indicate active
  provider mode, fallback activation, and failure transitions.
- **FR-010**: System MUST defer any provider-switch request received during an
  active session and apply it only after the next assistant restart.
- **FR-011**: System MUST transition to offline and require manual restart when
  both primary and fallback providers are unavailable.
- **FR-012**: System MUST persist the selected provider mode in user settings
  and reuse it as the default for subsequent restarts.
- **FR-013**: System MUST allow recoverable fallback from active SpeakKit mode
  to legacy mode.
- **FR-014**: System MUST NOT auto-switch from active legacy mode to SpeakKit
  during recoverable fallback handling.
- **FR-015**: System MUST use legacy mode for the current session when the
  persisted provider is unavailable at startup, MUST preserve the persisted
  provider selection value, and MUST emit a degraded-mode notification.

### Operational & Quality Requirements

- **OQ-001**: The specification MUST identify affected runtime layers for speech
  provider selection, lifecycle orchestration, and fallback handling.
- **OQ-002**: Provider integration MUST be bounded by explicit adapter/service
  interfaces so providers can be replaced without command-layer rewrites.
- **OQ-003**: Runtime-impacting provider behavior MUST define smoke validation
  and reliability expectations for startup, wake, listening, and speaking.
- **OQ-004**: Failure paths MUST define user-facing degraded-mode behavior and
  structured observability expectations for troubleshooting.

### Key Entities *(include if feature involves data)*

- **SpeechProviderProfile**: Declares provider identity, capability support,
  health status, and fallback eligibility.
- **SpeechProviderSelection**: Represents the currently selected provider mode
  and activation scope for a runtime session, including persisted default
  selection.
- **SpeechInteractionLifecycleEvent**: Represents provider-specific lifecycle
  and failure events emitted to observers for monitoring and validation.
- **FallbackActivationRecord**: Captures when fallback is triggered, why it was
  triggered, and what recovery path was applied.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In validation runs, at least 9 out of 10 representative
  wake-and-command scenarios complete successfully in legacy mode and in
  SpeakKit mode.
- **SC-002**: In at least 95% of recoverable provider-failure simulations, the
  assistant returns to an operable listening-ready state within 5 seconds.
- **SC-003**: 100% of tested startup failures in the primary provider path
  trigger explicit degraded-mode behavior instead of silent termination.
- **SC-004**: Observability checks confirm provider selection and fallback
  transition events are present for all validation scenarios.

## Assumptions

- SpeakKit is introduced as a selectable provider path, not as a full system
  replacement.
- The existing assistant behavior remains the baseline for acceptance.
- The project continues to support both GUI debug and headless operation paths.
- Provider selection is persisted in the user profile and can be changed before
  interactive runtime starts.
- Fallback behavior prioritizes usability and safety over feature completeness
  during degraded operation.
