# Feature Specification: Wake Strategy and Low-Power Standby

**Feature Branch**: `[011-wake-strategy-standby]`  
**Created**: 2026-04-21  
**Status**: Draft  
**Input**: User description: "Read Phase 11 from docs\implementationPlan.md to do spec number 11 with best practis"

## Clarifications

### Session 2026-04-21

- Q: How should the assistant behave when more than one permitted wake source can trigger at nearly the same time? -> A: Accept the first valid signal from any permitted wake source, then lock out the others for that wake cycle.
- Q: How should the assistant behave when no permitted wake source is available in the current configuration? -> A: Enter safe standby, provide a one-time degraded notification, and wait for configuration or hardware recovery.
- Q: What is the repeatable light-load validation scenario for wake latency baselines? -> A: Use 10 sequential wake cycles on an otherwise idle assistant session with stable provider availability and no concurrent long-running capability work.
- Q: How often should degraded standby guidance be repeated while the wake source remains unavailable? -> A: Announce degraded standby once per standby entry and again only when the degraded reason changes or a recovery occurs.
- Q: What canonical wake vocabulary should Phase 11 validate? -> A: Use `hi egb` and `مرحبا` as the approved wake phrases for STT or keyword-based validation until a hardware-specific wake phrase catalog replaces them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Wake Safely in Standby (Priority: P1)

As a blind or low-vision wearable user, I want the assistant to remain in a low-power standby state until an approved wake signal occurs so that it does not consume unnecessary attention, battery, or speech processing while idle.

**Why this priority**: Safe, predictable wake behavior is the foundation for wearable use. If standby still depends on open-ended speech processing in production-like use, the assistant remains costly, noisy, and harder to trust.

**Independent Test**: Put the assistant into standby with a production-like wake policy that disallows STT-based wake, then verify that it only leaves standby when an allowed keyword or hardware-trigger signal occurs.

**Acceptance Scenarios**:

1. **Given** the assistant is in standby with keyword wake enabled and STT-based wake disallowed, **When** the approved keyword wake signal occurs, **Then** the assistant leaves standby, enters listening, and gives the expected wake feedback without requiring open-ended STT to be running the whole time.
2. **Given** the assistant is in standby with hardware-trigger wake enabled and STT-based wake disallowed, **When** the hardware trigger fires, **Then** the assistant wakes and begins the active interaction flow without relying on continuous free-form speech monitoring.
3. **Given** the assistant is in standby with STT-based wake disallowed, **When** unrelated ambient speech or non-approved wake phrases are present, **Then** the assistant remains in standby and does not activate from free-form speech alone.
4. **Given** more than one permitted wake signal arrives during the same standby window, **When** the first valid signal is accepted, **Then** the assistant starts only one wake cycle and ignores competing signals until that wake cycle is complete.

---

### User Story 2 - Use a Development Wake Fallback (Priority: P2)

As a developer or tester, I want an STT-based wake fallback that is available only in approved development configurations so that I can test wake flows on non-final hardware without weakening production safety rules.

**Why this priority**: Development still needs a practical wake path before final hardware is always available, but that fallback must stay clearly separated from production behavior.

**Independent Test**: Run the assistant once in a development-allowed wake configuration and once in a production-like configuration, then verify that STT-based wake is accepted only in the development-allowed case.

**Acceptance Scenarios**:

1. **Given** the assistant is in a development configuration that explicitly allows STT-based wake, **When** the approved STT wake phrase is spoken, **Then** the assistant wakes and records that the development fallback path was used.
2. **Given** the assistant is in a production-like configuration with `stt_wake_allowed_in_production` disabled, **When** the same STT wake phrase is spoken, **Then** the assistant does not wake from that phrase and preserves standby safety.
3. **Given** no permitted wake source is available in the current configuration, **When** the assistant enters standby, **Then** it provides one-time degraded guidance, stays in a safe standby state, and does not silently enable a forbidden fallback.
4. **Given** the network becomes weak or unavailable while standby is active, **When** the selected wake source is local and still available, **Then** wake behavior remains usable without switching to a forbidden fallback, and any provider-backed degraded condition is surfaced through bounded guidance.

---

### User Story 3 - Measure Wake Readiness (Priority: P3)

As a maintainer preparing wearable releases, I want repeatable smoke checks and latency baselines for the wake path so that wake behavior stays measurable across refactors and release validation.

**Why this priority**: Wake behavior can regress quietly even when the assistant still "works." Release readiness needs evidence that standby, wake, and first response timing remain acceptable.

**Independent Test**: Run the defined wake smoke suite and baseline capture scenario, then verify that approved wake modes, rejected wake modes, and wake timing outcomes are all recorded and reviewable.

**Acceptance Scenarios**:

1. **Given** the release validation suite is run against a production-like wake configuration, **When** the smoke suite completes, **Then** it reports whether permitted wake modes succeed and forbidden wake modes remain blocked.
2. **Given** the defined light-load validation scenario is executed, **When** successful wake interactions occur, **Then** wake-to-listening and listening-to-response timing results are recorded against the baseline.
3. **Given** degraded standby guidance has already been announced for the current standby entry, **When** the wake source remains unavailable without a state change, **Then** the assistant does not repeat the same degraded guidance continuously.

---

### Edge Cases

- What happens when the preferred wake source is unavailable at startup or becomes unavailable while the assistant is already in standby?
  The assistant stays in safe standby, gives a one-time degraded notification for that standby entry, and waits for a valid recovery instead of enabling a forbidden fallback.
- How does the assistant behave when more than one wake mode is configured and multiple signals arrive close together?
  The first valid permitted signal wins, and later competing signals are ignored until the current wake cycle completes.
- What happens if ambient speech resembles a wake phrase while STT-based wake is disallowed?
- What happens when connectivity becomes weak or unavailable while standby is already active?
  Local permitted wake sources continue to work when available, while provider-backed degraded conditions are surfaced through one-time guidance instead of silently enabling a forbidden fallback.
- How does standby behave in headless mode when no GUI feedback is available?
- What happens when a wake signal arrives while the assistant is recovering from a degraded provider state or a recent interruption?

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: Blind and low-vision users receive a more predictable standby experience that avoids unwanted activation and reduces idle resource cost in wearable use.
- **Audio UX**: Wake acknowledgements should stay short, distinct, and easy to understand without adding long spoken delays before listening begins.
- **Non-Visual Operation**: All wake and standby behavior must remain understandable without a screen, using speech or other non-visual cues only when they help users confirm state changes.
- **Failure Handling**: If a configured wake source is unavailable, rejected, or degraded, the assistant must preserve safe standby behavior, give a one-time degraded notification for the current standby entry, and avoid silently switching to a less safe wake path.
- **Failure Handling**: If connectivity becomes weak or unavailable during standby, local permitted wake sources must keep working when available, while provider-backed degraded conditions must remain truthful and bounded.
- **Risk Controls**: Production-like standby must not depend on open-ended STT wake when that path is disabled; rejected wake attempts must not trigger protected actions or leave the runtime in an ambiguous state.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST honor the configured wake policy each time the assistant enters standby.
- **FR-002**: The system MUST support wake policy decisions for low-power keyword wake, hardware-trigger wake, and a development-only STT wake fallback.
- **FR-002a**: Phase 11 wake validation MUST use the canonical approved wake phrases `hi egb` and `مرحبا` for keyword or STT-based wake paths until a hardware-specific wake phrase catalog is defined.
- **FR-003**: The system MUST prevent STT-based wake from being used in production-like configurations when `stt_wake_allowed_in_production` is disabled.
- **FR-004**: The system MUST keep standby behavior centered on permitted wake signals rather than continuous free-form STT monitoring when a non-STT wake mode is configured.
- **FR-005**: The system MUST leave standby only after a permitted wake signal is recognized and MUST transition into the active listening flow once per accepted signal.
- **FR-006**: The system MUST reject disallowed wake attempts without starting the full interaction flow.
- **FR-006a**: When multiple permitted wake signals occur close together, the system MUST accept the first valid signal and lock out the others until the current wake cycle is complete.
- **FR-007**: The system MUST provide bounded degraded guidance when no permitted wake source is available instead of silently enabling a forbidden fallback.
- **FR-007a**: When no permitted wake source is available, the system MUST enter or remain in safe standby, issue one degraded notification for that standby entry, and wait for configuration or hardware recovery.
- **FR-007b**: When connectivity becomes weak or unavailable during standby, the system MUST preserve any still-available local wake source and surface provider-backed degraded conditions without silently enabling a forbidden fallback.
- **FR-008**: Users and testers MUST be able to intentionally enable STT-based wake in development-only scenarios when policy allows it.
- **FR-009**: The system MUST apply the same wake policy behavior in headless and GUI-driven runtime entry points.
- **FR-010**: The system MUST record which wake mode was selected, whether a wake attempt was accepted or rejected, and any degraded reason associated with standby behavior.
- **FR-011**: The system MUST define smoke validation for production-like wake mode behavior, development fallback behavior, unavailable wake-source behavior, and headless runtime behavior.
- **FR-011a**: The system MUST define validation for GUI bridge parity and weak-network degraded standby behavior when those conditions are relevant to the selected wake mode.
- **FR-012**: The system MUST define baseline measurement for wake-to-listening and listening-to-response timing using a repeatable light-load validation scenario.
- **FR-012a**: The repeatable light-load validation scenario MUST use 10 sequential wake cycles on an otherwise idle assistant session with stable provider availability and no concurrent long-running capability work.
- **FR-012b**: The system MUST avoid repeating unchanged degraded standby guidance within the same standby entry unless the degraded reason changes or recovery occurs.

### Operational & Quality Requirements

- **OQ-001**: The specification MUST identify the affected runtime layer as `core/assistant_runtime.py`, the wake-policy resolution boundary as `core/speech/provider_resolver.py`, the persisted wake-policy baseline as `settings/user_profile.json`, and validation coverage under `tests/`.
- **OQ-002**: Wake-policy behavior MUST remain scoped to runtime and wake-service boundaries rather than being embedded in unrelated UI-only flows.
- **OQ-003**: Runtime-affecting wake changes MUST define logging, smoke validation, and latency expectations for standby entry, wake acceptance, wake rejection, degraded standby behavior, and degraded-notification suppression during unchanged standby conditions.
- **OQ-004**: Any wake or standby outcome contract MUST describe structured result fields for `spoken_text`, `status`, `payload`, and `error_code` when applicable.

### Key Entities *(include if feature involves data)*

- **Wake Mode Policy**: The user or environment-defined rules that determine which wake signals are permitted in the current runtime context and whether STT-based wake is allowed.
- **Standby Session**: The assistant's idle state window, including the active wake policy, allowed wake sources, rejected wake attempts, and degraded-mode status.
- **Wake Signal Outcome**: The structured result of a wake attempt, including the requested wake source, acceptance or rejection status, degraded reason, and any follow-on cue for the user.
- **Wake Latency Baseline**: The measurable record of wake-to-listening and listening-to-response timing for 10 sequential wake cycles on an otherwise idle assistant session.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In production-like validation scenarios where STT-based wake is disabled, 100% of standby sessions ignore free-form STT wake attempts and respond only to permitted wake sources.
- **SC-002**: In the defined light-load validation scenario, at least 95% of accepted wake events reach listening within 1.5 seconds of the wake signal.
- **SC-003**: In the same validation scenario, at least 95% of successful wake interactions begin the first assistant response within 2.5 seconds after listening starts.
- **SC-004**: In 100% of unavailable or disallowed wake-source validation trials, the assistant remains in a safe standby state and records a clear rejected or degraded outcome.
- **SC-004a**: In 100% of degraded standby validation trials, unchanged degraded guidance is spoken no more than once per standby entry unless the degraded reason changes or recovery occurs.
- **SC-004b**: In 100% of weak-network validation trials where a local wake source is still available, the assistant preserves safe local wake behavior and records any degraded provider condition truthfully.
- **SC-005**: Release smoke validation covers production-like wake behavior, development-only STT fallback behavior, headless behavior, and degraded wake-source handling before the feature is considered ready.

## Assumptions

- The assistant already has a persisted runtime profile that can express wake-policy preferences without introducing a new datastore.
- A production-like configuration represents the release-intended wearable path, while development mode may temporarily allow broader wake options for testing.
- The defined light-load validation scenario consists of 10 sequential wake cycles in a single active assistant session with no competing long-running capability job during wake measurement.
- Keyword wake and hardware-trigger wake may not both be available on every machine, so the feature must describe safe degraded behavior when a configured source is unavailable.
- The canonical Phase 11 wake vocabulary is limited to `hi egb` and `مرحبا` for validation unless later hardware work introduces a dedicated wake phrase catalog.
