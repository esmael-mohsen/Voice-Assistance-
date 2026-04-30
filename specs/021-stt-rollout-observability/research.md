# Research: STT Observability, Rollout Gates, and PocketSphinx Decommission

## Decision: Use local field-safe release artifacts as the default telemetry destination

- **Decision**: Store STT telemetry events, per-run rollups, release gate
  evidence, Pi 4 qualification snapshots, and decommission evidence in local
  release artifacts by default, using the existing 180-day retention policy.
- **Rationale**: The spec explicitly avoids mandatory external telemetry and
  raw audio/utterance storage. The repository already has release artifact and
  diagnostics patterns, so local evidence keeps field iteration repeatable
  without adding operational dependency risk.
- **Alternatives considered**:
  - Require an external telemetry service: rejected because it conflicts with
    the non-goal and would slow field validation setup.
  - Store raw transcripts for easier debugging: rejected because default
    diagnostics must stay field-safe.

## Decision: Emit both event-level STT telemetry and per-run rollups

- **Decision**: Represent individual recognition attempts as field-safe STT
  telemetry events and aggregate candidate/session evidence into per-run
  rollups.
- **Rationale**: Event-level records explain precise failure and recovery
  decisions, while rollups make release gates and field reviews practical.
  Both forms are needed for SC-001 and SC-006.
- **Alternatives considered**:
  - Emit only logs: rejected because release gates need machine-readable
    counts and rates.
  - Emit only rollups: rejected because failure debugging loses source,
    confidence bucket, latency bucket, and reason-code detail.

## Decision: Keep rollout conservative and rollback-dominant

- **Decision**: Use rollout modes in the order `shadow`, `wake_only`,
  `commands_low_risk`, then `full_cloud_primary`; rollback settings or
  environment controls override any rollout mode until field validation is
  complete.
- **Rationale**: The project has already used conservative rollout controls
  for cloud STT and wake behavior. A rollback-dominant policy keeps field
  testing reversible while still allowing measurable cloud-primary adoption.
- **Alternatives considered**:
  - Start with full cloud-primary behavior: rejected because it increases
    safety and support risk before telemetry and gates are proven.
  - Remove rollback controls after initial validation: rejected because the
    spec requires rollback to remain available through field validation.

## Decision: Treat safety and fallback regressions as blocking release gates

- **Decision**: Block pilot and field approval for missing cloud
  configuration, missing strict fallback, default PocketSphinx usage, unsafe
  wake fallback, protected-command regression, bilingual regression,
  bounded-recovery regression, and missing or failed Pi 4 qualification.
- **Rationale**: These failures directly affect assistive reliability,
  command safety, and rollback readiness. The existing release gate framework
  already supports blocking decisions and evidence references.
- **Alternatives considered**:
  - Make gates advisory warnings: rejected because the spec requires
    safety-critical regressions to fail release validation.
  - Allow pilot approval without Pi 4 evidence: rejected because real hardware
    qualification is the wearable readiness baseline.

## Decision: Reuse the existing Pi 4 threshold policy and extend only if recognition-specific fields are missing

- **Decision**: Compare Pi 4 recognition qualification against the approved
  threshold policy in `settings/release_thresholds.json`, reusing baseline
  regression limits and resource ceilings.
- **Rationale**: The repository already has Pi 4 release gate semantics. Reuse
  avoids creating a second threshold authority and keeps pilot approval
  consistent across phases.
- **Alternatives considered**:
  - Hard-code new recognition thresholds in tests: rejected because threshold
    policy should remain configurable and reviewable.
  - Defer Pi 4 checks to manual notes only: rejected because release readiness
    must be machine-readable.

## Decision: Classify STT failures before user recovery is chosen

- **Decision**: Normalize no-network, credential, quota/rate, timeout,
  fallback-missing, microphone-timeout, clipping, language-mismatch, and
  confidence-policy failures into field-safe failure scenario results before
  selecting fallback, retry, safe refusal, or standby.
- **Rationale**: Recovery behavior must be bounded and explainable for
  non-visual use. A shared taxonomy also lets diagnostics and release gates
  prove that no failure scenario crashes the assistant.
- **Alternatives considered**:
  - Let each recognition path speak its own failure text: rejected because it
    fragments recovery behavior.
  - Collapse all failures into retry: rejected because some states require
    safe refusal or standby.

## Decision: Decommission PocketSphinx by proving zero default production usage

- **Decision**: Production readiness evidence must show zero default
  PocketSphinx candidates or invocations. Compatibility-only Sphinx tests may
  remain, but they are outside the required production accuracy baseline.
- **Rationale**: Earlier phases already moved PocketSphinx behind
  compatibility controls. Phase 21 should make decommissioning auditable
  without deleting useful legacy documentation too early.
- **Alternatives considered**:
  - Delete every Sphinx reference immediately: rejected because legacy
    environments may still need compatibility guidance.
  - Keep Sphinx in the accuracy baseline: rejected because it obscures
    cloud-primary and strict-fallback readiness.

## Decision: Use fixture replay in CI and real Raspberry Pi 4 evidence for pilot and field approval

- **Decision**: CI may validate contracts, rollups, failure recovery, privacy,
  and release-gate logic with deterministic fixtures and replayed evidence,
  but pilot and field approval require a real Raspberry Pi 4 qualification
  snapshot.
- **Rationale**: Fixture replay keeps daily validation fast and deterministic,
  while the Pi 4 baseline catches hardware-specific latency, CPU, memory,
  thermal, and repeated-wake behavior that cannot be inferred reliably from a
  desktop run.
- **Alternatives considered**:
  - Require real Pi 4 hardware for every CI run: rejected because it would make
    common development too slow and fragile.
  - Accept desktop replay for pilot approval: rejected because the spec
    requires approved Pi 4 threshold evidence before pilot or field rollout.
