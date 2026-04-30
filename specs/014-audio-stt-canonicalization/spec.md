# Feature Specification: Audio Front-End, Hybrid STT, and Command Canonicalization

**Feature Branch**: `[014-audio-stt-canonicalization]`  
**Created**: 2026-04-22  
**Status**: Draft  
**Input**: User description: "Read Phase 14 from docs\implementationPlan.md to do spec number 14 with best practis"

## Clarifications

### Session 2026-04-22

- Q: How should the runtime resolve disagreement between the local-first and rescue recognition results? -> A: Allow automatic execution only when both paths converge on the same canonical supported command; otherwise require confirmation for non-protected outcomes and safely refuse unresolved risky commands.
- Q: How should closed-vocabulary flows recover when recognition returns speech outside the valid answer set? -> A: Give one short constrained retry that names the valid options, then return to the prior safe step instead of switching to unrestricted recognition.
- Q: What behavior must simplified mode preserve when the hybrid rescue path is disabled or unavailable? -> A: Keep capture profiles, audio pre-processing, canonicalization, and mode-specific dictionary bias active; only the rescue pass may be skipped.
- Q: What should happen if optional speech enhancements exceed the Raspberry Pi 4 qualification budget? -> A: Demote the offending enhancement from the default deployment profile and qualify the simpler supported profile instead of shipping a degraded default.
- Q: What privacy rule should govern runtime telemetry and qualification evidence? -> A: Default telemetry and qualification artifacts store derived metrics and flags only; live user audio and raw transcripts stay out of default evidence, while audio fixtures use curated offline samples only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Capture Complete Spoken Requests (Priority: P1)

As a blind or low-vision user wearing the assistant, I want my full spoken
request to be captured cleanly even when I start softly, speak briefly, or end
with a quiet final word so that the assistant does not miss part of what I said.

**Why this priority**: If the capture step clips the start or end of an
utterance, every later recognition or parsing improvement is limited by missing
audio.

**Independent Test**: Run wearable-style command trials with soft starts, brief
pauses, and quiet endings, then verify that the assistant captures complete
utterances, records capture-quality metadata, and uses one bounded recovery
attempt when clipping is suspected.

**Acceptance Scenarios**:

1. **Given** a user speaks a supported command with a soft start or quiet final
   word, **When** command capture begins and ends, **Then** the assistant keeps
   enough pre-roll and post-roll padding to preserve the full utterance for
   recognition.
2. **Given** the assistant suspects start or end clipping, **When** the first
   capture completes, **Then** it performs one bounded re-listen with a shorter
   spoken prompt instead of immediately failing the interaction.
3. **Given** a command capture completes normally, **When** the transcript is
   returned, **Then** the assistant also records capture-quality metadata that
   can be used by later runtime decisions and regression checks.

---

### User Story 2 - Recognize Commands Reliably in Noisy Bilingual Use (Priority: P2)

As a user speaking Arabic, English, or a mixed command in everyday noise, I
want the assistant to use a local-first recognition flow with canonicalization
and vocabulary bias so that supported commands resolve correctly without
wandering into arbitrary free-text outputs.

**Why this priority**: Better capture only helps if recognition and transcript
normalization keep the result close to the supported command inventory.

**Independent Test**: Run benchmark trials that include noisy command audio,
Arabic-English mixing, and common STT substitutions, then verify that the
assistant prefers a fast local-first path, uses a bounded rescue path when
needed, and normalizes the result into supported command phrases before parsing.

**Acceptance Scenarios**:

1. **Given** the local-first recognizer returns a clear supported command,
   **When** the assistant evaluates the result, **Then** it continues without
   invoking a stronger rescue recognizer.
2. **Given** the first recognition pass is weak, clipped, or inconsistent,
   **When** a stronger rescue path is available, **Then** the assistant uses
   that bounded rescue step before deciding whether the command is safe to
   execute.
3. **Given** a transcript contains known Arabic, English, or bilingual
   substitution patterns, **When** canonicalization runs, **Then** the command
   text is normalized into parser-friendly phrasing from the supported command
   inventory.
4. **Given** the assistant is in a closed-choice flow such as onboarding or
   yes-no confirmation, **When** recognition runs, **Then** it biases decoding
   toward the valid answer set for that mode instead of broad arbitrary text.
5. **Given** a closed-choice interaction still returns speech outside the valid
   answer set after one constrained retry, **When** the assistant cannot map
   the response safely, **Then** it returns to the prior safe step instead of
   widening the interaction into unrestricted recognition.

---

### User Story 3 - Qualify Speech Quality on Raspberry Pi 4 (Priority: P3)

As a maintainer preparing the wearable runtime for broader use, I want measured
benchmarks and configurable speech policies so that I can prove the upgraded
pipeline improves recognition quality without breaking realistic Raspberry Pi 4
latency and resource expectations.

**Why this priority**: The assistant needs repeatable evidence that quality
improved and that lower-power deployments can still choose a simpler safe mode.

**Independent Test**: Execute benchmark and regression suites on representative
local samples, then verify that capture quality, recognition accuracy,
closed-vocabulary accuracy, and latency outcomes are recorded against the new
speech policies.

**Acceptance Scenarios**:

1. **Given** a deployment enables the full hybrid path, **When** command
   interactions run on Raspberry Pi 4-class hardware, **Then** benchmark
   evidence shows the recognition-quality gains remain within the documented
   latency and resource budget.
2. **Given** a lower-power or degraded deployment disables parts of the hybrid
   flow, **When** the assistant handles spoken commands, **Then** it still uses
   a predictable simplified recognition policy that preserves capture
   pre-processing, canonicalization, and mode-specific vocabulary bias instead
   of silently failing or claiming unsupported behavior.

### Edge Cases

- If optional audio enhancement or rescue logic improves accuracy but breaches
  the Raspberry Pi 4 qualification budget, that enhancement is disabled for the
  affected deployment profile and the simpler supported profile becomes the
  documented default.
- If start or end clipping is suspected on both the initial capture and the
  bounded re-listen, the assistant advances to the next safe recovery action
  instead of looping on repeated capture attempts.
- If the local-first and rescue recognition passes map to different canonical
  supported commands, the assistant treats the result as unresolved ambiguity
  and uses confirmation or safe refusal rather than auto-executing either one.
- Mixed Arabic-English command phrases remain eligible for canonicalization as
  long as enough tokens map to a supported alias or command phrase to avoid an
  unsafe guess.
- If a closed-vocabulary mode receives speech outside the valid answer set, the
  assistant gives one short constrained retry and then returns to the prior
  safe step instead of widening the interaction to unrestricted free text.
- If stronger rescue recognition is disabled, unavailable, or too slow for the
  current deployment mode, the assistant continues with the simplified mode and
  states truthfully that the stronger rescue path is not active.
- The feature must still operate safely in headless mode without relying on any
  visual disambiguation cues.
- Canonicalization changes must never bypass existing confirmation or safety
  policies for risky actions.
- Default telemetry and qualification evidence exclude live user audio and raw
  transcripts; only curated offline benchmark fixtures may include audio
  samples.

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: Blind and low-vision users benefit from fewer cut-off
  utterances, more reliable spoken command recognition, and clearer recovery
  behavior when the assistant is unsure.
- **Audio UX**: Recovery prompts must stay short, explicit, and mode-aware so
  the user is not forced through long repeated prompts for clipped or weak
  speech.
- **Non-Visual Operation**: Capture recovery, closed-choice guidance, and
  fallback behavior must remain fully understandable through speech alone
  without requiring a screen.
- **Failure Handling**: When capture quality or recognition quality stays too
  weak, the assistant must respond truthfully, avoid pretending to understand,
  and return to a safe standby or retry-ready state.
- **Risk Controls**: Canonicalization and dictionary bias must not silently
  turn ambiguous speech into destructive command execution; protected or risky
  actions must still respect existing confirmation and safety policies.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST apply a dedicated audio pre-processing stage
  before command transcription.
- **FR-002**: The audio pre-processing stage MUST normalize capture into a
  stable speech-ready format that reduces low-frequency rumble, DC offset, and
  uneven loudness before recognition.
- **FR-003**: The system MUST separate microphone capture policy from
  transcription policy so audio capture tuning can change without redefining the
  parser or command inventory.
- **FR-004**: The system MUST support distinct capture profiles for standby
  wake, onboarding, command capture, and confirmation or yes-no capture.
- **FR-005**: Command capture MUST include endpointing behavior that supports
  early speech-start detection, adaptive trailing silence, and anti-clipping
  padding before and after the utterance.
- **FR-006**: Each command-recognition attempt MUST return capture-quality
  metadata that includes speech start timing, speech end timing, utterance
  duration, and whether start or end clipping was suspected.
- **FR-007**: When clipping is suspected, the assistant MUST perform no more
  than one bounded re-listen with a shorter reprompt before moving to the next
  safe recovery decision.
- **FR-008**: The recognition contract MUST return a structured result that
  includes a primary transcript, alternative transcripts when available,
  confidence when available, detected language or language candidates,
  recognition-source metadata, and endpoint-quality hints.
- **FR-009**: The system MUST use a local-first recognition path for spoken
  commands before attempting any stronger rescue recognizer.
- **FR-010**: The system MUST support a bounded second-pass rescue recognition
  step when the first-pass result is weak, clipped, or inconsistent.
- **FR-010a**: When the local-first and rescue recognition paths resolve to
  different canonical supported commands, the assistant MUST treat the result
  as unresolved ambiguity and continue only through confirmation or safe
  refusal; automatic execution is allowed only when both paths converge on the
  same canonical supported command and existing safety rules permit execution.
- **FR-011**: The recognition pipeline MUST support a predictable simplified
  mode for deployments that disable or limit the hybrid path.
- **FR-011a**: Simplified mode MUST preserve capture profiles, audio
  pre-processing, canonicalization, and mode-specific dictionary bias while
  skipping only the unavailable or disabled rescue step and surfacing truthful
  degraded-mode status.
- **FR-012**: The system MUST apply a command canonicalization stage before
  intent parsing.
- **FR-013**: Canonicalization MUST normalize Arabic variants, English casing,
  punctuation, and spacing, and map known STT substitutions into canonical
  supported command phrases.
- **FR-014**: The system MUST support bilingual alias normalization so mixed
  Arabic-English command phrases can still resolve into the supported command
  space.
- **FR-015**: Closed or semi-closed speech flows MUST use dictionary bias or
  answer-set filtering aligned to the valid options for that mode.
- **FR-015a**: If a closed or semi-closed flow receives a result outside the
  valid answer set, the assistant MUST issue one short constrained retry that
  names the valid options and then return to the prior safe step rather than
  switching to unrestricted recognition for that interaction.
- **FR-016**: Command-mode recognition MUST bias toward the supported command
  inventory without making dictionary bias a mandatory global rule for all
  future speech interactions.
- **FR-017**: The system MUST handle known confusion pairs in closed-choice or
  safety-sensitive contexts so commonly misheard alternatives do not execute the
  wrong outcome silently.
- **FR-018**: The feature MUST provide benchmark fixtures and regression
  scenarios for noisy audio, clipped utterances, bilingual command journeys,
  alternative-transcript rescue, and dictionary-filtered closed-vocabulary
  flows.
- **FR-018a**: Default runtime telemetry and qualification artifacts MUST store
  derived metrics and decision flags only; live user audio and raw transcripts
  MUST be excluded from default evidence, while audio-bearing benchmark
  fixtures MUST use curated offline samples.
- **FR-019**: The feature MUST document the recommended free local-first speech
  stack and its expected tradeoffs for Raspberry Pi 4-class deployments.

### Operational & Quality Requirements

- **OQ-001**: The specification MUST identify the affected audio
  pre-processing, STT provider, assistant runtime, parser pre-processing, and
  settings boundaries.
- **OQ-002**: Speech integrations MUST define separate service boundaries for
  capture policy, audio pre-processing, local-first recognition, stronger
  rescue recognition, and transcript canonicalization.
- **OQ-003**: Runtime-affecting behavior MUST define smoke validation,
  benchmark fixtures, latency expectations, and recognition-quality regression
  checks for both open command mode and closed-vocabulary modes.
- **OQ-004**: Planning and implementation MUST treat `core/stt.py`,
  `core/speech/`, `core/assistant_runtime.py`, `core/parser.py`, a dedicated
  audio pre-processing module, a dedicated transcript canonicalization module,
  `settings/settings_manager.py`, and speech-quality tests under `tests/` as
  the primary repository touchpoints.
- **OQ-005**: Raspberry Pi 4 qualification evidence MUST record command latency,
  capture completeness, command-resolution accuracy, and closed-vocabulary
  answer accuracy for the configured recognition mode.
- **OQ-006**: Qualification evidence MUST identify which optional speech
  enhancements were enabled, and any enhancement that breaches the Raspberry Pi
  4 deployment budget MUST be demoted from default to optional-disabled for the
  affected profile.

### Key Entities *(include if feature involves data)*

- **Audio Capture Profile**: The policy set that defines how a listening mode
  captures and prepares speech before transcription.
- **Capture Quality Metadata**: The structured timing and clipping indicators
  returned for each utterance to describe how complete the captured speech was.
- **Hybrid Recognition Result**: The recognition outcome containing the best
  transcript, alternatives, confidence, language signals, source details, and
  endpoint-quality hints across the local-first and rescue paths.
- **Canonical Command Outcome**: The normalized command text produced after
  substitutions, alias mapping, bilingual canonicalization rules, and
  constrained-mode filtering are applied.
- **Speech Benchmark Fixture**: The reusable evaluation sample that represents
  noisy, clipped, bilingual, or closed-vocabulary speech scenarios for
  regression measurement.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In representative wearable command-capture trials, at least 90%
  of spoken commands are recorded without suspected start or end clipping after
  the configured capture policy is applied.
- **SC-002**: In the maintained noisy local benchmark set, supported
  command-resolution success improves by at least 20 percentage points over the
  pre-phase baseline.
- **SC-003**: In closed-vocabulary onboarding and confirmation trials, at least
  95% of responses resolve to the correct valid option without requiring a broad
  free-text retry.
- **SC-004**: In benchmark cases containing known Arabic, English, or bilingual
  substitution patterns, at least 90% of transcripts are normalized into the
  intended supported command phrase before parsing.
- **SC-005**: In Raspberry Pi 4 qualification runs, 95% of local-first command
  interactions begin spoken response within 2.5 seconds and 95% of rescue-path
  interactions begin spoken response within 5 seconds.
- **SC-006**: In 100% of qualification runs, benchmark evidence records capture
  completeness, command-resolution accuracy, closed-vocabulary accuracy, and
  recognition-path latency for the active deployment mode.
- **SC-007**: In 100% of qualification runs, the published evidence identifies
  the supported deployment profile and any optional enhancement that was
  disabled because it exceeded the Raspberry Pi 4 qualification budget.

## Assumptions

- The assistant already has provider-based speech and runtime boundaries that
  this phase will harden rather than replace.
- Protected-command confirmation and safe-refusal policies from earlier phases
  remain in force after canonicalization and recognition changes.
- The project can maintain a representative local benchmark set for noisy,
  clipped, bilingual, and closed-vocabulary speech validation.
- The default deployment target remains Raspberry Pi 4-class hardware using a
  free, local-first speech path as the preferred baseline.
- Future open-domain speech features may exist, so dictionary bias remains
  mode-specific instead of becoming a universal recognition rule.
