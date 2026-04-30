# Research: Wearable Readiness

## Decision: Introduce priority-aware message routing with duplicate coalescing

- **Decision**: Add a runtime message-priority model (`warning`,
  `action confirmation`, `info`, `error`) and coalesce duplicate
  same-priority messages within a 2-second window.
- **Rationale**: Wearable audio output must stay concise under bursty events.
  Priority routing protects urgent safety feedback, and coalescing reduces
  cognitive overload and repeated speech.
- **Alternatives considered**:
  - FIFO-only ordering: rejected because urgent events can be delayed by stale
    informational output.
  - Newest-wins dropping older messages: rejected because useful confirmation
    context may be lost unpredictably.

## Decision: Use cooperative interruption with immediate preemption semantics

- **Decision**: Implement shared interruption signaling so `stop`, `cancel`,
  and `emergency` preempt active listening or speaking, with non-critical
  interrupted speech discarded by default (no auto-resume).
- **Rationale**: Phase 5 safety behavior depends on predictable preemption.
  Cooperative interruption avoids runtime deadlocks and makes response timing
  measurable.
- **Alternatives considered**:
  - Auto-resume interrupted speech: rejected due to stale or confusing output.
  - Ask every time whether to resume: rejected for excessive interaction load
    in urgent contexts.

## Decision: Enforce bounded STT/TTS windows with explicit timeout outcomes

- **Decision**: Add explicit per-session bounds for listening and speaking and
  return machine-readable timeout/recovery outcomes when bounds are reached.
- **Rationale**: Any unbounded speech call can stall the runtime loop and
  violate wearable reliability requirements.
- **Alternatives considered**:
  - Leave provider defaults unbounded: rejected because failures become
    difficult to recover from safely.
  - Hard-kill worker threads/processes only: rejected as fragile and likely to
    produce inconsistent cleanup behavior.

## Decision: Default wake policy to low-power keyword spotting, fallback to hardware trigger

- **Decision**: Set low-power keyword spotting as the default wake mode and use
  hardware trigger wake as fallback; keep STT-based wake as development-only.
- **Rationale**: This aligns with wearable standby efficiency while preserving
  an always-available wake path when audio wake degrades.
- **Alternatives considered**:
  - Hardware trigger as default: rejected because it reduces hands-free flow.
  - User-configurable-only default at first run: rejected because safety and
    consistency need deterministic baseline behavior.

## Decision: Make provider `requires_network` metadata authoritative for offline policy

- **Decision**: Treat provider/capability network requirements as authoritative
  for degraded behavior and allow on-device fallback only for explicit
  allowlisted commands.
- **Rationale**: Wearable safety requires deterministic refusal or fallback
  behavior under weak connectivity; inferred behavior is risky.
- **Alternatives considered**:
  - Opportunistic fallback for any command with local components: rejected due
    to unpredictable and potentially unsafe execution.
  - Always refuse offline regardless of command: rejected because safe local
    assistance should remain available when explicitly allowlisted.

## Decision: Add critical prompt integrity guardrails for Arabic and English

- **Decision**: Maintain a critical prompt catalog and block/replace corrupted
  critical prompt output with safe fallback text before TTS emission.
- **Rationale**: Garbled onboarding or safety prompts are high-risk in
  non-visual use; integrity checks must run before user-facing speech.
- **Alternatives considered**:
  - Best-effort prompt quality only: rejected because regressions can ship
    silently.
  - Post-synthesis quality checks only: rejected because they detect issues too
    late in the interaction cycle.

## Decision: Define startup readiness and standby low-power signals as explicit runtime milestones

- **Decision**: Model startup as explicit non-visual milestones and validate
  readiness timing plus standby wake responsiveness over sustained idle runs.
- **Rationale**: Wearable usability depends on predictable "ready" cues and
  long-running standby behavior, not just command execution correctness.
- **Alternatives considered**:
  - Reuse desktop startup assumptions without milestone checks: rejected
    because desktop and wearable expectations differ.
  - Startup confirmation only via GUI state: rejected due to headless-first
    requirement.

## Decision: Expand observability around interruption, coalescing, and degraded execution

- **Decision**: Emit structured events for priority routing, coalescing,
  interruption, timeout exits, degraded/offline decisions, and startup
  readiness transitions.
- **Rationale**: The constitution requires testability and measurable
  reliability. These events are required to verify SC-002, SC-003, SC-005, and
  SC-007.
- **Alternatives considered**:
  - Human-readable logs only: rejected because they are hard to aggregate and
    assert in tests.
  - Metrics-only without event context: rejected because debugging failure
    causes becomes difficult.
