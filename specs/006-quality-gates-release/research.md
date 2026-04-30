# Research: Quality Gates and Release Preparation

## Decision: Use one release-blocking gate pipeline with deterministic order

- **Decision**: Run gates in a fail-fast order:
  `compile -> tests -> lint -> localization -> baseline-compare -> checklist`.
  A failed blocking gate sets release status to `failed`.
- **Rationale**: Deterministic ordering makes failures reproducible and keeps
  investigation focused on the first true blocker.
- **Alternatives considered**:
  - Parallel gate execution with aggregated results: rejected for Phase 6
    because it complicates triage and can hide first-cause failures.
  - Manual checklist-only signoff: rejected because it cannot guarantee
    repeatable technical validation.

## Decision: Treat lifecycle and primary-journey validation as mandatory gates

- **Decision**: Add explicit lifecycle and primary-journey suites as
  release-blocking integration gates for startup, standby, wake, listening,
  speaking, error handling, offline handling, and key user journeys.
- **Rationale**: These flows are the highest-impact safety and usability paths
  for blind and low-vision operation.
- **Alternatives considered**:
  - Unit-only gate policy: rejected because orchestration regressions can pass
    unit tests but fail end-to-end runtime behavior.
  - Ad-hoc manual runbook checks: rejected because pass/fail outcomes are not
    reliably auditable.

## Decision: Store per-metric latency thresholds in a versioned policy record

- **Decision**: Keep approved thresholds per latency metric in a versioned
  policy artifact and block release when any metric breaches its approved
  threshold.
- **Rationale**: The spec requires per-metric gating, and policy versioning
  ensures threshold changes are explicit and reviewable.
- **Alternatives considered**:
  - Single global latency threshold: rejected because wake/listen/speak paths
    have different performance envelopes.
  - Implicit threshold from latest run only: rejected because it allows silent
    drift and unstable release decisions.

## Decision: Compare candidate metrics against approved baseline snapshots

- **Decision**: Capture candidate metrics in a normalized run record and
  compare each required metric to the latest approved baseline snapshot for the
  same scenario/profile.
- **Rationale**: Baseline snapshots keep release decisions anchored to known
  acceptable behavior.
- **Alternatives considered**:
  - Compare to previous commit only: rejected because previous commit might be
    unapproved or already degraded.
  - Compare to long-term moving average only: rejected because it can hide
    abrupt regressions.

## Decision: Enforce localization integrity with a critical-prompt catalog

- **Decision**: Validate a curated Arabic/English critical-prompt set as a
  release-blocking gate and fail when prompts are missing, corrupted, or
  mismatched.
- **Rationale**: Critical prompt regressions are high-risk in non-visual flows
  and must be caught before delivery.
- **Alternatives considered**:
  - Spot-check localization manually: rejected due to low repeatability.
  - Validate only one language: rejected because both Arabic and English are
    required for pilot readiness.

## Decision: Model emergency override as auditable, dual-approval governance

- **Decision**: Allow override only after explicit approval by Engineering Lead
  and QA/Safety owner, with required reason, timestamp, and remediation window
  capped at 48 hours.
- **Rationale**: This preserves controlled emergency flexibility while keeping
  safety accountability explicit.
- **Alternatives considered**:
  - Single-approver override: rejected as insufficient control for risky
    releases.
  - Unlimited remediation window: rejected because unresolved risks can persist
    into field use.

## Decision: Retain release artifacts for 180 days using a manifest contract

- **Decision**: Persist test evidence, baseline comparison outputs, override
  records, and checklist signoff in a structured artifact manifest with
  `retention_until` set to 180 days from approval.
- **Rationale**: The spec requires 180-day retention and auditability.
- **Alternatives considered**:
  - Keep only console logs: rejected because logs are incomplete and hard to
    query.
  - Keep artifacts indefinitely: rejected because it increases maintenance cost
    without policy-driven lifecycle control.

## Decision: Pin runtime and dev dependencies and gate on reproducible commands

- **Decision**: Pin runtime and development tool versions, and standardize gate
  commands (`compileall`, `pytest`, `ruff`) so local and CI runs are aligned.
- **Rationale**: Reproducible environments reduce flaky release gating and
  support predictable troubleshooting.
- **Alternatives considered**:
  - Floating dependency ranges: rejected because upgrades can break gate
    stability unexpectedly.
  - Separate ad-hoc local vs CI command sets: rejected because it creates
    drift and false confidence.
