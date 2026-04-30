# Research: Offline Truth and Network Policy Alignment

## Decision: Treat the legacy speech path as network-required until proven otherwise

- **Decision**: Mark the current legacy speech provider as
  `requires_network=true` for truthful voice-operation readiness, even if some
  wake or local helper surfaces remain available without connectivity.
- **Rationale**: The current legacy STT/TTS path still depends on networked
  services, so reporting it as offline-capable creates false readiness and
  unsafe expectations.
- **Alternatives considered**:
  - Keep legacy marked as offline-capable: rejected because it contradicts the
    real behavior of STT/TTS in the current runtime.
  - Model only SpeakKit as network-dependent: rejected because both user-facing
    speech paths would still drift from reality.

## Decision: Make connectivity truth session-scoped and probe-backed

- **Decision**: Replace the current persisted-boolean interpretation with a
  runtime `ConnectivityState` that always starts in `auto`, is refreshed from a
  live probe at startup, and never restores a previous development override
  across sessions.
- **Rationale**: Persisted `network_available` and override state can become
  stale and falsely influence startup readiness, which is the exact problem
  Phase 8 is meant to eliminate.
- **Alternatives considered**:
  - Trust the persisted `network_available` value at startup: rejected because
    it can be stale before the assistant even starts listening.
  - Persist manual override until explicitly cleared: rejected because it can
    silently leak development behavior into later runs or release validation.

## Decision: Use an injectable standard-library probe with bounded uncertainty

- **Decision**: Introduce a small `NetworkProbe` helper under `core/speech/`
  that performs short, configurable TCP connectivity checks with standard
  library primitives and returns `online`, `offline`, or `uncertain` plus
  latency and failure metadata.
- **Rationale**: This keeps the implementation lightweight, avoids new
  dependencies, and makes unit/integration tests deterministic by allowing the
  probe behavior to be injected.
- **Alternatives considered**:
  - Add a new HTTP/network dependency for probing: rejected because the current
    stack does not need additional packages for this feature.
  - Perform a blocking live probe during every command decision: rejected
    because it would add unnecessary latency and flapping risk.

## Decision: Keep provider availability separate from connectivity truth

- **Decision**: Preserve provider/service availability
  (`ready|degraded|unavailable`) as a separate signal from general connectivity,
  and make offline-policy evaluation consume both signals instead of collapsing
  them into one `network_available` flag.
- **Rationale**: A device may have internet reachability while the active
  provider is unavailable, or a provider may be locally healthy while a
  network-required speech path is still unusable offline.
- **Alternatives considered**:
  - Treat provider failure as equivalent to offline: rejected because it hides
    the difference between general connectivity and provider-specific failure.
  - Ignore provider availability and trust connectivity only: rejected because
    degraded providers would still be reported as ready.

## Decision: Extend structured offline-policy decisions instead of ad-hoc checks

- **Decision**: Expand the current offline-policy evaluation path to return
  explicit structured outcomes that include override mode, detected
  connectivity, effective network availability, provider availability,
  allowlist status, decision, `spoken_text`, and `error_code`.
- **Rationale**: Runtime, resolver, release diagnostics, and regression tests
  already depend on structured evidence; Phase 8 needs a single machine-readable
  truth source rather than scattered booleans and strings.
- **Alternatives considered**:
  - Keep separate runtime/resolver branching logic: rejected because it invites
    drift and contradictory user guidance.
  - Rely on logs only: rejected because tests and release checks need a stable
    payload contract.

## Decision: Reuse Phase 7 critical prompt surfaces for offline and degraded guidance

- **Decision**: Keep offline safe-refusal, degraded startup, and related spoken
  guidance routed through the existing approved critical prompt catalog and
  surface bindings instead of introducing new embedded strings.
- **Rationale**: Phase 7 already established localization integrity guarantees,
  and Phase 8 should strengthen truthful behavior without bypassing those gates.
- **Alternatives considered**:
  - Add new embedded runtime strings for degraded/offline messaging: rejected
    because it would bypass catalog integrity protections.
  - Use English-only fallback text for new offline cases: rejected because the
    product remains accessibility-critical and bilingual.

## Decision: Cover offline truth with a provider-by-provider regression matrix

- **Decision**: Add unit, integration, and smoke coverage that exercises
  provider type, service availability, detected connectivity, override mode,
  uncertainty grace handling, and allowlisted versus non-allowlisted
  capabilities.
- **Rationale**: Offline truth is inherently a matrix problem; a few single-path
  tests would not reliably catch drift between metadata, runtime behavior, and
  user guidance.
- **Alternatives considered**:
  - Rely on a single happy-path offline test: rejected because it would miss
    startup, degraded, override, and provider-specific regressions.
  - Test only the pure function layer: rejected because runtime guidance and
    event payload alignment are part of the feature contract.
