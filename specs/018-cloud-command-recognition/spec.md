# Feature Specification: Cloud-Primary Command Recognition and Safety-Aware Fallback

**Feature Branch**: `[019-cloud-command-recognition]`  
**Created**: 2026-04-24  
**Status**: Draft  
**Input**: User description: "Read Phase 18 from docs\implementationPlan.md to do spec number 18 with best practis"

## Clarifications

### Session 2026-04-24

- Q: What should the default rollout posture be for cloud-primary command recognition? -> A: Opt-in only through existing rollout/config controls; disabled state preserves the previous command-recognition path.
- Q: What should happen when cloud fails and strict fallback cannot match approved grammar? -> A: Return no usable command transcript and let existing retry, confirmation, or safe-refusal recovery handle the turn without broad dictation.
- Q: Which confidence policy should cloud candidates use? -> A: Reuse the existing command confidence thresholds and protected-command policy; provider confidence is metadata, not direct execution authority.
- Q: How broad may command phrase hints become? -> A: Limit hints to deterministic approved catalogs and curated assistive variants with a documented priority order and maximum size; raw user utterances remain excluded by default.
- Q: How should wake-plus-command or protected phrases be treated in command mode? -> A: Wake wording must not bypass command validation; only the command portion can proceed, and protected commands always require explicit confirmation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand Commands With Cloud-Primary Recognition (Priority: P1)

As a blind or low-vision user, I want spoken commands to be recognized with the strongest available command-focused recognizer, so common Arabic, English, and bilingual commands are understood more reliably without changing how I talk to the assistant.

**Why this priority**: Command recognition is the primary way a headless assistant becomes useful; better command understanding directly reduces missed actions and repeated prompts.

**Independent Test**: Run command-mode recognition with cloud recognition available and representative command utterances, then verify the resulting command recognition outcome includes a usable transcript, alternatives, confidence metadata, selected and detected language context, and a cloud-primary source while preserving the existing command journey.

**Acceptance Scenarios**:

1. **Given** cloud command recognition is enabled and available, **When** the user speaks a supported short command, **Then** the assistant reports a cloud-primary command candidate with transcript, alternatives, confidence when available, and language metadata.
2. **Given** cloud recognition returns multiple alternatives, **When** command confidence and parser policies evaluate the turn, **Then** alternatives remain available for reranking and recovery decisions.
3. **Given** cloud recognition detects a language different from the selected profile language, **When** the command result is evaluated, **Then** detected language is used as metadata and does not automatically change the user profile language.

---

### User Story 2 - Recover Safely Through Strict Command Fallback (Priority: P2)

As a user depending on the assistant in noisy or unreliable network conditions, I want cloud command failures to fall back only to safe command grammars, so the assistant does not invent unsupported command text or crash when cloud recognition is weak.

**Why this priority**: Cloud-primary recognition improves accuracy only if unavailable, low-confidence, timeout, empty-result, and language-conflict cases degrade safely.

**Independent Test**: Simulate cloud empty result, timeout, low confidence, language mismatch, and parser rejection; verify strict command fallback runs only when allowed, returns grammar-constrained candidates, and otherwise lets existing retry or recovery behavior handle the turn.

**Acceptance Scenarios**:

1. **Given** cloud recognition times out, **When** strict fallback is enabled, **Then** command fallback uses only approved command grammar phrases and remains within the command listening window.
2. **Given** cloud recognition returns no usable transcript, **When** strict fallback is disabled, **Then** the assistant returns no usable command transcript and continues through existing recovery.
3. **Given** fallback hears unrelated speech, **When** the phrase is not in the approved command inventory, **Then** no command candidate is produced.
4. **Given** fallback produces a grammar match, **When** the result reaches command policy, **Then** it is marked with strict fallback source metadata and evaluated by the same parser and confidence rules as other command candidates.
5. **Given** cloud recognition fails and strict fallback finds no approved grammar match, **When** the command turn is resolved, **Then** the assistant exposes no usable command transcript and recovers through retry, confirmation, or safe refusal without broad dictation.

---

### User Story 3 - Use Command Hints That Reflect Assistive Use (Priority: P3)

As a release owner, I want command recognition hints to include supported assistive commands, Arabic variants, and common bilingual or phonetic forms, so the cloud recognizer is biased toward the actual command inventory without accepting open-ended dictation.

**Why this priority**: Better phrase hints improve command accuracy and reduce retries, but the hint inventory must stay bounded and auditable to avoid unsafe broad recognition.

**Independent Test**: Generate command phrase hints repeatedly and verify they include parser catalog commands, curated assistive phrases, Arabic command variants, mixed-speech forms, and stable ordering without raw user utterances.

**Acceptance Scenarios**:

1. **Given** command hints are generated, **When** the same approved command catalogs are used, **Then** the hint set is deterministic and deduplicated.
2. **Given** high-value assistive commands such as obstacle detection, face recognition, text reading, emergency help, and system stop are supported, **When** command hints are generated, **Then** their approved English, Arabic, bilingual, and phonetic variants are present.
3. **Given** a phrase is outside the approved command catalog and curated command variants, **When** hints are generated, **Then** it is not added from raw user utterance history by default.
4. **Given** hint generation reaches the documented maximum size, **When** extra approved phrases remain, **Then** stable priority ordering determines what is included and excluded.

---

### User Story 4 - Preserve Safety for Protected Commands (Priority: P4)

As a maintainer, I want cloud-primary recognition to feed the existing command confidence and confirmation policies instead of directly executing recognized text, so protected and ambiguous commands remain safe.

**Why this priority**: Better recognition must not weaken safety. High-risk commands still need confirmation, and ambiguous medium-risk commands need retry or confirmation instead of convenience-based execution.

**Independent Test**: Exercise protected commands, medium-risk commands with conflicting alternatives, low-risk high-confidence commands, and cloud/fallback failures; verify execution, confirmation, refusal, and retry decisions match existing safety policy.

**Acceptance Scenarios**:

1. **Given** a protected command is recognized with high confidence, **When** the assistant evaluates it, **Then** explicit confirmation is still required before execution.
2. **Given** cloud alternatives conflict for a medium-risk command, **When** confidence is borderline, **Then** the assistant asks for confirmation or retries rather than executing immediately.
3. **Given** a low-risk command is recognized with high confidence and clean parser acceptance, **When** the assistant evaluates it, **Then** it can execute through the normal dispatcher and resolver flow.
4. **Given** a cloud or fallback candidate is rejected by post-processing or parser validation, **When** command policy evaluates the turn, **Then** the assistant recovers through retry, confirmation, or safe refusal rather than executing raw recognition output.
5. **Given** the user includes wake wording before a protected command while already in command mode, **When** recognition and command policy evaluate the phrase, **Then** wake wording grants no execution shortcut and the protected command still requires explicit confirmation.

### Edge Cases

- Cloud command recognition succeeds but confidence is below the command threshold.
- Cloud recognition times out, returns no transcript, or reports an unavailable state.
- Cloud detects a language that conflicts with the selected command context.
- Cloud returns alternatives where one looks command-like and another looks unrelated.
- Strict fallback hears arbitrary speech that is outside the command inventory.
- Strict fallback produces a phrase that does not parse into a supported command.
- A protected command such as system stop, emergency action, reset, or settings-sensitive change is recognized with high confidence.
- The user speaks wake plus command in one phrase while the assistant is already in command mode; wake wording must not increase confidence or bypass command validation.
- Command recognition runs headless and must expose enough spoken recovery without GUI inspection.
- Diagnostics must explain recognition source and fallback decision without storing raw utterance content by default.

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: Blind and low-vision users get more reliable command understanding for short assistive actions, especially in Arabic, English, mixed speech, and noisy wearable contexts.
- **Audio UX**: Recognition failures should lead to short, clear retry, confirmation, or safe-refusal prompts rather than silent failure or confusing execution.
- **Non-Visual Operation**: Recognition source, fallback decision, and command confidence outcomes must be observable through field-safe runtime events and spoken recovery behavior without requiring the GUI.
- **Failure Handling**: Cloud timeout, empty result, low confidence, unavailable cloud, language mismatch, fallback no-match, and parser rejection must resolve to strict fallback, retry, confirmation, or safe refusal within existing command-session bounds.
- **Risk Controls**: Protected commands must still require explicit confirmation; fallback must be command-grammar constrained; raw STT text must never bypass parser, post-processing, confidence, dispatcher, or resolver safety layers.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST make explicitly enabled command-mode recognition cloud-primary when the cloud recognizer is available.
- **FR-002**: Cloud-primary command recognition MUST use command-focused phrase hints sourced from approved command catalogs and curated assistive variants.
- **FR-003**: Command recognition results MUST preserve transcript text, confidence when available, alternatives, recognition source, selected language, detected language, and failure context needed by existing command policy.
- **FR-004**: The command recognition flow MUST preserve existing public command result behavior and recognition path compatibility for local, rescue, and fallback flows.
- **FR-005**: The system MUST run strict command fallback when cloud command recognition returns no transcript, times out, reports low confidence, conflicts with command language context, or is rejected by command validation, when fallback is enabled.
- **FR-006**: Strict command fallback MUST only return candidates that match the approved command inventory or active closed-vocabulary command context.
- **FR-007**: The system MUST NOT use broad local dictation or PocketSphinx as a default command accuracy path.
- **FR-008**: Fallback behavior MUST remain bounded by the active command listening window and must not create an unbounded retry loop.
- **FR-009**: Command phrase hints MUST include approved high-value assistive commands, Arabic variants, English variants, bilingual forms, and common phonetic or speech-recognition variants.
- **FR-010**: Command phrase hints MUST be deterministic, deduplicated, auditable, and free of raw user utterance-derived entries by default.
- **FR-011**: Cloud confidence MUST be available to the existing confidence policy when the provider supplies it.
- **FR-012**: Alternative transcripts MUST remain available for command reranking, parser validation, confirmation, and rescue decisions.
- **FR-013**: Recognition outcomes with language mismatch, no command-like structure, endpoint clipping hints, or out-of-vocabulary command shape MUST be penalized or routed to recovery instead of being trusted blindly.
- **FR-014**: Strict fallback candidates MUST be promoted only when they map to a known command or active closed-vocabulary option.
- **FR-015**: Protected commands MUST continue to require explicit confirmation according to existing safety policy, regardless of cloud confidence.
- **FR-016**: Medium-risk commands MUST ask for confirmation or retry when cloud confidence is borderline or alternatives conflict.
- **FR-017**: Low-risk commands MAY execute directly only when confidence is high and parser acceptance is clean.
- **FR-018**: The system MUST emit field-safe diagnostics for command recognition source, fallback decision, confidence band, language mismatch, and failure reason without storing raw utterance content by default.
- **FR-019**: Cloud failures MUST produce strict fallback or existing recovery behavior rather than runtime crashes.
- **FR-020**: The feature MUST NOT execute commands directly from STT output without passing through existing post-processing, parser, confidence, dispatcher, and resolver policy.
- **FR-021**: Cloud-primary command recognition MUST remain opt-in through existing rollout or configuration controls; when disabled, the prior command-recognition path MUST remain behaviorally unchanged.
- **FR-022**: When cloud recognition fails and strict fallback cannot produce an approved grammar match, the system MUST return no usable command transcript and defer to existing retry, confirmation, or safe-refusal recovery without using broad dictation.
- **FR-023**: Cloud provider confidence MUST be interpreted through the existing command confidence thresholds, protected-command rules, and parser validation rather than creating a direct execution shortcut.
- **FR-024**: Command phrase hints MUST enforce a documented maximum size and stable priority order so the hint set remains bounded, deterministic, and auditable.
- **FR-025**: Wake wording present during command-mode recognition MUST NOT raise command confidence, bypass parser validation, or bypass protected-command confirmation.

### Operational & Quality Requirements

- **OQ-001**: The affected runtime layer is the command recognition boundary and command policy flow; the feature MUST NOT redesign the parser, dispatcher, resolver, or runtime command loop.
- **OQ-002**: External recognition behavior MUST remain behind the existing speech provider/listener boundary and return structured recognition metadata.
- **OQ-003**: Runtime-affecting behavior MUST define field-safe logging, smoke validation, and command-recognition latency or reliability expectations.
- **OQ-004**: Validation MUST cover cloud command success, cloud low confidence, cloud timeout, cloud unavailable or empty result, strict fallback success, strict fallback failure, language mismatch, conflicting alternatives, and protected-command confirmation.
- **OQ-005**: Validation MUST prove default command recognition excludes PocketSphinx from the production accuracy path.
- **OQ-006**: Validation MUST prove cloud and fallback command outcomes preserve compatibility with existing command result consumers.
- **OQ-007**: Validation MUST cover disabled rollout behavior, bounded hint generation, no-match strict fallback recovery, and wake-plus-command safety handling.

### Key Entities *(include if feature involves data)*

- **Command Recognition Candidate**: A recognized command transcript with source, confidence, alternatives, language metadata, and validation status.
- **Command Phrase Hint Set**: A deterministic command-focused hint inventory built from approved command catalogs and curated assistive variants, with documented maximum size and priority ordering.
- **Strict Command Fallback Outcome**: A grammar-constrained fallback result that either maps to an approved command candidate or returns no usable transcript.
- **Command Fallback Decision**: A structured decision explaining whether strict fallback, retry, confirmation, safe refusal, no usable transcript, or normal execution should follow a recognition attempt.
- **Command Safety Evaluation**: The existing policy outcome that determines execute, confirm, retry, fallback, defer, or refuse for a recognized command.
- **Recognition Source Metadata**: Field-safe metadata identifying whether the command came from cloud primary, strict Vosk fallback, rescue strict fallback, cloud unavailable recovery, or existing compatible paths.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With cloud command recognition explicitly enabled and available, representative command-mode validation produces cloud-primary command candidates without changing the user-facing command flow.
- **SC-002**: Supported Arabic and bilingual command fixtures show a strictly higher command-resolution success count than the recorded local-first baseline for the same fixture set.
- **SC-003**: Common command fixtures show a strictly lower fallback-to-retry count than the recorded local-first baseline for the same fixture set.
- **SC-004**: Command-mode recognition contributes zero PocketSphinx candidates in the default production path.
- **SC-005**: Cloud timeout, empty result, low-confidence, and unavailable scenarios recover through strict command fallback or existing recovery in 100% of validation cases.
- **SC-006**: Strict command fallback returns no usable transcript for unsupported free-form speech in 100% of covered no-match cases.
- **SC-007**: No protected command executes without explicit affirmative confirmation in validation.
- **SC-008**: Cloud and fallback alternatives remain available to downstream command policy in 100% of covered multi-alternative cases.
- **SC-009**: Field-safe diagnostics include recognition source, confidence band, fallback decision, and failure reason while showing no raw utterance retention by default.
- **SC-010**: With cloud-primary command recognition disabled, existing command-recognition behavior remains unchanged across the covered regression fixtures.
- **SC-011**: Strict fallback no-match cases produce no usable command transcript and route to existing recovery in 100% of covered validation cases.
- **SC-012**: Wake-plus-command protected-command fixtures require explicit confirmation in 100% of covered validation cases.

## Assumptions

- Phase 17 has already provided the optional cloud STT foundation, strict fallback contracts, and conservative rollout controls.
- This phase applies to command-mode recognition only; wake recognition is handled by a later phase.
- Existing post-processing, parser, confidence policy, dispatcher, resolver, and protected-command confirmation remain the authority for command execution.
- Cloud-primary behavior remains explicitly configurable, opt-in by default, and rollback-friendly.
- Phrase hints are generated from approved static catalogs and curated variants, not from raw user utterance history by default.
- Validation can use fake cloud responses and deterministic command fixtures without requiring live cloud credentials.
