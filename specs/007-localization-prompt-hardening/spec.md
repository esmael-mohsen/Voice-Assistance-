# Feature Specification: Localization Integrity and Prompt Hardening

**Feature Branch**: `[007-localization-prompt-hardening]`  
**Created**: 2026-04-19  
**Status**: Draft  
**Input**: User description: "Read Phase 7 from docs\implementationPlan.md to do spec number 7 with best practis"

## Clarifications

### Session 2026-04-19

- Q: Which artifact should remain the approved runtime source of truth for the critical prompt catalog? -> A: Keep `settings/user_profile.json` as the runtime baseline source of truth for the approved critical prompt catalog.
- Q: What must the release validation gate prove beyond the baseline catalog contents? -> A: Release validation checks the catalog and also verifies every critical runtime surface resolves through approved catalog keys, failing on embedded or unapproved prompt text.
- Q: Which localization integrity failures must automation detect? -> A: Fail on empty strings, replacement characters, and common Arabic mojibake or garbled-text patterns in Arabic prompt fields.
- Q: What should runtime do if a critical prompt key is missing or corrupt? -> A: Speak an approved same-language emergency fallback for that surface and emit an integrity failure signal.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Hear Correct Arabic Guidance (Priority: P1)

As a blind or low-vision Arabic-speaking user, I need onboarding and system
guidance prompts to be readable and understandable so I can set up and recover
the assistant without confusion.

**Why this priority**: Broken Arabic guidance directly harms accessibility and
can make first-run setup, interruption handling, and offline recovery unsafe.

**Independent Test**: Run an Arabic onboarding and guidance flow and verify
that all critical spoken prompts are readable, natural, and free from broken
characters.

**Acceptance Scenarios**:

1. **Given** the assistant starts in Arabic mode, **When** the user goes
   through onboarding, **Then** language, voice, speed, and name prompts are
   spoken in readable Arabic with no corrupted text.
2. **Given** the assistant needs to announce a critical interruption, offline,
   or confirmation message, **When** that prompt is selected, **Then** the user
   hears clear Arabic guidance instead of broken or unreadable output.

---

### User Story 2 - Keep Critical Prompts Consistent Everywhere (Priority: P2)

As a product and QA owner, I need critical prompts to come from one approved
source so wording stays consistent across onboarding, system guidance, and
recovery flows.

**Why this priority**: Fixing individual broken prompts is not enough if
multiple copies of the same prompt can drift apart later.

**Independent Test**: Review the approved critical prompt set and verify that
all shipped critical prompt surfaces resolve through approved catalog keys to
the same approved Arabic and English content for each prompt key.

**Acceptance Scenarios**:

1. **Given** a critical prompt is defined for onboarding or recovery,
   **When** different assistant flows request that prompt, **Then** they use
   the same approved wording for the active language.
2. **Given** a critical prompt is updated, **When** the updated content is
   shipped, **Then** the change is reflected consistently across all user-facing
   prompt surfaces that depend on it.

---

### User Story 3 - Block Broken Localization Before Release (Priority: P3)

As an engineering and release team, we need automated checks that detect broken
Arabic text patterns and fail validation before delivery so corrupted prompts
cannot silently return.

**Why this priority**: The fix is not durable unless release validation can
catch mojibake and similar corruption automatically.

**Independent Test**: Run localization validation against the shipped prompt
set and confirm the build fails if broken Arabic text patterns are present in
any critical prompt surface.

**Acceptance Scenarios**:

1. **Given** a candidate build contains a corrupted Arabic prompt, **When**
   localization validation runs, **Then** the validation fails and identifies
   the affected prompt.
2. **Given** a candidate build contains only approved Arabic and English prompt
   content, **When** localization validation runs, **Then** the build passes
   the prompt-integrity gate.

### Edge Cases

- A prompt is non-empty but still unreadable because it contains mojibake or
  mixed corrupted characters.
- A prompt contains text that is non-empty and lacks replacement characters but
  still matches known Arabic mojibake patterns.
- Arabic content is correct in onboarding but corrupted in a fallback or
  recovery path.
- A prompt key exists in one language but points to outdated wording in the
  other language.
- A release candidate introduces a new critical prompt that is not added to the
  approved catalog and instead ships embedded or unapproved prompt text.
- A runtime flow falls back to older embedded prompt text instead of the
  approved prompt source.
- A critical prompt key is missing or corrupt at runtime and the assistant must
  use a same-language emergency fallback without leaving the user without
  spoken guidance.

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: Ensures Arabic-speaking blind and low-vision users
  can trust critical spoken guidance during setup, interruptions, and degraded
  operation.
- **Audio UX**: Requires critical prompts to stay readable, concise, and
  unambiguous in both Arabic and English.
- **Non-Visual Operation**: Supports setup and recovery without requiring the
  user to inspect a screen to work around broken spoken text.
- **Failure Handling**: Requires validation and fallback handling so broken
  prompt content is caught before release rather than discovered in the field.
- **Runtime Safety**: Requires missing or corrupt critical prompt entries to
  degrade to approved same-language emergency fallback wording while emitting an
  integrity failure signal for diagnosis.
- **Risk Controls**: Protects onboarding, confirmation, interruption, and
  offline guidance prompts from silently regressing into unreadable output.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST identify and replace corrupted or unreadable text in
  critical user-facing prompts used for onboarding, interruptions,
  confirmations, and offline guidance.
- **FR-001a**: System MUST speak an approved same-language emergency fallback
  for any critical prompt surface when the configured prompt key is missing,
  invalid, or corrupt at runtime.
- **FR-002**: System MUST maintain one approved source of truth for each
  critical prompt in `settings/user_profile.json` as the runtime baseline so
  the same prompt key resolves consistently across assistant flows.
- **FR-003**: System MUST provide approved Arabic and English wording for every
  critical prompt included in release validation.
- **FR-003a**: System MUST require every critical runtime prompt surface in
  onboarding, interruption, confirmation, offline, and recovery flows to
  resolve through an approved catalog key rather than embedded or ad-hoc text.
- **FR-004**: System MUST detect localization integrity failures caused by
  empty values, replacement characters, mojibake, or other broken-text
  patterns in Arabic prompt fields, not only empty or missing prompt values.
- **FR-005**: System MUST fail release validation when any shipped critical
  prompt contains broken Arabic text or otherwise fails integrity checks.
- **FR-006**: System MUST identify which prompt or prompt surface caused a
  localization validation failure so the issue can be corrected before release.
- **FR-006a**: System MUST emit an integrity failure signal whenever runtime
  uses an emergency fallback for a critical prompt surface.
- **FR-007**: System MUST ensure a clean Arabic onboarding run speaks readable
  Arabic for language, voice, speed, and name collection guidance.

### Operational & Quality Requirements

- **OQ-001**: Localization integrity checks MUST cover all critical prompt
  surfaces included in onboarding, system guidance, and degraded or recovery
  flows.
- **OQ-001a**: Release validation MUST fail when any critical prompt surface
  bypasses the approved catalog or resolves to embedded or otherwise
  unapproved text.
- **OQ-002**: Prompt-integrity validation MUST be repeatable and produce clear
  pass/fail results suitable for release decisioning.
- **OQ-002a**: Automated integrity detection rules for Arabic prompts MUST be
  deterministic and based on explicit broken-text patterns suitable for
  regression tests.
- **OQ-003**: Localization failures MUST be auditable from validation output
  without requiring source-level debugging.
- **OQ-004**: The feature MUST preserve non-visual usability by prioritizing
  spoken clarity over wording variation in critical prompts.

### Key Entities *(include if feature involves data)*

- **Critical Prompt Catalog**: The approved set of critical prompts with stable
  prompt keys and approved Arabic and English wording, stored in
  `settings/user_profile.json` as the runtime baseline catalog.
- **Prompt Integrity Finding**: A validation outcome describing whether a
  critical prompt passed or failed integrity review and why.
- **Prompt Surface**: A user-facing situation where a critical prompt is
  presented, such as onboarding, interruption handling, confirmation, or
  offline guidance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of critical prompts used in onboarding, interruption,
  confirmation, and offline guidance are readable and free from broken Arabic
  text in release validation.
- **SC-002**: 100% of Arabic onboarding runs complete with readable prompts for
  language, voice, speed, and name guidance.
- **SC-003**: 100% of localization validation runs fail when mojibake is
  introduced into any critical shipped prompt, including common Arabic
  garbled-text patterns that do not rely on empty values or replacement
  characters alone.
- **SC-004**: 100% of localization failures identify the affected prompt key or
  prompt surface in validation output.
- **SC-005**: 100% of critical runtime prompt surfaces included in release
  validation resolve through approved catalog keys rather than embedded prompt
  text.
- **SC-006**: 100% of simulated missing or corrupt critical prompt runtime
  cases fall back to approved same-language emergency wording and emit an
  integrity failure signal.

## Assumptions

- Arabic and English remain the required supported languages for critical
  prompts in pilot readiness.
- Critical prompts are a bounded subset of all assistant wording and can be
  cataloged explicitly.
- Release validation already exists and can incorporate an expanded
  localization integrity gate.
- The user experience should prefer consistent approved wording over ad-hoc
  prompt variation in critical flows.
