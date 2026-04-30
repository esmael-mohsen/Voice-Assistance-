# Feature Specification: Capability Refactor

**Feature Branch**: `[004-capability-refactor]`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: User description: "Read Phase 4 from docs/implementationPlan.md and create a specification with best practices"

## Clarifications

### Session 2026-04-18

- Q: What capability timeout policy should migrated capabilities use? -> A: Use capability-specific timeouts with a hard maximum of 10 seconds.
- Q: What is the minimum migration scope for this feature? -> A: Deliver one real capability end-to-end, plus shared contract and fallback scaffolding for the rest.
- Q: Which capability should be the first real migration target? -> A: Obstacle detection.
- Q: How should fallback behave when a migrated real capability fails at runtime? -> A: Return a safe failure for migrated capabilities; keep fallback only for unmigrated or test-only paths.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trust Real Capability Responses (Priority: P1)

As an operator, I can use the first migrated real capability and receive clear
spoken feedback plus a stable machine-readable result without depending on the
legacy shared mock behavior.

**Why this priority**: The phase only proves its value if at least one real
capability works end-to-end and shows the new architecture is safer and more
trustworthy than the current bottleneck.

**Independent Test**: Validate obstacle detection as the first migrated real
capability in both headless and GUI-assisted runtime paths and confirm it
returns the intended spoken guidance, machine-readable outcome, and safe
recovery behavior.

**Acceptance Scenarios**:

1. **Given** obstacle detection has been migrated as the first real capability,
   **When** the operator requests it, **Then** the assistant completes the
   action with clear voice feedback and a stable structured outcome.
2. **Given** the same migrated capability is used in headless and GUI-assisted
   modes, **When** the request succeeds, **Then** the user-visible behavior and
   returned outcome remain equivalent.
3. **Given** the migrated capability is temporarily unavailable, **When** the
   operator requests it, **Then** the assistant fails safely with clear spoken
   guidance instead of hanging or returning a raw internal message.

---

### User Story 2 - Rely On Consistent Capability Contracts (Priority: P2)

As a runtime integrator, I can interact with each migrated capability through a
consistent control and result pattern so downstream logic does not depend on
capability-specific quirks or raw spoken strings.

**Why this priority**: Consistent contracts are what make incremental rollout
possible; without them, each new capability would keep increasing coupling and
regression risk.

**Independent Test**: Run contract validation across migrated capabilities and
confirm action, status, start, and stop behavior return stable, machine-safe
outcomes in normal and failure conditions.

**Acceptance Scenarios**:

1. **Given** two migrated capabilities, **When** the runtime requests command
   execution or status information, **Then** both return outcomes in the same
   structured shape.
2. **Given** a capability is already active or already stopped, **When** the
   runtime repeats the same control request, **Then** the capability responds
   consistently without duplicate side effects.
3. **Given** a capability needs to describe its current state, **When** status
   is requested, **Then** the runtime receives machine-readable state data and
   an optional short spoken summary.

---

### User Story 3 - Keep Runtime Responsive During Capability Failures (Priority: P3)

As a reliability owner, I can trust that stalled or failing capabilities do not
block the assistant indefinitely and that the temporary fallback path remains
usable only for unmigrated or test-only areas during incremental migration.

**Why this priority**: Capability refactoring is only safe if failures remain
contained; otherwise a single slow or broken integration can degrade the whole
assistant.

**Independent Test**: Simulate stalled, failing, and partially migrated
capability scenarios and confirm timeout handling, safe failure outcomes, and
restricted fallback behavior keep the assistant responsive.

**Acceptance Scenarios**:

1. **Given** a capability exceeds its allowed response window, **When** the
   assistant waits for a result, **Then** the request ends with a safe failure
   outcome instead of blocking the runtime indefinitely.
2. **Given** a migrated capability fails during execution, **When** the runtime
   handles the error, **Then** the operator hears a brief recovery message and
   downstream consumers receive a machine-readable failure outcome without
   silently reverting to legacy fallback behavior.
3. **Given** some capabilities are still unmigrated, **When** the operator uses
   those areas, **Then** the temporary fallback path remains available only for
   those unmigrated or explicit test-only paths until their real replacements
   are ready.

### Edge Cases

- A capability returns spoken feedback but omits the machine-readable payload.
- A start or stop request is repeated while the capability is already in the
  requested state.
- A capability reports partial success with useful data but also a recoverable
  warning.
- A capability becomes slow, unavailable, or unstable because a provider,
  device, or sensor dependency degrades.
- A migrated capability works in GUI-assisted mode but behaves differently in
  headless runtime.
- One capability depends on context from another capability and the upstream
  result is missing or stale.
- A fallback capability path exists for some unmigrated features while others
  already use real integrations.

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: Blind or low-vision users should receive more
  trustworthy real capability behavior without extra complexity or ambiguity.
- **Audio UX**: Spoken responses should stay brief, action-oriented, and easy
  to distinguish across success, unavailable, timeout, and failure outcomes.
- **Non-Visual Operation**: Every migrated capability must remain usable
  without relying on visual debug surfaces or screen-only disambiguation.
- **Failure Handling**: Slow, unavailable, or failing capabilities must return
  safe spoken guidance and machine-readable failure outcomes rather than
  blocking the assistant, exposing raw internal strings, or silently reverting
  migrated capabilities to mock behavior.
- **Risk Controls**: Capability migration must preserve existing command-layer
  safeguards and must not allow a failing capability to destabilize the primary
  assistant loop.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST migrate capabilities from the shared legacy mock path
  into independent capability boundaries without changing the supported user
  command set in this phase.
- **FR-002**: System MUST allow migrated capabilities to support a consistent
  action, activation, deactivation, and status interaction pattern.
- **FR-003**: System MUST return a structured capability outcome for success,
  status, timeout, and failure scenarios instead of raw spoken strings alone.
- **FR-004**: Structured capability outcomes MUST include user-facing spoken
  guidance and machine-readable state or payload data when applicable.
- **FR-005**: System MUST preserve a temporary fallback path only for
  unmigrated or explicit test-only capability behavior during the incremental
  rollout.
- **FR-006**: System MUST ensure repeated start or stop requests are idempotent
  and do not create duplicate side effects.
- **FR-007**: System MUST enforce capability-specific response windows for each
  migrated capability, and no capability may exceed 10 seconds before returning
  a safe timeout outcome.
- **FR-008**: System MUST provide a machine-readable status view for each
  migrated capability, with an optional short spoken summary for the operator.
- **FR-009**: System MUST keep capability outcomes equivalent across headless
  and GUI-assisted runtime paths.
- **FR-010**: System MUST support incremental migration so real integrations can
  be introduced one capability at a time without breaking unaffected
  capabilities, and this feature MUST deliver one real capability end-to-end
  plus the shared contract and fallback scaffolding needed for later
  migrations.
- **FR-011**: System MUST make capability failure outcomes safe, explicit, and
  recoverable for both operators and downstream consumers.
- **FR-012**: System MUST NOT use the fallback path to mask runtime failures in
  already migrated real capabilities, and those capabilities MUST return safe
  explicit failure outcomes instead.

### Operational & Quality Requirements

- **OQ-001**: The specification MUST identify the affected runtime layer as the
  capability/controller boundary and its downstream runtime consumers.
- **OQ-002**: Any provider, sensor, or device-backed capability MUST specify
  the service or adapter boundary it will use and the failure-handling
  expectations at that boundary.
- **OQ-003**: Runtime-affecting capability migration MUST define logging, smoke
  validation, and latency or reliability expectations for normal execution and
  timeout recovery.
- **OQ-004**: Capability outcomes MUST describe a structured result contract,
  including `spoken_text`, `status`, `payload`, and `error_code` when
  applicable.

### Key Entities *(include if feature involves data)*

- **Capability Handler**: A single capability's operational boundary that owns
  execution, activation, deactivation, and status behavior.
- **Capability Result**: The structured outcome returned from a capability,
  including spoken guidance, machine-readable payload, status, and failure
  details when relevant.
- **Capability Status Snapshot**: The machine-readable description of a
  capability's current state, readiness, and short summary.
- **Capability Timeout Policy**: The bounded execution expectation used to keep
  the assistant responsive when a capability stalls or becomes unavailable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Obstacle detection as the first migrated real capability
  completes end-to-end validation with correct spoken feedback and structured
  outcomes in 100% of planned acceptance scenarios, while the shared contract
  and fallback scaffolding remain available for unmigrated capabilities.
- **SC-002**: 100% of migrated capability contract checks confirm stable result
  and status shapes across normal, repeated, timeout, and failure conditions.
- **SC-003**: 100% of simulated stalled or unavailable migrated capability
  scenarios return a safe recoverable outcome within the configured capability
  timeout and never later than 10 seconds instead of leaving the runtime
  unresponsive or invoking fallback for already migrated capabilities.
- **SC-004**: Headless and GUI-assisted validation runs produce equivalent
  outcomes for all migrated capability regression scenarios.

## Assumptions

- The current command layer, runtime loop, and speech-provider abstractions are
  stable enough for this phase to focus on capability migration rather than
  command redesign.
- No new user-facing commands are added in this phase; the goal is to replace
  the legacy shared mock capability bottleneck incrementally.
- The minimum acceptable delivery for this feature is one real capability
  end-to-end, with the remaining capabilities still supported through shared
  contract and fallback scaffolding.
- Obstacle detection is the locked first real capability to migrate, followed
  by OCR, system status, money detection, face recognition, and then emotion
  recognition.
- Some capabilities may continue using the temporary fallback path while higher
  priority real integrations are introduced one by one, but migrated real
  capabilities fail safely instead of reverting to fallback behavior.
- Non-visual, headless operation remains the reference experience even when GUI
  tooling is used for debug or validation.

