# Research: Field Diagnostics and Release Consistency

## Decision: Run release gates through the active Python interpreter and record that context

- **Decision**: Release validation should invoke compile and test checks
  through the same active Python interpreter that launched
  `scripts/release_validate.py`, and the run summary should persist that
  interpreter path and invocation context as part of the run result.
- **Rationale**: Phase 12 explicitly targets reproducibility. The existing gate
  pipeline already centralizes command execution in `core/release_gates.py`, so
  pinning those commands to the current interpreter is the smallest change that
  removes PATH ambiguity and makes the execution context reviewable after the
  run completes.
- **Alternatives considered**:
  - Keep shell commands as bare `python` or `pytest` invocations: rejected
    because they can drift to a different interpreter or tool shim.
  - Move release validation into a new external wrapper script: rejected
    because the existing script already owns release orchestration.

## Decision: Make artifact expectations explicit in the release result

- **Decision**: The release result should declare the expected artifact
  categories, the produced artifact references, and any missing categories
  instead of leaving artifact completeness to implicit manifest inspection.
- **Rationale**: Operators need a stable summary that is useful even when a run
  fails or stops early. The current artifact manifest model already understands
  required kinds, so Phase 12 should surface that information directly in the
  run result rather than requiring manual reconstruction.
- **Alternatives considered**:
  - Rely only on `manifest.json`: rejected because the spec requires a run
    summary and per-gate results to remain useful even if artifacts are missing.
  - Add more placeholder files without summary-level reporting: rejected
    because it hides missing evidence behind weak conventions.

## Decision: Standardize runtime diagnostics around a canonical event envelope

- **Decision**: Provider-selection, offline-policy, and interrupt outcomes
  should emit a shared structured diagnostic event envelope containing
  timestamp, session or run identifier, event category, status or decision,
  reason code, provider context, next state, and latency when relevant.
- **Rationale**: The spec asks for cross-cutting diagnostic consistency, and
  the project already has runtime decision points that can populate those
  fields. A canonical envelope keeps logs comparable across features and avoids
  creating slightly different schemas for each runtime subsystem.
- **Alternatives considered**:
  - Keep separate per-subsystem log payloads: rejected because field review
    becomes slower and harder to teach.
  - Convert everything to free-form text summaries only: rejected because
    release evidence and triage need machine-readable fields.

## Decision: Keep default field artifacts metadata-only and privacy-aware

- **Decision**: Default field diagnostics should exclude raw user utterances
  and preserve only the canonical metadata needed for triage; any deeper
  content capture must be treated as an explicit, narrower troubleshooting path
  outside the default release artifact set.
- **Rationale**: The clarification and OQ-005 both prefer operational metadata
  over raw user content. The current pilot need is to explain runtime
  decisions, not to collect broad conversational transcripts.
- **Alternatives considered**:
  - Store raw utterances in all runtime diagnostics: rejected because it
    expands data exposure without being required for Phase 12.
  - Remove provider or decision context entirely: rejected because that would
    make the artifacts too weak for debugging.

## Decision: Troubleshooting should be artifact-first and ordered by signal strength

- **Decision**: The pilot troubleshooting workflow should always start with the
  run summary, then provider or degraded diagnostics, then offline-policy
  events, then interrupt outcomes and preemption latency, and finally any
  linked supporting artifacts.
- **Rationale**: This is the clarified operator workflow and matches the
  highest-signal evidence already present or planned in the release path.
- **Alternatives considered**:
  - Start from raw logs: rejected because it slows triage and depends on local
    expertise.
  - Split separate flows for every failure class first: rejected because the
    operator needs one short starting path that works across common cases.

## Decision: Preserve diagnostic meaning across headless and GUI paths at the runtime boundary

- **Decision**: Headless and GUI paths should reuse the same runtime-owned
  diagnostic producers so the meaning of provider, offline-policy, and
  interrupt events stays identical regardless of entrypoint.
- **Rationale**: The spec requires cross-path consistency, and the runtime
  already owns the underlying decisions. Making UI code the source of truth
  would violate the project constitution and create divergent field evidence.
- **Alternatives considered**:
  - Add GUI-specific diagnostic translations: rejected because they risk drift.
  - Limit the feature to headless mode only: rejected because the repo still
    supports GUI-driven debugging.

## Decision: Validate the phase with failed-run, parity, and reviewability scenarios

- **Decision**: Phase 12 validation should cover interpreter-pinned gate
  execution, failed-run artifact completeness, provider diagnostics,
  offline-policy diagnostics, interrupt latency diagnostics, and operator
  review workflow coverage.
- **Rationale**: The feature spans release tooling, runtime outcomes, and
  documentation, so a single test layer would miss important regressions.
- **Alternatives considered**:
  - Unit tests only: rejected because release-entrypoint and review-flow
    outcomes cross subsystem boundaries.
  - Documentation-only review: rejected because reproducibility and structured
    diagnostics need executable validation.
