# Feature Specification: Arabic, Bilingual Canonicalization, and Safety Confidence Hardening

**Feature Branch**: `[022-arabic-command-safety]`  
**Created**: 2026-04-26  
**Status**: Draft  
**Input**: User description: "Read Phase 20 from docs\implementationPlan.md to do spec number 20 with best practis"

## Clarifications

### Session 2026-04-26

- Q: How should supported Arabic and bilingual variant inventory be governed? -> A: Use a curated allowlist tied to the existing supported command catalog; do not learn new executable variants from field utterances by default.
- Q: Which command groups remain protected in this phase? -> A: Keep stop-system, emergency mode, reset and settings-sensitive actions, and critical wearable actions under protected-command rules.
- Q: How should corrupted or mojibake Arabic-like text behave at runtime? -> A: Treat it as non-executable; allow only bounded retry for non-protected flows and safe refusal for protected flows.
- Q: What is the default decision when medium-risk commands have language mismatch or high-impact substitutions? -> A: Require confirmation when there is a stable supported command candidate; retry instead when no stable supported command candidate exists.
- Q: What field-safe metadata must remain visible to downstream safety policy? -> A: Preserve integrity status, substitution markers, confidence band, language mismatch markers, and alternative-conflict markers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand Supported Arabic And Mixed Commands Reliably (Priority: P1)

As a blind or low-vision user, I want supported Arabic and mixed-language commands to resolve into the intended assistant action, so I can speak naturally without repeating myself or switching to rigid phrasing.

**Why this priority**: If supported Arabic and bilingual commands are not understood reliably, the assistant remains difficult to use in real-world spoken interaction.

**Independent Test**: Run supported Arabic, Egyptian-Arabic, Arabizi, and mixed-language command fixtures and verify they resolve to the intended existing command outcome without requiring a screen.

**Acceptance Scenarios**:

1. **Given** a user speaks a supported Arabic command using common letter variants or spoken phrasing, **When** the assistant evaluates the transcript, **Then** it resolves to the intended existing command meaning.
2. **Given** a user speaks a supported command using mixed Arabic and English wording, **When** the assistant evaluates the transcript, **Then** it resolves to the same intended command meaning as the canonical supported phrase.
3. **Given** a recognition path returns a phonetic or mixed-language variation of a supported command that matches the curated variant inventory, **When** the assistant evaluates it, **Then** the assistant converts it into parser-ready text that preserves the intended command meaning.

---

### User Story 2 - Keep Safety Strict For Risky Commands (Priority: P2)

As a user issuing potentially risky commands, I want the assistant to remain strict when transcripts are uncertain or safety-sensitive, so accidental actions never happen for the sake of convenience.

**Why this priority**: Better recognition is only valuable if it does not weaken confirmation rules for protected commands.

**Independent Test**: Run protected-command fixtures with clean, ambiguous, conflicting, and near-miss transcripts and verify that only explicitly confirmed risky actions can proceed.

**Acceptance Scenarios**:

1. **Given** a protected command is recognized with uncertainty, conflicting alternatives, or language mismatch, **When** the assistant evaluates it, **Then** the assistant requires explicit affirmative confirmation before execution.
2. **Given** a risky command phrase is near-miss, corrupted, or only partially matches a protected command, **When** the assistant evaluates it, **Then** the assistant does not execute it directly.
3. **Given** a low-risk command is recognized cleanly with strong evidence, **When** the assistant evaluates it, **Then** the assistant may execute it directly without adding unnecessary friction.

---

### User Story 3 - Reject Corrupted And Unsafe Text Safely (Priority: P3)

As a user in noisy or unstable recognition conditions, I want corrupted Arabic-like text, mojibake, and unsupported near-command phrases to fail safely, so the assistant never acts on garbage input.

**Why this priority**: Misinterpreting corrupted or unsupported text is more harmful than asking for retry or clarification.

**Independent Test**: Run corrupted-text, mojibake, unsupported phrase, and language-mismatch fixtures and verify the assistant retries, confirms, or refuses safely instead of misexecuting.

**Acceptance Scenarios**:

1. **Given** a transcript contains corrupted Arabic-like text, **When** the assistant evaluates it, **Then** the assistant treats it as non-executable command text and responds with bounded retry for non-protected flows or safe refusal for protected flows.
2. **Given** a transcript is close to a supported command but does not meet the supported command boundary, **When** the assistant evaluates it, **Then** the assistant does not execute the command directly.
3. **Given** a transcript has a language mismatch or ambiguity that could change command meaning, **When** the assistant evaluates it, **Then** the assistant asks for confirmation when a stable supported command candidate exists and otherwise retries instead of assuming intent.

---

### User Story 4 - Explain Major Normalization Decisions Safely (Priority: P4)

As a maintainer or release owner, I want field-safe normalization and confidence metadata that explains why the assistant accepted, confirmed, retried, or rejected a command, so I can debug command behavior without storing raw utterances.

**Why this priority**: Accuracy and safety improvements are hard to validate in the field unless the assistant can explain high-impact decisions in a privacy-preserving way.

**Independent Test**: Exercise accepted, confirmed, retried, and rejected command fixtures and verify the emitted metadata explains major normalization and safety decisions without raw user content.

**Acceptance Scenarios**:

1. **Given** the assistant applies a major normalization or substitution to supported command text, **When** the command is evaluated, **Then** field-safe metadata records integrity status and any high-impact substitution markers without exposing raw utterance content.
2. **Given** the assistant requires confirmation or retry because of ambiguity, language mismatch, or conflicting alternatives, **When** the command decision is emitted, **Then** the reason is distinguishable in field-safe diagnostics through confidence band, language mismatch markers, or alternative-conflict markers.
3. **Given** the assistant rejects corrupted or unsafe text, **When** the decision is emitted, **Then** the rejection reason remains understandable without exposing raw utterance content.

### Edge Cases

- Corrupted Arabic-like text that visually resembles valid Arabic but cannot be trusted and must remain non-executable.
- Mojibake or encoding-damaged text that should never be interpreted as a command.
- Mixed Arabic and English command phrases that include phonetic spellings or Arabizi.
- Recognition alternatives that point to different command intents with similar scores.
- Near-miss phrases for protected commands that resemble a real command but should not execute and should fail through safe refusal rather than speculative retry into action.
- Confirmation replies that are bilingual, indirect, or include extra filler words.
- Language mismatch between the apparent transcript language and the expected command context, including cases where only one stable supported candidate remains.
- Supported commands spoken with colloquial wording that remains close enough to existing intent boundaries only when the phrase is included in the curated supported variant inventory.

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: Improves hands-free use for blind or low-vision users by making supported Arabic and mixed-language commands easier to understand on the first attempt.
- **Audio UX**: The assistant should continue to prefer short, clear spoken outcomes, with confirmation only when uncertainty or risk justifies it.
- **Non-Visual Operation**: Command understanding, retry behavior, and confirmation decisions must remain understandable without any screen or text display.
- **Failure Handling**: Corrupted text, ambiguity, language mismatch, and unsupported near-command phrases must fail safely through bounded retry, confirmation, or refusal rather than silent misexecution; corrupted protected-command attempts must be refused rather than treated as recoverable executable input.
- **Risk Controls**: Protected commands remain under strict confirmation; better normalization must not weaken stop-system, emergency, reset or settings-sensitive, or critical wearable safeguards.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST normalize supported Arabic command text across common letter-form variants so equivalent spoken inputs can resolve to the same intended command meaning.
- **FR-002**: The system MUST remove decorative or non-meaningful text noise, punctuation noise, and spacing noise before command evaluation.
- **FR-003**: The system MUST treat supported Egyptian-Arabic and bilingual spoken variants as eligible mappings to existing supported command meanings.
- **FR-004**: The system MUST support useful Arabizi and phonetic mixed-language forms only when they map to an already supported command boundary.
- **FR-005**: The system MUST expand supported Arabic and bilingual command vocabulary only through a curated allowlist of phrases that map to existing intent meanings.
- **FR-006**: The system MUST avoid adding vague or overly broad phrases that would materially increase false positives and MUST NOT learn new executable variants from field utterances by default.
- **FR-007**: The system MUST reject corrupted Arabic-like or mojibake text as non-executable command text rather than interpreting it as executable command text.
- **FR-008**: The system MUST preserve enough field-safe metadata to explain major normalization decisions without storing raw utterance content by default, including integrity status and high-impact substitution markers.
- **FR-009**: The system MUST use recognition metadata such as confidence, alternatives, and language mismatch signals when deciding whether to execute, confirm, retry, or refuse.
- **FR-010**: The system MUST allow direct execution for low-risk commands only when recognition evidence and command acceptance are both clean.
- **FR-011**: The system MUST require confirmation for medium-risk commands when confidence is borderline, alternatives conflict, language mismatch exists, or high-impact substitutions were applied, but only when a stable supported command candidate remains after normalization.
- **FR-012**: The system MUST keep high-risk and protected commands under strict explicit affirmative confirmation, including stop-system, emergency mode, reset or settings-sensitive actions, and critical wearable actions.
- **FR-013**: The system MUST NOT directly execute a protected command from a near-miss, ambiguous, or corrupted transcript, and corrupted protected-command attempts MUST be refused rather than retried into execution.
- **FR-014**: The system MUST keep confirmation and clarification behavior consistent across Arabic, English, and mixed-language affirmative or negative replies.
- **FR-015**: The system MUST ensure supported Arabic and bilingual command fixtures resolve to the intended existing command identifiers.
- **FR-016**: The system MUST ensure unsupported or unsafe near-command phrases result in retry, confirmation, or safe refusal instead of silent execution; medium-risk cases without a stable supported command candidate MUST retry rather than confirm execution intent.
- **FR-017**: The system MUST apply the same safety expectations regardless of whether the transcript came from the primary recognition path or a bounded fallback path.
- **FR-018**: The system MUST surface language mismatch, ambiguity, integrity, and alternative-conflict markers when they materially affect command confidence or safety handling.
- **FR-019**: The system MUST provide regression coverage for supported Arabic commands, bilingual commands, phonetic variants, corrupted text, protected commands, and language-mismatch scenarios.
- **FR-020**: Post-processing decisions that materially change command interpretation MUST remain visible to downstream confidence and safety policy decisions through integrity status, substitution markers, confidence band, language mismatch markers, and alternative-conflict markers.

### Operational & Quality Requirements

- **OQ-001**: The affected runtime layers MUST remain within the existing command normalization, parser, dialog, and runtime-decision surfaces rather than introducing a separate command system.
- **OQ-002**: The feature MUST preserve the existing adapter boundary between recognition output and command decision logic.
- **OQ-003**: Validation MUST cover primary recognition, bounded fallback recognition, Arabic/bilingual normalization, and protected-command safety behavior.
- **OQ-004**: Field-safe diagnostics MUST explain major normalization, ambiguity, and safety outcomes without logging raw utterance content by default.

### Key Entities *(include if feature involves data)*

- **Normalized Command Candidate**: A field-safe representation of transcript text after supported normalization and canonicalization decisions have been applied.
- **Variant Mapping Rule**: A curated allowlist mapping from a supported Arabic, bilingual, or phonetic phrase variant to an existing intended command meaning.
- **Safety Decision Record**: A machine-readable summary of whether a command was executed, confirmed, retried, refused, or rejected because of ambiguity, corruption, risk, or missing stable candidate support.
- **Text Integrity Assessment**: A field-safe determination of whether recognized text is trustworthy enough for command evaluation, should trigger bounded retry, or should be refused as corrupted.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 95% of covered supported Arabic command fixtures resolve to the intended existing command identifier without manual re-entry.
- **SC-002**: At least 90% of covered bilingual and phonetic command fixtures resolve to the intended existing command identifier without requiring more than one retry.
- **SC-003**: Zero protected-command fixtures execute without explicit affirmative confirmation when ambiguity, corruption, near-miss phrasing, or uncertainty is present.
- **SC-004**: 100% of covered corrupted Arabic-text and mojibake fixtures are rejected safely rather than interpreted as executable commands.
- **SC-005**: 100% of covered command decisions that depend on major normalization, ambiguity, or language mismatch emit field-safe metadata explaining the decision path.

## Assumptions

- The existing command catalog and intent identifiers remain the authoritative scope for what commands are supported.
- The supported Arabic and bilingual variant inventory will be curated alongside the existing command catalog and will not auto-learn executable phrases from field utterances by default.
- Existing command risk tiers already distinguish low-risk, medium-risk, and protected actions.
- Recognition results already provide enough metadata to expose confidence, alternatives, and language context for safety decisions.
- The assistant will continue to prefer metadata-only diagnostics and will not store raw utterance content by default.

