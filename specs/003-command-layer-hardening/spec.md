# Feature Specification: Command Layer Hardening

**Feature Branch**: `[003-command-layer-hardening]`  
**Created**: 2026-04-17  
**Status**: Draft  
**Input**: User description: "Phase 3 from docs/implementationPlan.md"

## Clarifications

### Session 2026-04-17

- Q: What safeguard should protected system commands use? → A: Require confirmation only for high-consequence system commands; use stricter matching for lower-risk system commands.
- Q: What should Phase 3 include? → A: Harden only the current supported command set; do not add new commands in this phase.

### Session 2026-04-18

- Q: How long should follow-up command context stay active? → A: Keep context for one immediate follow-up command only.
- Q: How should missing or unclear parameters be handled? → A: Ask for clarification once, then fail safely if still unclear.
- Q: What minimum regression coverage should this phase protect? → A: Cover protected system commands, everyday assistant commands, and highest-value existing capability commands.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trust Everyday Commands (Priority: P1)

As an operator, I can speak the assistant's common Arabic and English commands
and get the intended outcome without accidental activations or confusing
misfires.

**Why this priority**: Command trust is the foundation for every later
capability. If core commands are unreliable, the assistant is not safe or
useful enough to extend.

**Independent Test**: Run a regression set of high-priority Arabic and English
commands across protected system commands, everyday assistant commands, and
highest-value existing capability commands, including near-miss phrases, and
confirm intended commands succeed while false positives are safely rejected.

**Acceptance Scenarios**:

1. **Given** a supported high-priority command spoken clearly, **When** the
   assistant processes it, **Then** it resolves to the intended action and
   returns an appropriate spoken response.
2. **Given** a phrase that is similar to a supported command but does not meet
   the validation rules, **When** the assistant processes it, **Then** it does
   not trigger the wrong action.
3. **Given** a supported command spoken in Arabic or English, **When** the
   assistant processes it in GUI or console mode, **Then** the user-visible
   behavior stays equivalent.

---

### User Story 2 - Return Structured Command Outcomes (Priority: P2)

As a runtime integrator, I can receive structured command outcomes and clearer
parameter/session information so downstream layers do not have to infer intent
from free-form strings.

**Why this priority**: Structured outcomes make command handling safer,
testable, and easier to extend without brittle parsing assumptions.

**Independent Test**: Execute representative commands that include valid
parameters, missing parameters, and invalid requests, then confirm the
assistant returns a consistent structured outcome for each case.

**Acceptance Scenarios**:

1. **Given** a command that requires parameters, **When** the assistant
   resolves it, **Then** the resulting outcome includes the command decision,
   parameter values, and user-facing spoken text in a consistent shape.
2. **Given** a command with missing or unclear parameters, **When** the
   assistant processes it, **Then** it asks for clarification once and returns
   a structured failure outcome if the request is still unclear.
3. **Given** an ongoing session with relevant command context, **When** the
   next command depends on that context, **Then** the assistant uses the
   current session state consistently and predictably for one immediate
   follow-up command only.

---

### User Story 3 - Separate Safe System Commands (Priority: P3)

As a reliability owner, I can trust that system-level commands are handled
separately from capability requests so risky actions are better protected and
easier to audit.

**Why this priority**: High-consequence commands need stricter handling than
general capability requests, especially in a voice-first assistive product.

**Independent Test**: Validate protected system commands, general capability
commands, and ambiguous phrases, then confirm system actions only occur through
their intended path and never from weak matches.

**Acceptance Scenarios**:

1. **Given** a protected system command, **When** the assistant processes it,
   **Then** it applies stricter validation and only executes when the intent is
   explicit enough.
2. **Given** a general capability command, **When** the assistant processes it,
   **Then** it is routed through the capability path rather than the system
   command path.
3. **Given** an ambiguous phrase near a risky system command, **When** the
   assistant processes it, **Then** it rejects or clarifies the request instead
   of executing the risky action.

### Edge Cases

- A spoken phrase partially matches more than one supported command.
- The utterance mixes Arabic and English terms in the same request.
- Required parameters are missing, contradictory, or extracted with low
  confidence.
- A clarification attempt still leaves required parameters unresolved and the
  assistant must fail safely without guessing.
- The user repeats a command while the assistant is already in a related active
  state.
- Background speech or transcription noise creates a near-match to a protected
  system command.
- A network-dependent speech provider becomes slow or unavailable during command
  handling and the assistant must preserve safe command outcomes through the
  existing provider fallback or degraded-mode path.
- The same command is issued in GUI and headless mode and must behave the same
  way.
- A previously valid session context becomes stale after one follow-up command
  and must not influence later requests.

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: More trustworthy command handling reduces confusion
  and makes the assistant safer for blind or low-vision users who depend on
  spoken feedback.
- **Audio UX**: Spoken confirmations should stay short, specific, and clearly
  distinguish success, clarification, and rejection outcomes.
- **Non-Visual Operation**: Command understanding and response behavior must
  remain fully usable without any screen-based disambiguation.
- **Weak-Network Behavior**: If a network-backed speech provider slows down or
  fails during recognition or spoken response, the assistant must preserve safe
  command behavior, reuse the existing fallback or degraded-mode path, and give
  clear spoken guidance when a command cannot continue normally.
- **Non-Verbal Feedback**: This phase does not introduce any new non-verbal
  feedback dependency; existing runtime or GUI indicators may mirror command
  state, but all primary command flows must remain fully operable by audio
  alone.
- **Failure Handling**: Ambiguous, noisy, or invalid commands must fail safely
  with clear spoken guidance rather than silently doing the wrong thing.
- **Risk Controls**: High-consequence system commands must require explicit
  spoken confirmation before execution, while lower-risk system commands must
  still require stronger intent validation than ordinary capability commands
  and must not trigger from weak matches.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST recognize the supported high-priority command set in
  both Arabic and English using consistent decision rules.
- **FR-002**: System MUST reduce false positives for near-match, noisy, or
  weak-confidence phrases before executing any command.
- **FR-003**: System MUST return a safe clarification or rejection outcome when
  a spoken request is ambiguous or does not meet the validation threshold.
- **FR-004**: System MUST represent command decisions using a unified command
  result model rather than raw response strings alone.
- **FR-005**: Unified command results MUST include `spoken_text`, `status`,
  `payload`, and `error_code` when applicable.
- **FR-006**: System MUST resolve command parameters in a structured form that
  downstream layers can consume without reparsing spoken output.
- **FR-007**: System MUST ask for clarification once when required parameters
  are missing or unclear, then fail safely if the request remains unresolved.
- **FR-008**: System MUST use session-aware command context when it is needed to
  interpret a follow-up request.
- **FR-009**: System MUST separate system commands from capability commands
  before execution routing occurs.
- **FR-010**: System MUST apply stronger safeguards to protected system
  commands than to ordinary capability commands.
- **FR-011**: System MUST preserve equivalent command outcomes across GUI and
  console or headless execution paths.
- **FR-012**: System MUST emit observable outcomes for matched, rejected,
  ambiguous, and failed command-processing cases.
- **FR-013**: System MUST include regression coverage for protected system
  commands, everyday assistant commands, and highest-value existing capability
  commands in both Arabic and English, including their boundary cases.
- **FR-014**: System MUST require an explicit confirmation step before
  executing high-consequence system commands.
- **FR-015**: System MUST use stricter intent validation for lower-risk system
  commands without forcing confirmation for every system command.
- **FR-016**: System MUST limit this phase to hardening and validating the
  currently supported command set rather than adding new commands.
- **FR-017**: System MUST retain session-aware command context for at most one
  immediate follow-up command before clearing it.

### Operational & Quality Requirements

- **OQ-001**: The specification MUST identify the affected command-understanding
  layers, including parsing, dispatching, resolving, and runtime-facing result
  delivery.
- **OQ-002**: Command-hardening behavior MUST define thresholding, grouping,
  and intent-specific validation expectations without bypassing existing
  runtime-service boundaries.
- **OQ-003**: Runtime-affecting command changes MUST define repeatable
  regression and smoke validation for GUI and headless paths.
- **OQ-004**: Structured command outcomes MUST describe how success,
  clarification, rejection, and failure states are represented for downstream
  consumers.

### Key Entities *(include if feature involves data)*

- **CommandIntent**: Represents the normalized command the assistant believes
  the user requested, including intent identity, confidence, and category.
- **CommandResolution**: Represents the resolved command decision, extracted
  parameters, validation outcome, and routing destination.
- **CommandExecutionResult**: Represents the structured result returned to
  runtime consumers, including spoken text, status, payload, and error details.
- **SessionCommandContext**: Represents the active session state that may
  influence how a follow-up command is interpreted or validated.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 90% of curated Arabic and English regression cases
  covering protected system commands, everyday assistant commands, and
  highest-value existing capability commands resolve to the intended user
  outcome.
- **SC-002**: Protected system commands show 0 unintended activations across
  the curated near-match and noisy-input regression scenarios.
- **SC-003**: 100% of ambiguous or invalid regression scenarios return a safe
  structured outcome with user-facing guidance instead of a silent failure or
  wrong action.
- **SC-004**: GUI and console or headless validation runs produce equivalent
  outcomes for all high-priority regression scenarios.

## Assumptions

- The current supported commands remain the baseline scope for regression
  protection during this phase.
- Adding new commands is out of scope for this phase; the focus is making the
  existing command set trustworthy first.
- Trustworthiness is prioritized over aggressively accepting fuzzy phrases.
- Runtime extraction and speech-provider abstraction from earlier phases remain
  available and stable enough to support this work.
- The most important command set includes everyday assistant actions, protected
  system actions, and the highest-value capability triggers already present in
  the product.
