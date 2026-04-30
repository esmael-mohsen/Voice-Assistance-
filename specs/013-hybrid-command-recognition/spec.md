# Feature Specification: Hybrid Command Recognition and Post-Processing

**Feature Branch**: `[013-hybrid-command-recognition]`  
**Created**: 2026-04-21  
**Status**: Draft  
**Input**: User description: "Read Phase 13 from docs\implementationPlan.md to do spec number 13 with best practis"

## Clarifications

### Session 2026-04-21

- Q: How should the runtime handle recognition results that do not include a usable confidence score? -> A: Treat missing confidence as uncertain, allowing immediate execution only for unambiguous non-protected commands and requiring fallback or confirmation otherwise.
- Q: How many retry or clarification cycles are allowed for medium-confidence command handling? -> A: Allow one additional retry or clarification cycle before safe refusal or deferral.
- Q: What minimum telemetry fields should every command-recognition decision record? -> A: Record session identifier, recognition path, confidence band, fallback usage, decision outcome, protected-command flag, and latency impact, without raw utterances by default.
- Q: How should the spoken-response latency target be measured? -> A: Measure 30 local-first trials and 30 fallback-assisted trials per validation run, then compute the 95th percentile from recognition start to spoken-response start and store the result in the Phase 13 quickstart evidence.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recognize Common Commands Quickly (Priority: P1)

As a blind or low-vision user wearing the assistant, I want common spoken
commands to be recognized through a fast local-first path so that everyday
actions still work promptly even when connectivity is weak or unavailable.

**Why this priority**: Everyday command recognition is the core assistant
experience. If the first recognition path is slow or unavailable, the wearable
feels unreliable immediately.

**Independent Test**: Run representative Arabic and English command trials with
network available and unavailable, then verify that supported high-confidence
commands complete through the first recognition path without unnecessary extra
prompts.

**Acceptance Scenarios**:

1. **Given** a supported everyday command is spoken clearly, **When** the local
   recognition path produces a high-confidence result, **Then** the assistant
   executes the command without asking for confirmation or invoking a stronger
   fallback path.
2. **Given** connectivity is unavailable, **When** a supported command can be
   recognized confidently by the local path, **Then** the assistant completes
   the command safely and responds truthfully without claiming a network
   fallback was used.
3. **Given** a recognition result does not include a usable confidence score,
   **When** the assistant evaluates a non-protected command, **Then** it treats
   the result as uncertain and only executes immediately if post-processing
   leaves a single unambiguous supported interpretation.

---

### User Story 2 - Handle Uncertain Commands Safely (Priority: P2)

As a user speaking in noise, mixing languages, or giving a risky command, I
want the assistant to react to uncertainty with confirmation, retry, or safe
refusal so that it does not mis-execute commands when recognition is weak.

**Why this priority**: Confidence-aware handling is what turns better
recognition into safer recognition. Without it, fallback and normalization can
still produce harmful false positives.

**Independent Test**: Exercise medium-confidence, low-confidence, and ambiguous
command trials for both ordinary and protected intents, then verify that the
assistant escalates recognition, confirms, retries, or refuses according to the
confidence band instead of silently guessing.

**Acceptance Scenarios**:

1. **Given** the first recognition result is ambiguous or medium confidence,
   **When** the assistant evaluates it, **Then** it uses a stronger recognition
   step or a bounded confirmation flow before deciding whether to execute.
2. **Given** a protected command has low confidence or conflicting alternatives,
   **When** the user has not given an explicit affirmative confirmation,
   **Then** the assistant does not execute the command.
3. **Given** the stronger fallback path is unavailable, **When** the remaining
   recognition result is still too uncertain for safe execution, **Then** the
   assistant gives truthful guidance and keeps the system in a safe state.
4. **Given** a medium-confidence command remains uncertain after one additional
   retry or clarification cycle, **When** the user still has not produced a
   safe executable result, **Then** the assistant refuses or defers the command
   instead of continuing to loop.

---

### User Story 3 - Normalize Noisy Bilingual Speech Consistently (Priority: P3)

As a maintainer validating command quality, I want a dedicated post-processing
layer and measurable recognition telemetry so that common Arabic and English
mishearings are corrected consistently and regressions can be detected early.

**Why this priority**: Accuracy gains do not hold unless normalization behavior
and fallback decisions are reviewable and repeatable across noisy bilingual
inputs.

**Independent Test**: Run a regression set containing noisy transcripts,
Arabic-English switching, and common substitution patterns, then verify that the
assistant normalizes command phrasing consistently and records which decision
path was used.

**Acceptance Scenarios**:

1. **Given** a transcript contains a known Arabic or English substitution,
   **When** command post-processing runs, **Then** the transcript is normalized
   into the canonical command phrasing before intent parsing.
2. **Given** a command required fallback recognition or confidence-based
   confirmation, **When** the interaction completes, **Then** the recorded
   telemetry identifies the confidence band, decision path, and latency impact
   without depending on raw user utterances in the default artifact set.

### Edge Cases

- What happens when the first recognition path does not provide a usable
  confidence score?
- How does the assistant behave when alternative transcripts point to different
  intents with different safety consequences?
- What happens when Arabic and English command tokens appear in the same spoken
  request?
- How is a protected command handled when the transcript looks plausible but the
  confidence band remains below the execution threshold?
- What happens when the network fallback path is unavailable, slow, or returns a
  result that still conflicts with the local interpretation?
- How are no-confidence and medium-confidence results kept bounded so the user
  is not trapped in retries or unsafe guesses?
- What happens when the user is in headless mode and cannot rely on any visual
  cue for clarification?

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: Blind and low-vision users gain more reliable spoken
  command handling, especially for short wearable interactions where a single
  misheard command can block progress or create confusion.
- **Audio UX**: High-confidence commands should feel immediate, while
  medium-confidence commands should use short, explicit confirmation or retry
  prompts that do not overload the user with long explanations.
- **Non-Visual Operation**: All confidence-aware decisions, fallback guidance,
  and protected-command handling must remain fully understandable through speech
  alone in headless use.
- **Failure Handling**: When recognition remains uncertain, the assistant must
  respond truthfully, avoid pretending a command succeeded, and preserve a safe
  idle or recovery state.
- **Risk Controls**: Protected or high-consequence commands must require clear
  affirmative confirmation when confidence is below the safe execution threshold,
  and low-confidence recognition must never silently bypass existing safety
  dialogs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST produce a command-recognition result that includes
  the primary transcript, confidence score when available, alternative
  transcripts when available, and recognition source metadata.
- **FR-002**: The system MUST attempt a fast local-first recognition path before
  using any stronger fallback recognizer for spoken commands.
- **FR-003**: The system MUST escalate to a stronger fallback recognition step
  when the first result is below the command execution confidence threshold or
  when intent resolution remains ambiguous.
- **FR-004**: The system MUST preserve a safe offline command path so that
  supported commands can still be handled locally when fallback recognition is
  unavailable.
- **FR-005**: The system MUST include a dedicated command post-processing stage
  that normalizes transcripts before intent parsing.
- **FR-006**: The post-processing stage MUST correct common Arabic and English
  recognition substitutions and canonicalize command phrasing before parsing.
- **FR-007**: The runtime MUST apply confidence-aware decision bands so that
  high-confidence commands can execute immediately, medium-confidence commands
  trigger bounded confirmation or retry handling, and low-confidence results do
  not execute silently unsafe actions.
- **FR-007a**: Recognition results without a usable confidence score MUST be
  treated as uncertain and MAY execute immediately only when post-processing
  leaves a single supported non-protected interpretation; otherwise they MUST
  require fallback recognition, explicit confirmation, or safe refusal.
- **FR-007b**: Medium-confidence command handling MUST allow no more than one
  additional retry or clarification cycle before safe refusal or deferral.
- **FR-008**: Protected commands MUST require explicit affirmative confirmation
  whenever confidence is below the safe execution threshold, even if a fallback
  recognizer proposes a plausible transcript.
- **FR-009**: When recognition remains too uncertain after available fallback
  and confirmation steps, the system MUST refuse execution safely and provide
  truthful spoken guidance.
- **FR-010**: The system MUST support Arabic, English, and mixed bilingual
  command inputs through the same recognition and post-processing flow.
- **FR-010a**: Mixed bilingual inputs MUST remain supported from the initial
  recognition result through runtime decision handling and not rely only on
  parser-side normalization after a single-language recognition assumption.
- **FR-011**: The system MUST record recognition-path telemetry that captures
  confidence band, fallback usage, and latency impact for command interactions.
- **FR-011a**: Every command-recognition telemetry record MUST include session
  identifier, recognition path, decision outcome, protected-command flag, and
  latency impact, plus confidence band and fallback usage when applicable.
- **FR-012**: Default recognition telemetry MUST avoid storing raw user
  utterances unless a narrower, explicitly approved troubleshooting workflow
  requires them.

### Operational & Quality Requirements

- **OQ-001**: The specification MUST identify the affected recognition-result
  boundary, runtime decision boundary, parser pre-processing boundary, and
  settings boundary.
- **OQ-002**: The feature MUST define distinct service boundaries for the local
  recognition path, stronger fallback recognition path, and command
  post-processing layer.
- **OQ-003**: Runtime-affecting behavior MUST define smoke validation,
  regression coverage, telemetry expectations, and latency expectations for both
  local-only and fallback-assisted command handling.
- **OQ-004**: Planning and implementation MUST treat `core/stt.py`,
  `core/assistant_runtime.py`, `core/parser.py`, `core/dispatcher.py`,
  `settings/settings_manager.py`, and a dedicated command post-processing module
  as the primary repository touchpoints.
- **OQ-005**: Confidence-aware decisions MUST remain consistent across console,
  GUI, and headless wearable-style entry paths when the same recognition inputs
  and safety conditions are encountered.

### Key Entities *(include if feature involves data)*

- **Command Recognition Result**: The structured outcome of one recognition
  attempt, including the best transcript, available confidence information,
  alternatives, and recognition-source context.
- **Confidence Decision Band**: The runtime classification that determines
  whether a command can execute immediately, needs confirmation or retry, or
  must be refused safely.
- **Command Normalization Record**: The transformed command text after
  substitutions and canonical phrasing rules are applied before intent parsing.
- **Recognition Telemetry Sample**: The reviewable record of which recognition
  path was used, whether fallback was triggered, which confidence band applied,
  the resulting decision outcome, whether the command was protected, and how
  much latency the interaction added.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In representative bilingual command trials, at least 90% of
  supported high-confidence commands complete on the first attempt without an
  extra confirmation prompt.
- **SC-002**: In representative medium-confidence command trials, at least 95%
  of interactions end in correct confirmation, bounded retry, or safe refusal
  rather than incorrect command execution.
- **SC-003**: In protected-command validation trials, 100% of low-confidence or
  ambiguous requests require explicit affirmative confirmation before execution,
  with zero unsafe silent executions.
- **SC-004**: In representative offline trials where network fallback is
  unavailable, 100% of locally supported commands still produce a truthful and
  safe outcome instead of hanging or falsely reporting success.
- **SC-005**: In 95% of high-confidence local-first trials, the assistant
  begins its spoken response within 2 seconds, and in 95% of fallback-assisted
  trials it begins its spoken response within 4 seconds, measured per
  validation run across 30 local-first trials and 30 fallback-assisted trials
  using the 95th percentile from recognition start to spoken-response start.
- **SC-006**: In 100% of reviewed command-recognition telemetry samples, the
  recorded evidence shows confidence band, fallback usage, and latency impact
  without exposing raw utterances in the default artifact set.

## Assumptions

- The assistant already has a command parser, dispatcher, and protected-command
  handling flow that this phase will harden rather than replace.
- A local recognition path is available for at least a meaningful subset of the
  command vocabulary used in wearable scenarios.
- Stronger fallback recognition may be slower or may depend on connectivity, so
  it should be used selectively rather than as the default path for every
  command.
- Existing confirmation and clarification behavior can be reused as long as it
  becomes confidence-aware and remains bounded.
- This phase improves command recognition quality and safety; it does not expand
  the command catalog beyond what the current parser and resolver already
  support.
