# Feature Specification: Interrupt Safety and TTS Preemption

**Feature Branch**: `[010-interrupt-safety-preemption]`  
**Created**: 2026-04-20  
**Status**: Draft  
**Input**: User description: "Read Phase 10 from docs\implementationPlan.md to do spec number 10 with best practis"

## Clarifications

### Session 2026-04-20

- Q: Should interrupt safety phrases work only in the active language or remain available bilingually at all times? -> A: Approved interrupt phrases remain available in both Arabic and English at all times as a global safety vocabulary.
- Q: What preemption latency target should define acceptable interrupt performance for release validation? -> A: Accepted interrupts should stop audible speech within 500 milliseconds in at least 95% of validation runs, with no validated case exceeding 1 second.
- Q: What runtime state should be considered the safe default after an interrupt is accepted and acknowledged? -> A: The assistant should return to standby by default after interrupt acknowledgement unless a higher-priority safety recovery state is required.
- Q: How should the assistant behave when the interrupted operation has already crossed a non-reversible point? -> A: The assistant should stop speech immediately, prevent follow-on work, and give a brief best-effort cancellation acknowledgement that the action may already be completing.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Stop Speech Immediately (Priority: P1)

As a blind or low-vision user, I need spoken output to stop immediately when I
say a supported interrupt phrase so the assistant does not keep talking over me
during an urgent moment.

**Why this priority**: If speech cannot be interrupted quickly, the assistant
becomes frustrating and unsafe in situations where the user needs silence or
control right away.

**Independent Test**: Start a long spoken response, say an approved interrupt
phrase in Arabic or English, and verify the speech stops quickly and the
assistant returns to a safe listening or standby state.

**Acceptance Scenarios**:

1. **Given** the assistant is speaking, **When** the user says `stop`,
   `cancel`, or an approved Arabic interrupt variant, **Then** the speech is
   interrupted quickly and the assistant confirms the interruption safely.
2. **Given** the assistant is speaking, **When** the user says an unrelated
   phrase, **Then** the current spoken response continues normally.
3. **Given** the assistant is speaking a long message, **When** an interrupt is
   detected near the end of playback, **Then** the assistant still stops the
   remaining speech instead of finishing the full response.

---

### User Story 2 - Cancel In-Flight Work Safely (Priority: P2)

As a user, I need interrupt commands to stop not only speech but also the
current in-flight action when that action is still safe to cancel, so the
assistant does not continue processing after I asked it to stop.

**Why this priority**: Stopping speech alone is not enough if the assistant or
an active capability continues working in the background after the user has
withdrawn the request.

**Independent Test**: Start a command or capability that produces spoken
feedback and active work, issue an approved interrupt phrase, and verify the
assistant halts or abandons the active operation and returns a safe outcome.

**Acceptance Scenarios**:

1. **Given** the assistant is handling an in-flight operation that is still
   safe to cancel, **When** the user says a supported interrupt phrase,
   **Then** the operation is cancelled promptly and the user receives a clear
   spoken acknowledgement.
2. **Given** the assistant receives an interrupt while transitioning between
   listening, thinking, and speaking, **When** the interrupt is processed,
   **Then** the runtime ends in one safe state rather than becoming stuck
   between modes.
3. **Given** a capability cannot be fully cancelled once it reaches a
   non-reversible point, **When** the user interrupts, **Then** the assistant
   must stop further speech, surface the safest available outcome, and avoid
   starting follow-on work from the interrupted flow while clearly indicating
   that the underlying action may already be completing.

---

### User Story 3 - Measurable Interrupt Reliability (Priority: P3)

As a developer or QA owner, I need interrupt latency and outcome data to be
measured consistently so regressions in stop behavior are caught before release
or field testing.

**Why this priority**: Emergency stop behavior is safety-critical, and without
measurable regression protection it can silently degrade as the speech pipeline
evolves.

**Independent Test**: Run interrupt-focused regression and smoke coverage under
normal and loaded conditions, then verify the recorded preemption latency stays
within the approved target and the final runtime state is deterministic.

**Acceptance Scenarios**:

1. **Given** interrupt handling is exercised by automated validation,
   **When** the suite runs, **Then** it records preemption latency and final
   outcome data for each tested path.
2. **Given** the assistant is under moderate runtime load, **When** a supported
   interrupt is spoken, **Then** the preemption remains bounded and does not
   degrade into unresponsive playback.
3. **Given** Arabic and English interrupt variants are part of the supported
   vocabulary, **When** regression coverage runs, **Then** both languages
   produce consistent interruption outcomes.

---

### Edge Cases

- The user says an interrupt phrase while speech is starting but before the
  full response becomes audible.
- The user says multiple interrupt phrases in quick succession.
- Background noise partially resembles `stop` or an Arabic interrupt phrase.
- The assistant is in the thinking state with no audible speech yet when the
  interrupt arrives.
- The interrupt arrives while a capability is already completing or returning a
  final result.
- The active language and the spoken interrupt phrase do not match, but the
  interrupt is still a supported global safety phrase.

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: Gives blind or low-vision users immediate control
  over speech output and active assistant work during urgent, confusing, or
  overstimulating moments.
- **Audio UX**: Interrupt phrases must be short, easy to remember, and
  acknowledged with concise spoken feedback rather than long explanations.
- **Non-Visual Operation**: The entire stop or cancel flow must work through
  speech alone, without requiring the user to look at a screen or press a UI
  control.
- **Failure Handling**: If a full cancellation is not possible, the assistant
  must still stop further speech quickly, avoid cascading work, and report the
  safest available outcome.
- **Weak-Network Behavior**: If a network-backed speech or capability provider
  stalls, times out, or becomes unavailable, the runtime-owned interrupt path
  must still stop local spoken output, suppress follow-on speech, and return a
  degraded outcome that truthfully reports whether remote work may still be
  completing.
- **Non-Verbal Feedback Needs**: No new non-verbal interrupt feedback is
  required in this phase; speech acknowledgement remains authoritative and any
  optional UI indicator stays secondary.
- **Risk Controls**: Supported interrupt phrases must remain reliable across
  Arabic and English regardless of the current prompt language, interruption
  must be bounded in time, and the runtime must recover to a safe stable state
  instead of hanging mid-flow.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST recognize the Phase 10 approved interrupt vocabulary
  as a global safety vocabulary rather than only in the currently active
  language. The canonical vocabulary for this phase is English `stop`,
  `cancel`, and `stop now`, plus Arabic `قف`, `توقف`, and `إلغاء`.
- **FR-002**: System MUST allow an approved interrupt phrase to preempt active
  spoken output before the full response finishes.
- **FR-003**: System MUST provide a clear spoken acknowledgement when an
  interrupt is accepted.
- **FR-004**: System MUST ignore unrelated speech that does not match the
  approved interrupt vocabulary.
- **FR-005**: System MUST route accepted interrupts through one consistent
  interrupt-handling path across runtime states.
- **FR-006**: System MUST stop or abandon in-flight work when that work is
  still safe to cancel.
- **FR-007**: System MUST prevent interrupted flows from continuing with extra
  spoken follow-up once the interrupt has been accepted.
- **FR-008**: System MUST return the runtime to a safe stable state after an
  interrupt outcome is resolved, defaulting to standby after acknowledgement
  unless a higher-priority safety recovery state is required.
- **FR-009**: System MUST preserve structured outcome data for accepted,
  ignored, cancelled, and partially-cancelled interrupt paths.
- **FR-010**: System MUST measure preemption latency for approved interrupt
  paths.
- **FR-011**: System MUST keep interrupt behavior bounded and reproducible
  under normal runtime load and a defined moderate-load validation scenario
  that includes one active spoken response of at least 5 seconds, one
  concurrent in-flight assistant operation that is either thinking or
  safe-to-cancel capability work, and enabled structured recovery logging in
  the same runtime session.
- **FR-012**: System MUST include automated regression coverage for interrupt
  vocabulary, preemption behavior, final runtime state, and latency recording.
- **FR-013**: System MUST keep this phase scoped to emergency stop or cancel
  behavior, TTS preemption, interrupt propagation, and validation rather than
  broad conversational command redesign.
- **FR-014**: System MUST stop spoken output immediately and provide a brief
  best-effort cancellation acknowledgement even when the interrupted operation
  can no longer be fully reversed.
- **FR-015**: System MUST preserve interrupt responsiveness during weak-network
  or provider-stall conditions by allowing local speech preemption and safe
  degraded recovery even when the underlying remote operation cannot be fully
  cancelled immediately.

### Operational & Quality Requirements

- **OQ-001**: The specification MUST identify the affected runtime layers as
  the shared runtime flow, speech output behavior, and interrupt-focused
  validation under `tests/`.
- **OQ-002**: Interrupt handling MUST define the service boundary between
  interrupt detection, spoken-output preemption, and in-flight work
  cancellation.
- **OQ-003**: Runtime-affecting interrupt behavior MUST define logging, smoke
  validation, and latency expectations for accepted and ignored interrupts,
  including a release target of speech preemption within 500 milliseconds in at
  least 95% of validation runs.
- **OQ-004**: Structured interrupt outcomes MUST continue to expose
  `spoken_text`, `status`, `payload`, and `error_code` when applicable.
- **OQ-005**: The design MUST define timeout handling and degraded-mode
  behavior for provider-backed speech or capability paths so interrupt
  validation remains truthful when network-backed work stalls or outlives local
  speech preemption.

### Key Entities *(include if feature involves data)*

- **Interrupt Vocabulary**: The approved Phase 10 safety phrases that can
  request an emergency stop or cancel action. The canonical vocabulary for this
  feature is English `stop`, `cancel`, and `stop now`, plus Arabic `قف`,
  `توقف`, and `إلغاء`.
- **Interrupt Event**: The structured record that captures the detected
  interrupt phrase, acceptance decision, affected runtime state, and final
  outcome.
- **Preemption Outcome**: The structured result of stopping speech or active
  work, including acknowledgement, cancellation status, and final safe state.
- **Preemption Latency Record**: The measurable timing record between interrupt
  detection and effective speech or work stoppage.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of approved interrupt phrases covered by the regression
  suite stop active spoken output before the original response fully completes.
- **SC-002**: At least 95% of approved Arabic and English interrupt variants in
  the regression suite are accepted as the intended stop or cancel action.
- **SC-003**: 100% of accepted interrupts covered by validation leave the
  assistant in a safe stable runtime state with no unintended follow-up speech.
- **SC-004**: Preemption latency is measured for all automated interrupt
  validation paths; accepted interrupts stop audible speech within 500
  milliseconds in at least 95% of validation runs, and no validated case
  exceeds 1 second.
- **SC-005**: Interrupt behavior remains deterministic across normal and
  moderate-load validation runs, with no hangs or unbounded playback after an
  accepted stop request.

## Assumptions

- The assistant already has basic interrupt concepts, but the current behavior
  is not yet reliable enough for assistive emergency stop use.
- Arabic and English remain the supported spoken languages for safety-critical
  interrupt phrases in this phase, and both languages remain valid even when
  the active prompt language differs.
- The moderate-load validation profile for this phase means one long active TTS
  response, one concurrent in-flight assistant operation, and structured
  logging enabled in the same runtime session rather than synthetic
  high-concurrency stress testing.
- Some in-flight operations may be safe to cancel while others may only support
  best-effort stop behavior once they near completion.
- The runtime already exposes enough state transitions to define a safe stable
  end state after an interrupt, with standby as the default recovery state for
  accepted interrupts.
- This phase focuses on speech preemption and interrupt propagation rather than
  redesigning the full command model or wake strategy.
