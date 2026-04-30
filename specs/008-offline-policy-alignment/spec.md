# Feature Specification: Offline Truth and Network Policy Alignment

**Feature Branch**: `[008-offline-policy-alignment]`  
**Created**: 2026-04-19  
**Status**: Draft  
**Input**: User description: "Read Phase 8 from docs\implementationPlan.md to do spec number 8 with best practis"

## Clarifications

### Session 2026-04-19

- Q: What manual network-state override model should Phase 8 support? → A: Use a tri-state network mode: `auto`, `force_offline`, or `force_online` for development/testing only.
- Q: What offline-execution approval model should Phase 8 use? → A: Keep a narrow explicit allowlist: only individually approved capabilities may execute offline or in degraded mode.
- Q: How should Phase 8 model availability signals for offline/degraded decisions? → A: Track both general connectivity and provider/service availability separately, and let offline/degraded policy use both signals.

### Session 2026-04-20

- Q: How should the assistant behave when the connectivity probe is temporarily uncertain? → A: Use the last known state briefly, then fall back to offline if the probe remains uncertain.

- Q: How should the development network override behave across restarts? -> A: The manual network override is session-scoped only and always resets to `auto` on startup.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Safe Offline Guidance (Priority: P1)

As a blind or low-vision user, I need the assistant to tell me truthfully when a
request cannot be completed without connectivity so I do not rely on false
promises or unsafe behavior.

**Why this priority**: Truthful offline behavior is the core safety outcome of
this phase. If the assistant misrepresents what it can do while offline, the
user may waste time, lose trust, or attempt a risky action without support.

**Independent Test**: Disable connectivity, request a network-dependent action,
and verify the assistant either refuses safely with localized guidance or uses
an approved local fallback when one exists.

**Acceptance Scenarios**:

1. **Given** the assistant is offline and the user requests a network-dependent
   action with no approved offline path, **When** the request is evaluated,
   **Then** the assistant refuses safely and speaks truthful guidance in the
   active language.
2. **Given** the assistant is offline and the user requests an allowlisted
   action with an approved offline path, **When** the request is evaluated,
   **Then** the assistant uses the degraded path and clearly communicates that a
   fallback mode is active.

---

### User Story 2 - Honest Provider State (Priority: P2)

As a user, I need startup, degraded-mode, and provider readiness behavior to
reflect the real network dependency of the active speech path so I hear honest
guidance before attempting voice interaction.

**Why this priority**: Once safe refusal exists, the next most important need is
consistent truth at the provider/runtime level so the user understands whether
the assistant is ready, degraded, or unavailable.

**Independent Test**: Start the assistant with different provider and
connectivity states and verify that readiness, degraded guidance, and runtime
events all describe the same effective availability.

**Acceptance Scenarios**:

1. **Given** the active speech path depends on connectivity, **When** the
   assistant starts without network access, **Then** it reports degraded or
   unavailable status consistently in spoken guidance and runtime events.
2. **Given** connectivity changes during runtime, **When** the assistant
   reevaluates provider availability, **Then** subsequent decisions and guidance
   reflect the new effective state without contradicting prior status signals.

---

### User Story 3 - Reproducible Offline Policy Decisions (Priority: P3)

As a developer or QA owner, I need a repeatable offline-policy matrix across
providers and allowlisted capabilities so regressions are caught before release
or field testing.

**Why this priority**: Once user-facing behavior is safe and truthful, the team
needs reliable regression protection to keep those guarantees intact over time.

**Independent Test**: Run a regression suite that covers provider type,
connectivity state, manual override state, and allowlisted vs non-allowlisted
capabilities, then confirm the resulting decisions and guidance remain
consistent.

**Acceptance Scenarios**:

1. **Given** a provider/capability/offline-state matrix is executed, **When**
   regression validation completes, **Then** each case produces a deterministic
   policy decision and matching user guidance.
2. **Given** a development override is active, **When** offline policy is
   evaluated, **Then** the override is visible in state and diagnostics and does
   not silently mask true dependency rules.

---

### Edge Cases

- A connectivity probe temporarily disagrees with real network reachability and
  the assistant must avoid falsely claiming success.
- The network drops after startup but before a network-dependent action begins.
- A capability is allowlisted, but its local fallback path is unavailable or
  incomplete.
- A provider appears selectable but cannot function without connectivity once
  the user starts voice interaction.
- A development override is enabled and later removed while the assistant is
  already running.
- A previous test session ended with a manual override enabled and the
  assistant restarts into normal operation.
- Connectivity becomes uncertain for a short period and the assistant must avoid
  rapid state flapping while still converging to a safe offline state if
  certainty is not restored quickly.

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: Prevents blind or low-vision users from receiving
  misleading offline responses and helps them trust whether the assistant can
  really act.
- **Audio UX**: Spoken guidance must be short, explicit, and honest about
  offline, degraded, and unavailable states in Arabic and English.
- **Non-Visual Operation**: All key decisions must remain understandable through
  speech and structured runtime signals without requiring the screen.
- **Failure Handling**: When connectivity is uncertain or unavailable, the
  assistant must prefer safe refusal or an explicitly named degraded path over
  ambiguous or overly optimistic behavior.
- **Risk Controls**: Network-dependent actions must never be presented as ready
  when they are not; offline fallbacks must only be used when approved; manual
  override behavior must remain explicit and bounded to development use.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST classify each supported speech-provider path by
  whether it requires live connectivity for successful voice operation.
- **FR-002**: System MUST maintain a current network-availability state based on
  a reliable connectivity check, while allowing an explicit tri-state override
  mode of `auto`, `force_offline`, or `force_online` for development workflows
  only.
- **FR-003**: System MUST reset any manual network override to `auto` at
  startup so development-only override state cannot persist across sessions.
- **FR-004**: System MUST maintain provider or service availability as a
  distinct signal from general network reachability.
- **FR-005**: System MUST re-evaluate offline policy whenever provider state,
  provider availability, or network availability changes during startup or
  runtime.
- **FR-006**: System MUST use the last known connectivity state only for a
  brief bounded grace window when probe results are uncertain, then fall back to
  offline behavior if uncertainty persists.
- **FR-007**: System MUST refuse execution safely when a user requests an action
  that cannot be completed safely without connectivity.
- **FR-008**: System MUST only allow offline execution for capabilities with an
  approved degraded or local fallback path that is explicitly listed as
  offline-eligible.
- **FR-009**: System MUST provide truthful spoken guidance in the active
  language when the assistant is offline, degraded, or unable to use the active
  provider safely.
- **FR-010**: System MUST keep provider metadata, runtime state, offline-policy
  decisions, and diagnostic events aligned so they do not contradict one
  another.
- **FR-011**: Users MUST be able to receive the same safe offline policy
  behavior in GUI mode, console mode, and headless-first runtime flows.
- **FR-012**: System MUST make development override state visible in diagnostics
  and policy evaluation so test results are interpretable.

### Operational & Quality Requirements

- **OQ-001**: The specification MUST identify the affected runtime layers as
  `core/speech/`, the shared runtime layer, `settings/`, and offline policy
  regression coverage in `tests/`.
- **OQ-002**: Any provider or connectivity behavior MUST define the boundary
  between provider dependency metadata, network-availability state, and offline
  policy evaluation, including the separate role of provider/service
  availability.
- **OQ-003**: Runtime-affecting behavior MUST define logging and regression
  validation for provider-state changes, degraded-mode guidance, offline
  decisions, and bounded handling of uncertain probe results.
- **OQ-004**: Runtime-affecting behavior MUST define startup validation that
  proves persisted runtime state cannot silently reactivate a prior
  development-only network override.
- **OQ-005**: Offline or degraded command outcomes MUST preserve a structured
  result contract that clearly communicates `spoken_text`, `status`, `payload`,
  and `error_code` when applicable.
- **OQ-006**: Validation coverage MUST include provider type, connectivity
  state, allowlisted capability status, and manual override state.

### Key Entities *(include if feature involves data)*

- **Provider Connectivity Profile**: The approved truth about whether a speech
  path can function without live connectivity and what user-facing state it
  should report when offline.
- **Network Availability State**: The current view of whether the assistant can
  rely on external connectivity, including live probe status and a
  development-only tri-state override of `auto`, `force_offline`, or
  `force_online` that resets to `auto` on startup.
- **Provider Availability State**: The current view of whether the active
  speech-provider path is actually usable, independent from raw network
  reachability.
- **Offline Policy Decision**: The evaluated outcome for a command or runtime
  state, such as safe refusal, approved degraded fallback, or normal execution.
- **Capability Offline Eligibility**: The approved determination of whether a
  capability may run offline and under what degraded conditions, based on a
  narrow explicit allowlist rather than inferred fallback behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of network-dependent actions attempted while offline are
  either refused safely or routed to an approved degraded path; none produce a
  false-success spoken response.
- **SC-002**: Connectivity loss or restoration is reflected in runtime state and
  user-facing guidance within 5 seconds of detection.
- **SC-003**: When probe certainty is temporarily lost, the assistant does not
  remain in the previous online state beyond the approved brief grace window
  before converging to offline-safe behavior.
- **SC-004**: 100% of assistant startups begin in `auto` override mode unless a
  new session explicitly sets a development override.
- **SC-005**: 100% of covered offline-policy decisions use both connectivity and
  provider-availability signals without producing contradictory readiness or
  degraded-state guidance.
- **SC-006**: 100% of supported provider and capability combinations in the
  offline regression matrix produce consistent decisions across provider
  metadata, runtime events, and spoken guidance.
- **SC-007**: During offline or degraded startup scenarios, users receive
  explicit readiness guidance in the active language before any network-required
  voice flow proceeds.

## Assumptions

- Users depend on spoken guidance as the primary source of truth during offline
  and degraded conditions.
- Existing runtime logging and event emission can be extended rather than
  replaced.
- The project will continue supporting bilingual Arabic/English guidance for
  critical offline and degraded states.
- Development override support is needed for local testing, but release and
  field validation should still reflect true dependency rules, with `auto`
  remaining the normal operating mode.
- Development-only override state must not persist across restarts, so every
  new assistant session begins from the real detected network state unless a
  tester explicitly chooses another override for that session.
- Offline or degraded execution is opt-in per capability and must not be
  inferred automatically from the mere existence of a fallback path.
- General network reachability and provider/service usability are related but
  not equivalent, so both must be represented in decisions and diagnostics.
- Short-lived probe uncertainty should be handled with a bounded grace period
  rather than an indefinite last-known-state assumption.
