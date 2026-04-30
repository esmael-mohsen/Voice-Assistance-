# Feature Specification: STT Observability, Rollout Gates, and PocketSphinx Decommission

**Feature Branch**: `[023-stt-rollout-observability]`  
**Created**: 2026-04-28  
**Status**: Draft  
**Input**: User description: "Read Phase 21 from docs\implementationPlan.md to do spec number 21 with best practis"

## Clarifications

### Session 2026-04-28

- Q: What is the default destination and retention policy for STT observability evidence? -> A: Store field-safe telemetry events, run summaries, and release evidence in local release artifacts by default with the existing 180-day release-artifact retention policy; external telemetry sinks remain optional.
- Q: What telemetry shape should planning treat as required? -> A: Emit both event-level records and per-run rollups keyed by session or candidate run, using source, rollout mode, status, confidence bucket, failure category, recovery outcome, latency bucket, and reason codes only.
- Q: What rollout posture and rollback precedence should be used by default? -> A: Default to shadow mode for pilots, progress through wake_only, commands_low_risk, then full_cloud_primary, and let rollback settings or environment controls override any rollout mode until field validation is complete.
- Q: Which release gates are blocking for pilot or field approval? -> A: Missing cloud configuration, missing strict fallback, default PocketSphinx usage, unsafe wake fallback, protected-command regression, bilingual regression, failed bounded recovery, and missing or failed Pi 4 qualification block pilot or field approval.
- Q: What is the minimum Pi 4 qualification and PocketSphinx decommission threshold? -> A: Require the approved Pi 4 threshold policy plus zero default PocketSphinx candidates or invocations in production readiness evidence; compatibility-only Sphinx checks remain outside the required accuracy baseline.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand STT Behavior In The Field (Priority: P1)

As a maintainer or release owner, I want field-safe STT telemetry that shows
how recognition attempts, failures, fallbacks, confidence, retries, clipping,
timeouts, Arabic handling, and language mismatch behave, so I can evaluate the
cloud-primary STT rollout without storing raw audio or raw utterances.

**Why this priority**: The team cannot safely improve wake, command, Arabic,
and fallback behavior unless production-like recognition outcomes are
measurable and privacy-preserving.

**Independent Test**: Exercise representative cloud, fallback, retry,
timeout, clipping, confidence, Arabic-failure, and language-mismatch scenarios
and verify each emits field-safe telemetry with source, mode, status,
confidence bucket, and reason-code information only.

**Acceptance Scenarios**:

1. **Given** a cloud STT attempt succeeds or fails, **When** the attempt
   finishes, **Then** field-safe telemetry records the source, mode, status,
   confidence bucket when available, and a non-content reason code.
2. **Given** strict fallback, rescue recognition, retry, clipping, timeout,
   Arabic failure, or language mismatch occurs, **When** the runtime records
   the outcome, **Then** the event can be counted without exposing raw audio or
   raw utterance content.
3. **Given** diagnostics are inspected after a validation run, **When** the
   maintainer reviews the evidence, **Then** cloud failure frequency, fallback
   frequency, confidence distribution, retry rate, clipping rate, timeout rate,
   Arabic failure markers, and language mismatch rate are distinguishable in
   event-level records and per-run rollups.

---

### User Story 2 - Gate Cloud-Primary Rollout Safely (Priority: P2)

As a release owner, I want release gates for cloud configuration, fallback
availability, protected-command safety, bilingual regression, wake fallback,
and Raspberry Pi 4 qualification, so unsafe or unqualified builds do not move
into field use.

**Why this priority**: Rollout safety depends on objective go/no-go checks
before the assistant is placed in production-like wearable conditions.

**Independent Test**: Run release validation with passing and failing
configuration, fallback, protected-command, bilingual, wake fallback, and
Raspberry Pi 4 qualification evidence and verify safety-critical regressions
block release readiness.

**Acceptance Scenarios**:

1. **Given** cloud-primary configuration is missing or invalid, **When**
   release validation runs, **Then** the readiness result fails with a clear
   field-safe reason.
2. **Given** strict local fallback is unavailable or wake fallback is unsafe,
   **When** release validation runs, **Then** rollout readiness is blocked.
3. **Given** protected-command confirmation or bilingual command regression
   checks fail, **When** release validation runs, **Then** the release is
   marked unsafe until the regression is resolved.
4. **Given** Raspberry Pi 4 qualification evidence is present, **When**
   release validation evaluates it, **Then** wake latency, command recognition
   latency, fallback latency, CPU usage, and memory usage are compared against
   the approved Pi 4 threshold policy.

---

### User Story 3 - Recover Predictably From STT Failure Scenarios (Priority: P3)

As a blind or low-vision user, I want STT failures to lead to bounded recovery
such as fallback, retry, safe refusal, or standby, so recognition problems do
not crash the assistant or create confusing behavior.

**Why this priority**: Field conditions include weak networks, missing
credentials, provider limits, missing fallback models, microphone timeouts,
clipping, and language mismatch; each must fail in a controlled way.

**Independent Test**: Run no-network, missing-credential, expired-credential,
quota/rate, cloud-timeout, missing-fallback, microphone-timeout,
repeated-clipping, and language-mismatch fixtures and verify every case
returns a bounded user-safe result with field-safe diagnostics.

**Acceptance Scenarios**:

1. **Given** network, credential, quota, or cloud timeout failure occurs,
   **When** recognition cannot complete through the primary path, **Then** the
   assistant falls back, retries, refuses safely, or returns to standby without
   an unhandled crash.
2. **Given** the fallback model is unavailable, **When** fallback would be
   needed, **Then** the assistant reports a field-safe unavailable-fallback
   reason and chooses retry, safe refusal, or standby.
3. **Given** repeated clipped utterances, microphone timeout, or language
   mismatch occurs, **When** the assistant handles the failure, **Then** the
   user receives a short non-visual recovery path and diagnostics record the
   reason without raw content.

---

### User Story 4 - Decommission PocketSphinx From The Active STT Path (Priority: P4)

As a maintainer, I want PocketSphinx removed from required production
recognition and release expectations after validation, so the supported STT
architecture is clear: cloud primary with strict local fallback and documented
compatibility limits.

**Why this priority**: Keeping a legacy recognizer in the active accuracy
baseline makes release results harder to interpret and increases maintenance
surface after the compatibility window.

**Independent Test**: Inspect release dependencies, default runtime behavior,
required accuracy baselines, and STT documentation to verify PocketSphinx is
not required for production recognition while any remaining compatibility path
is explicitly documented.

**Acceptance Scenarios**:

1. **Given** a default production recognition path is selected, **When** STT
   readiness is evaluated, **Then** readiness evidence shows zero default
   PocketSphinx candidates or invocations.
2. **Given** legacy environments still reference PocketSphinx compatibility,
   **When** documentation is reviewed, **Then** the compatibility note explains
   its non-primary status and rollback limits.
3. **Given** release accuracy baselines are generated, **When** required checks
   are listed, **Then** Sphinx-specific accuracy tests are not part of the
   required production baseline.

### Edge Cases

- Network is unavailable during a cloud-primary recognition attempt.
- Cloud credentials are missing, expired, malformed, or not authorized.
- Cloud quota or provider rate limits prevent recognition.
- Cloud recognition times out after partial or no result.
- Strict fallback is configured but its local model is missing or unusable.
- Microphone capture times out or repeatedly clips the recognition window.
- Recognition returns low confidence, missing confidence, or conflicting
  alternatives.
- Arabic or bilingual recognition fails while a fallback or retry is possible.
- Language mismatch occurs between detected speech and selected command
  context.
- Rollout mode is shadow-only and must not alter user-visible behavior.
- Rollback settings are present and must remain usable during field
  validation and must override the current rollout mode when set.
- A release build passes replay validation but has missing or failed Pi 4
  qualification evidence; it may remain eligible for internal replay review
  but is blocked from pilot or field approval.
- PocketSphinx is installed in the environment but not explicitly selected for
  compatibility; it must produce zero production candidates or invocations.
- Headless operation needs the same diagnostics and recovery behavior as GUI
  debug mode.

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: Improves safety for blind or low-vision users by
  making STT failures measurable and recoverable without relying on visual
  inspection.
- **Audio UX**: Recovery prompts should be short, direct, and task-oriented;
  confirmation remains required for protected commands and repeated failures
  should avoid long spoken explanations.
- **Non-Visual Operation**: Rollout state, fallback readiness, failure
  category, and recovery outcome must be observable in field-safe diagnostics
  and usable in headless validation.
- **Failure Handling**: Network, credential, quota, timeout, clipping,
  fallback-unavailable, Arabic failure, and language mismatch scenarios must
  end in fallback, retry, safe refusal, or standby rather than an unhandled
  crash.
- **Risk Controls**: Release gates must block safety-critical regressions,
  protected-command confirmation failures, missing fallback readiness, and
  rollout modes that would remove rollback during field validation; missing or
  failed Pi 4 qualification blocks pilot and field approval.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST emit field-safe telemetry for every cloud
  recognition attempt, including source, rollout mode, status, confidence
  bucket when available, and non-content reason code.
- **FR-002**: The system MUST measure strict fallback frequency, rescue
  recognition frequency, retry rate, clipping frequency, timeout frequency,
  Arabic recognition failure markers, and language mismatch rate.
- **FR-003**: Telemetry and diagnostics MUST NOT store raw audio or raw
  utterance content by default.
- **FR-004**: The system MUST preserve enough field-safe diagnostics to explain
  whether recognition failed because of cloud availability, credentials,
  quota/rate limits, timeout, fallback availability, audio capture, language
  mismatch, or confidence policy.
- **FR-004a**: The system MUST store field-safe STT telemetry events, per-run
  rollups, and release evidence locally by default with the existing 180-day
  release-artifact retention policy; external telemetry sinks are optional.
- **FR-004b**: Required STT telemetry records MUST be keyed by session or
  candidate run and include source, rollout mode, status, confidence bucket,
  failure category, recovery outcome, latency bucket, and reason codes only.
- **FR-005**: Release validation MUST detect invalid cloud-primary
  configuration before a field rollout is considered ready.
- **FR-006**: Release validation MUST detect unavailable strict local fallback
  before a field rollout is considered ready.
- **FR-007**: Release validation MUST verify that default production
  recognition produces zero PocketSphinx candidates or invocations.
- **FR-008**: Release validation MUST include wake fallback correctness,
  protected-command confirmation, and bilingual command regression outcomes.
- **FR-009**: Raspberry Pi 4 qualification MUST capture wake latency, command
  recognition latency, fallback latency, CPU usage, and memory usage for
  recognition windows.
- **FR-009a**: Raspberry Pi 4 qualification MUST compare recognition latency
  and resource evidence against the approved Pi 4 threshold policy, including
  the existing baseline-regression limits and resource ceilings.
- **FR-010**: Safety-critical release gates MUST fail pilot and field
  readiness when cloud configuration, strict fallback readiness, default
  PocketSphinx exclusion, wake fallback correctness, protected-command
  confirmation, bilingual command behavior, bounded recovery behavior, or Pi 4
  qualification regresses.
- **FR-011**: The system MUST classify no-network, missing-credential,
  expired-credential, quota/rate, cloud-timeout, missing-fallback,
  microphone-timeout, repeated-clipping, and language-mismatch scenarios into
  bounded outcomes.
- **FR-012**: Each STT failure scenario MUST resolve to fallback, retry, safe
  refusal, or standby without an unhandled runtime crash.
- **FR-013**: The system MUST support staged rollout modes in the recommended
  pilot order: `shadow`, `wake_only`, `commands_low_risk`, then
  `full_cloud_primary`.
- **FR-014**: Shadow rollout mode MUST collect field-safe recognition metadata
  without changing user-visible command behavior.
- **FR-015**: Rollback controls MUST remain available through field validation,
  MUST override any rollout mode when set, and MUST NOT be removed until field
  validation is complete.
- **FR-016**: PocketSphinx MUST be removed from active production recognition
  requirements after validation while any remaining compatibility path is
  documented.
- **FR-017**: Sphinx-specific tests MUST NOT be required for the production
  accuracy baseline after decommissioning, except for compatibility-only checks
  that prove zero default production usage.
- **FR-018**: STT documentation MUST describe cloud-primary recognition,
  strict local fallback, rollout modes, troubleshooting categories,
  Raspberry Pi 4 qualification expectations, and PocketSphinx non-primary
  status.
- **FR-019**: Field-safe diagnostics MUST remain available in headless and GUI
  debug operation.
- **FR-020**: Release evidence MUST distinguish telemetry collection,
  readiness gates, failure-scenario recovery, rollout mode validation, and
  PocketSphinx decommission status.

### Operational & Quality Requirements

- **OQ-001**: The affected runtime layer is speech recognition, runtime
  diagnostics, release validation, and field documentation.
- **OQ-002**: Recognition providers and fallbacks MUST remain behind existing
  speech-provider boundaries with bounded timeout and fallback behavior.
- **OQ-003**: Runtime-affecting changes MUST include structured logging,
  smoke validation, and measurable latency or reliability expectations for
  recognition attempts and fallback recovery.
- **OQ-004**: STT readiness outcomes MUST provide structured result fields for
  user-facing guidance, status, field-safe payload, and error category when
  applicable.

### Key Entities *(include if feature involves data)*

- **STT Telemetry Event**: A field-safe recognition event describing source,
  rollout mode, status, confidence bucket, failure category, and recovery
  outcome without raw audio or raw utterance content.
- **STT Telemetry Rollup**: A per-session or per-candidate-run summary of
  field-safe STT counts, rates, confidence buckets, latency buckets, failure
  categories, and recovery outcomes.
- **Rollout Mode**: A staged deployment state that determines whether cloud
  recognition is observed only (`shadow`), used for wake only (`wake_only`),
  used for low-risk commands (`commands_low_risk`), or used fully with strict
  local fallback (`full_cloud_primary`).
- **Release Gate Result**: A readiness record that reports pass/fail status
  for cloud configuration, fallback availability, protected-command safety,
  bilingual regression, wake fallback, Pi 4 qualification, and PocketSphinx
  decommission status, including whether the result blocks pilot or field
  approval.
- **Failure Scenario Result**: A bounded recovery record for network,
  credential, quota, timeout, fallback, microphone, clipping, language, and
  confidence failures.
- **Pi 4 Qualification Snapshot**: A field validation summary of wake latency,
  command recognition latency, fallback latency, CPU usage, and memory usage.
- **PocketSphinx Compatibility Note**: A documented compatibility status that
  clarifies any legacy path is not part of the required production accuracy
  baseline.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of covered STT attempt, fallback, retry, clipping, timeout,
  Arabic-failure, and language-mismatch fixtures emit field-safe event records
  and per-run rollups without raw audio or raw utterance content.
- **SC-002**: Release validation fails 100% of covered missing cloud
  configuration, missing fallback, unsafe wake fallback, protected-command
  regression, bilingual command regression, bounded-recovery regression,
  default PocketSphinx usage, and missing or failed Pi 4 qualification
  scenarios that would otherwise be approved for pilot or field use.
- **SC-003**: 100% of covered STT failure scenarios resolve to fallback,
  retry, safe refusal, or standby without an unhandled runtime crash.
- **SC-004**: Raspberry Pi 4 qualification evidence reports wake latency,
  command recognition latency, fallback latency, CPU usage, and memory usage
  for every covered qualification run and marks the run against the approved
  threshold policy.
- **SC-005**: Default production readiness evidence shows PocketSphinx is not
  required for active recognition or the required production accuracy baseline
  by recording zero default PocketSphinx candidates or invocations.
- **SC-006**: Field diagnostics can attribute 100% of covered recognition
  failures to cloud, fallback, audio capture, language mismatch, confidence
  policy, or rollout configuration categories.

## Assumptions

- Cloud-primary STT and strict local fallback already exist as selectable
  recognition paths from previous phases.
- Field validation can run without an external telemetry service by using
  local field-safe diagnostics and release evidence artifacts.
- Local release evidence follows the existing 180-day release-artifact
  retention policy unless a later governance decision changes it.
- Raspberry Pi 4 remains the target hardware qualification baseline for the
  wearable validation path.
- Rollback controls remain configuration-driven until field validation is
  complete.
- PocketSphinx compatibility, if still present, is legacy-only and not a
  production accuracy requirement.
