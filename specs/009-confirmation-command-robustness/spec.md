# Feature Specification: Confirmation, Clarification, and Command Robustness

**Feature Branch**: `[009-confirmation-command-robustness]`  
**Created**: 2026-04-20  
**Status**: Draft  
**Input**: User description: "Read Phase 9 from docs\implementationPlan.md to do spec number 9 with best practis"

## Clarifications

### Session 2026-04-20

- Q: What safety precedence should apply when a confirmation response contains both affirmative and cancel or negative cues? -> A: Negative or cancel cues always win over affirmative cues.
- Q: How many clarification retries should the assistant allow before stopping safely? -> A: Allow two clarification retries after the initial clarification prompt, then stop safely.
- Q: How should clarification prompts present missing options for parameter-required intents? -> A: Speak the currently supported choices explicitly instead of using an open-ended generic retry.
- Q: What should happen to stale follow-up context when a confirmation or clarification flow becomes active? -> A: Pending confirmation or clarification takes priority and clears unrelated stale follow-up context.
- Q: What scope boundary should this phase use for dialog robustness work? -> A: Limit scope to protected-command confirmation, comparable onboarding confirmation reuse, and parameter-required clarification flows.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Safe Confirmation Matching (Priority: P1)

As a blind or low-vision user, I need protected commands to recognize common
affirmative and negative speech variants so confirmations stay safe and usable
even when speech recognition adds filler words or minor phrasing differences.

**Why this priority**: Protected commands must never execute accidentally, but
they also cannot depend on brittle exact-match phrasing that makes safe actions
unusable in real speech conditions.

**Independent Test**: Trigger a protected command, answer with common Arabic
and English confirmation variants, and verify the assistant executes only after
an explicit affirmative response and never on ambiguous or negative replies.

**Acceptance Scenarios**:

1. **Given** a protected command is waiting for confirmation, **When** the user
   responds with a clear affirmative phrase in the active language or a common
   STT variant, **Then** the assistant confirms the action and executes it once.
2. **Given** a protected command is waiting for confirmation, **When** the user
   responds with a clear negative or cancel phrase, **Then** the assistant does
   not execute the command and announces that the action was cancelled.
3. **Given** a protected command is waiting for confirmation, **When** the
   response is unrelated, unclear, or only partially matches a confirmation
   phrase, **Then** the assistant does not execute the command and continues
   with a bounded safe confirmation flow.
4. **Given** a protected command is waiting for confirmation, **When** the
   response contains both affirmative and negative or cancel cues, **Then** the
   assistant chooses the safe non-executing outcome.

---

### User Story 2 - Bounded Clarification Prompts (Priority: P2)

As a user, I need the assistant to ask for missing command options in a clear,
explicit way so I can finish settings-related requests without guessing what
the system expects.

**Why this priority**: Once confirmation is reliable, the next most important
dialog problem is unclear clarification behavior for commands that require a
specific option such as language or voice selection.

**Independent Test**: Issue a parameter-required intent without the required
option, respond with valid and invalid clarification answers, and verify the
assistant either resolves the request correctly or stops safely after the retry
limit.

**Acceptance Scenarios**:

1. **Given** the user requests a settings command without the required option,
   **When** the assistant requests clarification, **Then** it presents explicit
   supported choices such as the currently supported language or voice options
   rather than a vague retry prompt.
2. **Given** a clarification prompt is active, **When** the user provides a
   valid supported choice, **Then** the assistant completes the requested
   action using that choice.
3. **Given** a clarification prompt is active, **When** the user repeatedly
   provides invalid or unrelated answers, **Then** the assistant stops the flow
   safely after the bounded retry limit without changing settings.

---

### User Story 3 - Reproducible Dialog Robustness (Priority: P3)

As a developer or QA owner, I need regression coverage for confirmation,
clarification, and follow-up dialog behavior so STT-driven safety regressions
are caught before release.

**Why this priority**: Safe dialog behavior must remain stable over time, and
regression protection is the practical way to preserve that safety as command
logic evolves.

**Independent Test**: Run a regression suite covering Arabic and English
confirmation phrases, clarification retries, cancellations, and follow-up state
interactions, then verify outcomes remain deterministic.

**Acceptance Scenarios**:

1. **Given** a regression suite covers common affirmative, negative, and cancel
   STT variants, **When** validation runs, **Then** each variant produces a
   consistent dialog outcome.
2. **Given** confirmation, clarification, and follow-up state can overlap in
   real sessions, **When** the regression suite exercises those transitions,
   **Then** one dialog state does not incorrectly satisfy or corrupt another.
3. **Given** stale follow-up context exists from an earlier command, **When** a
   new confirmation or clarification flow begins, **Then** the stale follow-up
   context does not satisfy the new dialog flow.

---

### Edge Cases

- STT returns filler-heavy responses such as "yes please" or "aywa tamam"
  instead of a single exact keyword.
- The response contains conflicting intent, such as both affirmative and cancel
  cues, and the assistant must choose the safe non-executing outcome with
  negative or cancel precedence.
- The user changes language mid-dialog and the assistant must still interpret
  yes, no, and cancel safely.
- A clarification session is active while stale follow-up context still exists
  from a previous command, and the unrelated follow-up context must be cleared.
- Background speech or noise partially resembles an affirmative response during
  a protected confirmation.
- The user stops responding during clarification and the assistant must not
  remain trapped in an indefinite retry loop.

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: Improves trust in protected-command handling and
  reduces the chance that a blind or low-vision user must repeat awkward exact
  phrases to complete or cancel a high-consequence action.
- **Audio UX**: Confirmation and clarification prompts must be short, explicit,
  and easy to answer in Arabic and English, with clear feedback when an action
  is confirmed, cancelled, or stopped safely.
- **Non-Visual Operation**: The full flow must work through speech alone,
  without requiring the user to inspect a screen or remember hidden option
  names.
- **Failure Handling**: Ambiguous or conflicting dialog input must always
  resolve to a non-executing safe outcome, and repeated clarification failures
  must end with a clear safe stop.
- **Risk Controls**: Protected commands must require explicit affirmative
  confirmation, cancellation must remain easy to trigger, and clarification
  retries must be bounded so the assistant does not drift into unintended
  actions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST interpret confirmation responses using approved
  affirmative, negative, and cancel phrase families rather than relying on
  exact full-string matches.
- **FR-002**: System MUST support common Arabic and English confirmation
  variants for protected-command confirmation.
- **FR-003**: System MUST use one consistent yes/no/cancel interpretation model
  across protected-command confirmation and comparable onboarding or
  confirmation flows.
- **FR-004**: System MUST execute a protected command only after an explicit
  affirmative confirmation while the command is still pending.
- **FR-005**: System MUST treat ambiguous, conflicting, or unrelated
  confirmation responses as non-executing outcomes.
- **FR-006**: System MUST give negative or cancel cues precedence over
  affirmative cues when both appear in the same confirmation response.
- **FR-007**: System MUST allow a negative or cancel response to clear the
  pending protected action and provide spoken cancellation feedback.
- **FR-008**: System MUST present explicit currently supported choices when a
  parameter-required intent needs clarification.
- **FR-009**: System MUST limit clarification to one initial prompt plus no
  more than two clarification retries before stopping safely.
- **FR-010**: System MUST clear unrelated stale follow-up context whenever a
  confirmation or clarification flow becomes active.
- **FR-011**: System MUST keep confirmation, clarification, and follow-up state
  isolated so one pending dialog does not incorrectly fulfill another.
- **FR-012**: System MUST provide confirmation and clarification guidance in the
  active language and behave consistently in GUI, console, and headless-first
  runtime flows.
- **FR-013**: System MUST preserve structured command outcomes for confirmed,
  cancelled, clarification-required, and clarification-failed flows.
- **FR-014**: System MUST include regression coverage for common confirmation
  variants, clarification outcomes, and follow-up interactions.
- **FR-015**: System MUST keep this phase scoped to protected-command
  confirmation, comparable onboarding confirmation reuse, and
  parameter-required clarification flows rather than expanding general
  free-form conversation understanding.

### Operational & Quality Requirements

- **OQ-001**: The specification MUST identify the affected runtime layers as
  the shared command-resolution layer in `core/`, the runtime dialog flow, and
  regression validation in `tests/`.
- **OQ-002**: Dialog interpretation behavior MUST define a shared boundary for
  yes/no/cancel parsing so the assistant does not use divergent confirmation
  rules in different flows, including comparable onboarding confirmation.
- **OQ-003**: Runtime-affecting dialog behavior MUST define logging and
  regression validation for protected confirmations, cancellations,
  clarification retries, and safe-stop outcomes.
- **OQ-004**: Structured dialog outcomes MUST continue to expose
  `spoken_text`, `status`, `payload`, and `error_code` when applicable.

### Key Entities *(include if feature involves data)*

- **Confirmation Vocabulary**: The approved families of affirmative, negative,
  and cancel phrases that may satisfy or reject a protected confirmation.
- **Pending Confirmation State**: The active record of which protected action is
  waiting for explicit user approval and what payload would be executed if
  approved.
- **Clarification Session**: The active state for a parameter-required intent
  that still needs an explicit supported option before it can proceed.
- **Dialog Outcome Record**: The structured result of a confirmation or
  clarification step, such as confirmed, cancelled, clarification required, or
  clarification failed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of protected intents covered by the regression suite remain
  blocked until an explicit affirmative confirmation is recognized.
- **SC-002**: At least 95% of approved Arabic and English confirmation phrase
  variants in the regression suite resolve to the intended confirm, cancel, or
  safe-retry outcome.
- **SC-003**: 100% of ambiguous or cancellation confirmation cases in the
  regression suite leave the protected action unexecuted.
- **SC-004**: When a required option is missing, the assistant either resolves
  the request from an explicit supported answer or stops safely within the
  bounded clarification limit of one initial prompt plus no more than two
  clarification retries.
- **SC-005**: The same approved yes/no/cancel inputs produce consistent dialog
  outcomes across protected-command confirmation and other confirmation flows.

## Assumptions

- Protected commands already exist and will continue to be treated as
  higher-consequence actions that require explicit confirmation.
- Language and voice-selection commands remain representative examples of
  parameter-required intents that need clarification.
- The assistant will continue supporting Arabic and English spoken guidance for
  critical dialogs.
- A small bounded clarification limit is acceptable for accessibility and
  safety, provided the assistant ends with a clear safe-stop response.
- Follow-up session context remains valuable, but it should only be reused when
  it is explicitly relevant to the current dialog state.
- This phase intentionally does not broaden the assistant into general
  free-form conversation repair or open-ended dialog management.
