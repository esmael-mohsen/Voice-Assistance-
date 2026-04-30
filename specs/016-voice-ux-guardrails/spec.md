# Feature Specification: Continuous Turn-Taking, Closed-Vocabulary Guardrails, and Pilot-Grade Voice UX

**Feature Branch**: `[017-voice-ux-guardrails]`  
**Created**: 2026-04-23  
**Status**: Draft  
**Input**: User description: "Read Phase 16 from docs\implementationPlan.md to do spec number 16 with best practis"

## Clarifications

### Session 2026-04-23

- Q: Which guided prompts should allow early barge-in by default? -> A: Allow early barge-in for onboarding choices, low-risk settings, informational prompts, and retry/help prompts; block protected confirmations, shutdown, and destructive flows until spoken once.
- Q: Can unrelated speech break out of a closed-vocabulary turn? -> A: Only approved global safety commands may preempt a closed-vocabulary turn; all other speech is rejected within the current guided context.
- Q: What fallback should guided setup use after retry limits are exhausted? -> A: Keep the last confirmed or safe default value for required settings, skip unconfirmed personalization such as name, and continue unless no safe fallback exists, in which case exit gracefully.
- Q: When may a captured spoken name be accepted as final? -> A: Only after an explicit user confirmation; uncertain or unconfirmed name candidates are discarded rather than persisted.
- Q: What minimum evidence should every pilot UX validation run record? -> A: Record journey completion, retries, barge-in acceptance, prompt-echo suppressions, out-of-domain rejections, and final fallback or exit reason without raw user utterances by default.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Answer Naturally During Guided Prompts (Priority: P1)

As a blind or low-vision user, I want to answer onboarding and settings prompts
as soon as I know the answer, even if the assistant is still finishing the
prompt, so the conversation feels natural instead of rigid.

**Why this priority**: If the assistant forces users to wait for narrow
response windows, basic setup becomes frustrating and error-prone, especially
in headless wearable use.

**Independent Test**: Run guided prompts for onboarding choices, low-risk
settings, informational prompts, and retry/help turns where users answer before
prompt completion, during allowed playback, and immediately after prompt
completion, then verify accepted turns are captured without forcing repeated
prompts.

**Acceptance Scenarios**:

1. **Given** the assistant is speaking a guided prompt that allows early
   answers, **When** the user gives a valid response before the prompt ends,
   **Then** the assistant captures the response, stops or shortens playback as
   needed, and advances without asking the user to repeat.
2. **Given** the assistant is in a protected confirmation, shutdown, or
   destructive flow, **When** the user interrupts before the safe point,
   **Then** the assistant preserves the protection boundary and only accepts
   input after the full initial prompt has been spoken once.
3. **Given** the assistant finishes an eligible prompt and the user responds
   immediately, **When** the turn opens, **Then** the response is handled as
   the intended answer rather than as noise, echo, or an out-of-turn utterance.

---

### User Story 2 - Keep Closed-Choice Dialogs On Track (Priority: P2)

As a user speaking Arabic, English, or mixed variants, I want closed-choice
questions such as language, voice, speed, yes/no, and retry prompts to accept
only the supported answers and reject unrelated speech clearly, so the
assistant does not guess incorrectly.

**Why this priority**: Closed-choice turns are where over-interpretation causes
the most confusion and safety risk, especially during onboarding and recovery
flows.

**Independent Test**: Exercise each closed-vocabulary context with valid
aliases, mixed-language variants, near misses, unrelated answers, and
non-safety commands, then verify only approved answers resolve the dialog, only
global safety commands may preempt, and all other answers trigger bounded
recovery.

**Acceptance Scenarios**:

1. **Given** the assistant asks a closed-choice question, **When** the user
   gives a supported answer or alias in Arabic, English, or a common mixed
   variant, **Then** the assistant resolves the intended option without
   requiring open-ended interpretation.
2. **Given** the assistant is waiting for a closed-choice answer, **When** the
   user gives an out-of-domain phrase, **Then** the assistant rejects it
   explicitly, gives a short recovery prompt, and stays in the same safe dialog
   context.
3. **Given** a recent system prompt shares words with the allowed answer set,
   **When** overlapping prompt text is captured, **Then** the assistant ignores
   the prompt echo and waits for fresh user speech.
4. **Given** the assistant is waiting for a closed-choice answer, **When** the
   user says an unrelated command that is not part of the approved global
   safety vocabulary, **Then** the assistant keeps the current guided context
   active and does not branch into a new task.

---

### User Story 3 - Complete Setup and Recovery Without Fragile Loops (Priority: P3)

As a maintainer preparing pilot use, I want onboarding, name capture,
confirmation, and recovery journeys to stay short, recover predictably, and be
measurable end-to-end, so real users are less likely to get trapped in
confusing loops.

**Why this priority**: A pilot-grade assistive experience depends on full
spoken journeys succeeding reliably, not just isolated recognition turns.

**Independent Test**: Run end-to-end onboarding and settings journeys covering
early answers, prompt echo, repeated invalid answers, mixed Arabic/English
turns, and name confirmation recovery, then verify journeys complete or exit
gracefully within bounded retries.

**Acceptance Scenarios**:

1. **Given** the user provides a name during onboarding, **When** the captured
   utterance includes minor recognition artifacts or a clipped first attempt,
   **Then** the assistant asks a concise confirmation or retry prompt and only
   accepts the name as final after explicit confirmation.
2. **Given** repeated invalid or missing answers occur in a guided flow,
   **When** the retry limit is reached, **Then** the assistant uses the
   last confirmed or safe default value for required settings, skips
   unconfirmed personalization such as name, or exits gracefully if no safe
   fallback exists instead of looping indefinitely.
3. **Given** a pilot UX validation run is executed, **When** the representative
   spoken journeys complete, **Then** the results show completion, retry,
   rejection, and recovery outcomes clearly enough to tune future releases.

---

### Edge Cases

- The user answers at the exact moment a prompt is ending, and the system must
  treat the turn consistently instead of splitting the utterance across two
  interaction states.
- The assistant's own prompt contains words like "yes", "Arabic", or "repeat"
  and must not be misinterpreted as the user's answer.
- A user mixes Arabic and English in the same short response, and the
  assistant must accept intentional bilingual aliases without expanding into
  arbitrary free-text interpretation.
- A closed-choice answer sounds similar to an unsupported word, and the
  assistant must prefer safe rejection over guessing.
- The user says an unrelated command while the assistant is waiting for a
  closed-choice answer, and the assistant must keep the protected or guided
  dialog context unless the utterance matches an approved global safety
  command.
- Name capture returns a partial or noisy utterance, and the assistant must
  avoid storing a broken identity value by discarding unconfirmed name
  candidates instead of persisting them.
- The user remains silent after barging in or starts speaking but stops
  mid-answer, and the assistant must recover with short prompts rather than
  resetting the entire journey unnecessarily.
- A required onboarding answer remains unresolved after the final retry, and
  the assistant must continue with the last confirmed or safe default setting
  when one exists instead of trapping the user in setup.
- Headless operation must remain fully usable without screen cues for
  turn-taking, rejection, retry, or completion.
- Changes to barge-in or retry behavior must not weaken existing safeguards
  around stop, close, destructive, or other high-consequence actions.

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: Blind and low-vision users gain a more natural
  spoken experience that accepts timely answers, keeps guided dialogs on track,
  and reduces frustration during setup and recovery.
- **Audio UX**: Guided prompts must stay short, directive, and easy to answer
  quickly, while protected flows remain explicit when interruption is not yet
  safe.
- **Non-Visual Operation**: The full turn-taking, rejection, retry, and
  completion path must remain understandable without any screen-based feedback.
- **Failure Handling**: Prompt echo, unrelated answers, clipped input, silence,
  and repeated invalid turns must degrade into bounded recovery prompts or safe
  exit rather than long loops or silent failure.
- **Risk Controls**: Early-answer capture and dialog convenience must preserve
  existing protections for stop, close, destructive, and other
  high-consequence actions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a centralized turn-taking policy for
  guided speech interactions that distinguishes at least speaking-only,
  speaking-with-barge-in, active listening, closed-vocabulary listening,
  confirmation waiting, and recovery-after-no-input or clipped-input states.
- **FR-002**: The turn-taking policy MUST allow early answer capture for
  onboarding, settings, and other low-risk guided prompts where natural
  interruption is safe.
- **FR-002a**: Early barge-in MUST be enabled by default for onboarding
  choices, low-risk settings, informational prompts, and retry/help prompts,
  while protected confirmations, shutdown, and destructive flows remain blocked
  until their initial prompt has been spoken once.
- **FR-003**: Protected, destructive, or other high-consequence flows MUST
  preserve stricter interruption boundaries and MUST NOT accept early input
  until the safe point is reached.
- **FR-004**: When an early answer is accepted, the assistant MUST coordinate
  prompt playback and input handling so the user does not need to repeat the
  answer simply because the prompt was still finishing.
- **FR-005**: The system MUST maintain a shared closed-vocabulary registry for
  guided contexts including language choice, voice gender, speech speed,
  yes/no/cancel, wake confirmation, and retry/repeat/help prompts.
- **FR-006**: Each closed-vocabulary context MUST support approved Arabic,
  English, and common mixed-language aliases intentionally rather than treating
  the turn as unrestricted free dictation.
- **FR-007**: Guided responses MUST be validated against the active
  closed-vocabulary context before dialog resolution occurs.
- **FR-008**: Out-of-domain, unsupported, or ambiguous answers in a
  closed-vocabulary context MUST be rejected explicitly with a short recovery
  prompt instead of being over-interpreted as a valid choice.
- **FR-009**: The system MUST detect and ignore prompt echo or system
  self-capture during guided dialog turns.
- **FR-010**: Prompt echo suppression MUST NOT unfairly consume the user's
  retry budget when no fresh user answer was received.
- **FR-011**: Retry behavior for guided dialogs MUST be bounded and
  mode-specific: first retry short clarification, second retry narrower wording
  with explicit options, and final retry safe fallback or graceful exit.
- **FR-011a**: When a required onboarding or settings choice reaches its final
  retry without a valid answer, the assistant MUST keep the last confirmed or
  safe default value and continue when that path remains safe; if no safe value
  exists, it MUST exit the guided flow gracefully.
- **FR-012**: Guided prompts for onboarding and settings MUST be short,
  directive, and easy to answer quickly without requiring the user to remember
  long instructions.
- **FR-013**: Name capture MUST wait for a complete enough utterance to support
  a trustworthy confirmation step before accepting a final spoken name, and a
  newly captured name MUST NOT become final without explicit user confirmation.
- **FR-014**: Name confirmation MUST support robust affirmative, negative, and
  cancel behavior in Arabic and English and recover cleanly from uncertain
  answers.
- **FR-014a**: Uncertain, rejected, or unconfirmed name candidates MUST be
  discarded rather than persisted or reused as the accepted spoken name.
- **FR-015**: The assistant MUST preserve the active guided context when
  unrelated speech or unsupported commands occur during a closed-vocabulary
  turn, allowing preemption only for the approved global safety vocabulary or
  an existing higher-priority safety command.
- **FR-016**: The assistant MUST remain usable in headless operation, with
  spoken or otherwise non-visual cues sufficient for turn-taking, rejection,
  retry, and completion states.
- **FR-017**: The feature MUST provide end-to-end validation journeys covering
  early answers during playback, repeated invalid answers, mixed-language
  onboarding, prompt echo suppression, and name capture/confirmation recovery.
- **FR-018**: The feature MUST define a practical pilot UX acceptance checklist
  that reviewers can use to judge whether spoken journeys feel natural,
  bounded, and understandable.
- **FR-019**: The feature MUST document tuning guidance for allowed barge-in
  modes, closed-vocabulary sets, retry limits, and prompt style so future
  iteration can happen without redefining the user contract.
- **FR-020**: Changes introduced by this feature MUST preserve existing
  confirmation and safety protections for stop, close, destructive, and other
  high-consequence actions.

### Operational & Quality Requirements

- **OQ-001**: The specification MUST identify the affected runtime layers:
  turn-taking coordination, guided-dialog policy, speech capture and playback
  coordination, vocabulary validation, tuning surfaces, and pilot UX
  documentation or test coverage.
- **OQ-002**: Voice UX changes MUST define clear boundaries between
  turn-taking decisions, closed-vocabulary policy, prompt echo rejection, and
  downstream dialog resolution.
- **OQ-003**: Runtime-affecting behavior MUST define repeatable smoke or
  journey validation plus measurable expectations for early-answer handling,
  rejection accuracy, retry bounds, prompt echo suppression, and guided-flow
  completion.
- **OQ-004**: Guided-dialog outcomes MUST use a structured contract that
  distinguishes accepted answers, rejected answers, suppressed prompt echoes,
  retry steps, fallback or exit actions, preserved safety state, and journey
  evidence for completion status, retries used, accepted barge-ins, prompt-echo
  suppressions, out-of-domain rejections, and final fallback or exit reason
  without raw user utterances in default validation artifacts.

### Key Entities *(include if feature involves data)*

- **Turn-Taking Window**: Defines whether the assistant is speaking only,
  speaking with barge-in allowed, actively listening, waiting for confirmation,
  or recovering from missing or partial input for a specific dialog turn.
- **Closed Vocabulary Context**: Represents a guided answer space such as
  language, voice, speed, yes/no/cancel, wake confirmation, or retry/help,
  including approved aliases and rejection rules.
- **Prompt Echo Signal**: Represents evidence that captured speech likely came
  from the assistant's recent prompt rather than from fresh user intent.
- **Name Candidate**: Represents a captured spoken name awaiting acceptance,
  confirmation, retry, or rejection; it becomes usable only after explicit
  confirmation and is otherwise discarded.
- **Pilot Voice UX Evaluation Run**: Captures one repeatable spoken-journey
  assessment with completion status, retries used, accepted barge-ins,
  prompt-echo suppressions, out-of-domain rejections, and final fallback or
  exit reason for pilot-readiness review, without raw user utterances in
  default evidence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 90% of benchmarked onboarding and settings answers
  spoken during approved barge-in windows are accepted without requiring the
  user to wait for prompt completion or repeat the answer.
- **SC-002**: At least 95% of benchmarked closed-vocabulary turns for
  language, voice, speed, and yes/no/cancel resolve correctly within two turns,
  while 100% of out-of-domain answers are rejected into a bounded recovery path
  rather than misapplied as valid choices.
- **SC-003**: Prompt echo causes fewer than 1 false accepted answer per 100
  guided-dialog benchmark turns, and no validation scenario loses more than one
  retry to prompt echo without fresh user speech.
- **SC-004**: At least 90% of first-run onboarding benchmark journeys,
  including mixed Arabic/English and name-confirmation recovery scenarios,
  complete without manual restart, and 100% of non-completing journeys end in
  safe default continuation or graceful exit within three failed attempts.
- **SC-005**: In 100% of pilot UX validation runs, the recorded evidence
  includes journey completion status, retries used, accepted barge-ins,
  prompt-echo suppressions, out-of-domain rejections, and final fallback or
  exit reason without raw user utterances in default artifacts.

## Assumptions

- This phase applies to guided speech interactions such as onboarding,
  settings, confirmations, and short recovery flows rather than unrestricted
  open-domain conversation.
- Arabic and English remain the supported primary languages, with intentional
  mixed-language aliases accepted only in documented closed-vocabulary
  contexts.
- The assistant continues to prioritize headless, non-visual use for blind and
  low-vision users, so spoken brevity and clarity remain more important than
  verbose explanations.
- Existing safety, confirmation, and stop behavior remain in place and are
  tightened rather than replaced by this feature.
- Earlier phases already provide structured speech recognition results and
  regression harnesses that this phase can extend for end-to-end UX
  validation.
- Pilot-readiness review in this phase remains lightweight and local-first; it
  does not require a general-purpose conversational AI control layer or an
  external observability platform.
