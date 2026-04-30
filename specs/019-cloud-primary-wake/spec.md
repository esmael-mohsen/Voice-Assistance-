# Feature Specification: Cloud-Primary Wake Recognition and Standby Fallback Reliability

**Feature Branch**: `[021-cloud-primary-wake]`  
**Created**: 2026-04-25  
**Status**: Draft  
**Input**: User description: "Read Phase 19 from docs\implementationPlan.md to do spec number 19 with best practis"

## Clarifications

### Session 2026-04-25

- Q: What is the default rollout posture for cloud-primary wake recognition? → A: Opt-in only via existing configuration/rollout controls; when disabled, non-cloud wake behavior remains unchanged.
- Q: When should strict local wake fallback run relative to cloud wake results? → A: Run strict local wake fallback whenever cloud wake does not yield a canonical wake (timeout, unavailable, empty/unusable transcript, or non-canonical).
- Q: How should “wake + command” utterances be handled while in standby? → A: Accept wake only if canonical; do not execute or queue the command text from the same utterance.
- Q: What is the maximum allowed duration for a standby wake attempt? → A: ≤ 7 seconds.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Wake The Assistant Reliably In Standby (Priority: P1)

As a blind or low-vision user, I want the assistant to reliably recognize my wake phrase while it is in standby, so I can start interacting without repeating myself or needing a screen.

**Why this priority**: If wake fails, the entire assistant experience becomes unusable—especially on wearable hardware.

**Independent Test**: Run a set of wake-phrase fixtures (English, Arabic, and mixed) while the assistant is in standby and verify that a canonical wake is accepted within the wake listening window (≤ 7 seconds), and that non-wake speech does not exit standby.

**Acceptance Scenarios**:

1. **Given** the assistant is in standby and speech-based wake is enabled, **When** the user speaks a supported wake phrase clearly, **Then** the assistant accepts the wake and transitions out of standby into the normal active interaction flow.
2. **Given** cloud-based speech recognition is configured and available, **When** the user speaks a supported wake phrase, **Then** the system attempts cloud-primary wake recognition first and still accepts the wake only if it matches the canonical wake rules.
3. **Given** cloud-primary wake recognition fails (timeout, unavailable, empty/unusable transcript, or non-canonical transcript), **When** the user speaks a supported wake phrase, **Then** the system attempts a strict local wake fallback and accepts the wake only if it matches the canonical wake rules.
4. **Given** both cloud-primary and strict local wake fallback fail to produce a canonical wake, **When** the wake attempt completes, **Then** the assistant returns to standby safely without hanging, crashing, or leaving the user in an unclear state.

---

### User Story 2 - Avoid False Wakes And Unsafe Activations (Priority: P2)

As a user in noisy or conversational environments, I want the assistant to avoid waking up from unrelated speech or similar-sounding words, so it does not start listening or acting unexpectedly.

**Why this priority**: False wakes can lead to accidental actions, privacy risk, and user distrust—especially for assistive devices.

**Independent Test**: Run negative fixtures (noise, unrelated speech, similar-sounding non-wake words, and “wake + command” phrases) and verify the system rejects them as wake while remaining stable.

**Acceptance Scenarios**:

1. **Given** the user speaks unrelated speech that does not include a canonical wake phrase, **When** the wake attempt completes, **Then** the system rejects the attempt and remains in standby.
2. **Given** the recognition transcript includes command-like content but no wake phrase, **When** wake evaluation runs, **Then** the system MUST NOT accept wake.
3. **Given** the recognition transcript contains a wake-like approximation that is not canonical, **When** wake evaluation runs, **Then** the system rejects it and records it as a non-canonical wake rejection.
4. **Given** the environment contains short noise bursts or partial words, **When** wake evaluation runs, **Then** the system rejects them and returns to standby without escalating to broad dictation.
5. **Given** the user speaks a canonical wake phrase followed by command text in a single utterance, **When** the assistant is in standby, **Then** the assistant MAY accept wake but MUST NOT execute or queue the command text from the same utterance.

---

### User Story 3 - Preserve Existing Wake Modes And Standby Stability (Priority: P3)

As a maintainer and release owner, I want the wake system to remain compatible with existing standby flow and wake modes, so the new recognition ordering does not break low-power keyword wake or hardware-trigger wake.

**Why this priority**: This feature must improve reliability without destabilizing the runtime or removing critical fallback wake paths.

**Independent Test**: Validate that hardware-trigger wake and low-power keyword wake still function as before, and that repeated wake misses do not destabilize standby.

**Acceptance Scenarios**:

1. **Given** hardware-trigger wake is available, **When** the hardware trigger occurs, **Then** the assistant wakes using the existing hardware-trigger path (independent of speech-based wake changes).
2. **Given** low-power keyword wake is enabled, **When** the keyword wake path triggers, **Then** the assistant wakes using the existing keyword path (independent of speech-based wake changes).
3. **Given** the assistant experiences repeated wake misses, **When** it remains in standby for extended periods, **Then** the standby loop stays stable and continues to accept new wake attempts.

---

### User Story 4 - Provide Field-Safe Wake Telemetry For Debugging (Priority: P4)

As a release owner, I want field-safe telemetry that distinguishes wake accepted, wake rejected, cloud failure, and fallback used cases, so I can evaluate reliability without storing raw utterances.

**Why this priority**: Wearable reliability improvements require measurement, but diagnostics must remain privacy-preserving by default.

**Independent Test**: Exercise wake success, wake rejection, cloud failure, and fallback success paths and verify structured, field-safe markers are emitted for each outcome.

**Acceptance Scenarios**:

1. **Given** a wake is accepted, **When** the wake attempt completes, **Then** the system emits a structured wake outcome with a source classification (cloud primary or strict local fallback) and a canonical acceptance marker.
2. **Given** a wake is rejected as non-canonical, **When** the wake attempt completes, **Then** the system emits a structured rejection outcome that distinguishes non-canonical rejection from provider failure.
3. **Given** cloud wake recognition fails and strict fallback succeeds, **When** the wake attempt completes, **Then** the system emits a structured outcome indicating cloud failure and fallback usage.
4. **Given** both cloud and fallback fail, **When** the wake attempt completes, **Then** the system emits a wake-miss outcome and returns to standby.

### Edge Cases

- Cloud recognition returns a high-confidence transcript that is unrelated speech.
- Cloud recognition returns a transcript that contains command content but omits the wake phrase.
- The user says wake + command in a single utterance; wake acceptance must not be granted unless the wake portion is canonical, and the command portion must not be executed from the same utterance.
- Arabic wake variants and bilingual wake phrases (English wake words, Arabic names, mixed speech).
- Similar-sounding non-wake words that partially resemble the wake phrase.
- Network loss, weak connectivity, or provider timeouts during wake.
- Local fallback returns a transcript that is not in the approved wake alias set.
- Headless operation where wake feedback and recovery must be understandable without a GUI.
- Repeated wake misses causing resource or state leaks (standby must remain stable).

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: Improves the user’s ability to start interaction hands-free and non-visually, reducing repeated attempts and frustration in real-world wearable use.
- **Audio UX**: Wake success should lead to a consistent, brief acknowledgement; wake failure should be silent or minimal and must not confuse the user by partially entering an active state.
- **Non-Visual Operation**: All wake outcomes (accepted/rejected/missed) must be handled in a way that does not require on-screen debugging to recover.
- **Failure Handling**: Cloud timeouts, unavailable network, empty transcripts, and non-canonical transcripts must return to standby safely and quickly, with strict local fallback used when allowed.
- **Risk Controls**: Canonical wake matching remains the final gate; unrelated transcripts and command-only transcripts MUST NOT be treated as wake; strict local fallback must remain constrained to approved wake aliases and variants.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST make speech-based wake recognition cloud-primary when a cloud wake recognizer is configured and available.
- **FR-002**: The system MUST attempt a strict local wake fallback when cloud wake recognition does not yield a canonical wake (timeout, unavailable, empty/unusable transcript, or non-canonical transcript) and local fallback is enabled.
- **FR-003**: Wake acceptance MUST be determined by canonical wake matching rules; raw speech-recognition transcripts alone MUST NOT directly accept wake.
- **FR-004**: If a wake recognition path produces a transcript that is not canonical, the system MUST mark it as non-canonical and MUST NOT accept wake from it.
- **FR-005**: If both cloud-primary and strict local fallback fail to produce a canonical wake, the system MUST return to standby reliably without stalling or exiting unexpectedly.
- **FR-006**: The strict local wake fallback MUST be limited to an approved set of wake aliases and curated safe variants.
- **FR-007**: The system MUST reject strict-fallback transcripts that are not in the approved wake alias set (including unrelated speech and non-wake words).
- **FR-008**: Wake phrase hints (when used) MUST be built from the canonical wake aliases and curated variants, including supported English, Arabic, and bilingual forms.
- **FR-009**: Wake hint inventories MUST remain bounded and deterministic so they reduce false rejects without increasing false accepts.
- **FR-010**: The system MUST reject wake acceptance when the transcript contains command content but does not contain a canonical wake phrase.
- **FR-011**: The system MUST preserve existing hardware-trigger wake and low-power keyword wake paths; this feature MUST NOT remove or degrade them.
- **FR-012**: The speech-based wake flow MUST remain compatible with the existing standby wake attempt loop and must not change standby state semantics.
- **FR-013**: When network conditions prevent cloud wake recognition, the system MUST degrade gracefully and still support strict local wake fallback where permitted.
- **FR-014**: The wake flow MUST NOT depend on always-on cloud streaming; wake recognition MUST use bounded attempts consistent with standby behavior.
- **FR-015**: The system MUST emit a wake-miss outcome when both recognition paths fail, and it MUST be distinguishable from non-canonical rejection.
- **FR-016**: The system MUST emit wake source classifications for accepted and rejected attempts that distinguish at least: cloud primary, strict local fallback, and rejected non-canonical.
- **FR-017**: The system MUST support bilingual wake variants (English wake words and Arabic variants) through canonical alias definitions and curated variants.
- **FR-018**: The system MUST include test coverage for noise, similar-sounding non-wake words, wake + command utterances, Arabic wake variants, and cloud-timeout-then-fallback-success cases.
- **FR-019**: Cloud-primary wake recognition MUST remain opt-in via existing configuration/rollout controls; when disabled, speech-based wake MUST remain behaviorally consistent with the prior non-cloud wake path.
- **FR-020**: When a wake attempt contains a canonical wake phrase plus additional command text, the system MUST treat the attempt as wake-only and MUST NOT execute or queue the command text from the same utterance.

### Operational & Quality Requirements

- **OQ-001**: The affected runtime layer is the wake subsystem in the core runtime and the speech provider boundary; the feature MUST preserve the existing wake mode selection and standby flow.
- **OQ-002**: Cloud and local wake recognition MUST remain behind the existing speech provider / recognizer boundary and return structured outcomes suitable for canonical wake evaluation.
- **OQ-003**: Wake attempts MUST remain bounded by the wake listening window (≤ 7 seconds); the system MUST not introduce an unbounded retry loop inside standby.
- **OQ-004**: Field-safe diagnostics MUST identify wake outcome and wake source classification without persisting raw utterance content by default.
- **OQ-005**: Validation MUST cover cloud available, cloud timeout/unavailable, strict fallback success, strict fallback no-match, non-canonical rejection, and repeated wake miss stability.

### Key Entities *(include if feature involves data)*

- **Wake Attempt Outcome**: A structured record of a single wake attempt (accepted/rejected/missed), including a source classification and a canonical-match indicator.
- **Wake Source Classification**: A field-safe label indicating whether the attempt was resolved via cloud primary, strict local fallback, or rejected as non-canonical.
- **Wake Phrase Hint Set**: A bounded, deterministic list of wake aliases and curated variants used to bias wake recognition toward canonical wake phrases.
- **Approved Wake Alias Catalog**: The canonical set of wake aliases and safe variants used by both hints and strict local fallback.
- **Wake Miss Marker**: A field-safe event/marker emitted when no canonical wake is detected and the assistant returns to standby.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With cloud wake recognition configured and available, at least 95% of canonical wake fixtures are accepted within the wake listening window (≤ 7 seconds).
- **SC-002**: With cloud wake recognition unavailable (timeout or network down) and strict local fallback enabled, at least 90% of canonical wake fixtures are accepted within the wake listening window (≤ 7 seconds).
- **SC-003**: Across a negative fixture set (noise + non-wake speech), wake false accepts are 0 for the covered fixtures.
- **SC-004**: In a repeated-miss stability run (at least 50 consecutive wake misses), the assistant remains in standby and continues accepting new wake attempts without crash or stall.
- **SC-005**: For 100% of wake attempts in validation, the system emits a field-safe wake outcome including outcome type and source classification, with no raw utterance retention by default.
- **SC-006**: In standby, 100% of covered wake attempts produce an outcome (accepted, rejected, or missed) and return control to standby or active flow within 7 seconds.

## Assumptions

- A canonical wake alias list already exists (or can be defined) and is used as the authoritative wake acceptance gate.
- A cloud speech recognition provider may be configured, but the assistant must function safely when it is unavailable.
- A strict local wake recognizer is available as a bounded, grammar-like fallback and can be exercised without network connectivity.
- Hardware-trigger wake and low-power keyword wake remain supported and are not in scope for redesign.
- Validation can use deterministic fixtures and simulated provider outcomes without requiring live credentials or storing raw speech content by default.
