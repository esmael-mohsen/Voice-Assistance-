# Research: Wake Reliability, Telemetry, and Raspberry Pi Performance Qualification

## Decision: Extend the existing wake path instead of creating a new always-listening runtime

- **Decision**: Keep wake hardening inside `core/wake_word.py`,
  `core/speech/legacy_wake.py`, `core/speech/speakkit_wake.py`, and
  `core/assistant_runtime.py` rather than introducing a separate wake service
  or permanent always-open microphone mode.
- **Rationale**: Phase 11 already established wake-policy boundaries. Phase 15
  needs stronger acceptance, recovery, and measurement rules, not a parallel
  runtime architecture.
- **Alternatives considered**:
  - Add a new dedicated wake daemon: rejected because it would increase
    architectural churn and split runtime authority.
  - Turn production mode into unrestricted always-listening: rejected because
    the spec explicitly excludes heavy always-listening behavior.

## Decision: Use tiered wake scoring with a bounded confirmation window only for weak or noisy detections

- **Decision**: Treat clear high-confidence wake detections as direct entries
  into listening, while weak or noisy detections enter one short confirmation
  window before either promotion or safe return to standby.
- **Rationale**: This matches the clarified product intent: fast wake behavior
  for clear cases without over-promoting noisy borderline detections.
- **Alternatives considered**:
  - Always require confirmation after wake: rejected because it would slow down
    normal interactions and weaken the wearable feel.
  - Never use a confirmation window: rejected because noisy or weak detections
    would either raise false accepts or force overly conservative thresholds.

## Decision: Keep multilingual wake alias handling bounded by canonical alias groups

- **Decision**: Normalize supported wake phrases into a small canonical alias
  catalog and tune acceptance against that bounded set instead of broadly
  expanding multilingual wake vocabulary.
- **Rationale**: The feature must support multilingual use without making false
  accepts explode. Canonical alias groups preserve clarity and measurability.
- **Alternatives considered**:
  - Add many phonetic and conversational wake variants: rejected because the
    false-accept risk would grow faster than the product value.
  - Support one wake phrase only: rejected because the spec explicitly calls
    out multilingual suitability.

## Decision: Make safe barge-in prompt-class driven instead of globally enabled

- **Decision**: Classify spoken prompts into barge-in-safe and protected
  groups, allowing interruption for informational, retry, and wake-ready
  prompts while protecting shutdown, destructive, and explicit confirmation
  prompts until spoken once.
- **Rationale**: Barge-in needs to feel natural without weakening safety.
  Prompt-class policy is the smallest incremental design that preserves both
  responsiveness and risk controls.
- **Alternatives considered**:
  - Enable barge-in for every spoken prompt: rejected because it would weaken
    destructive-action safeguards and confirmation integrity.
  - Disable barge-in entirely: rejected because the spec requires faster
    turn-taking and no unnecessary waiting.

## Decision: Use a shared three-fault recovery budget per interaction cycle

- **Decision**: Track ordinary wake misses, STT failures, and provider faults
  within the current interaction cycle and reset the speech loop to standby
  after the third consecutive fault, with one short recovery announcement.
- **Rationale**: The clarification pass established this threshold, and it
  gives a bounded, easy-to-test recovery rule that prevents stalled loops.
- **Alternatives considered**:
  - Keep retrying until the user stops: rejected because it traps the user in a
    broken interaction.
  - Reset after the first ordinary fault: rejected because it would be too
    brittle for normal background noise and transient provider issues.

## Decision: Emit lightweight structured telemetry to local candidate artifacts by default

- **Decision**: Model speech telemetry as structured events written to local
  artifact bundles by default, with optional pluggable sinks for future export.
- **Rationale**: The phase needs hard numbers without introducing a mandatory
  external observability platform. Local artifact storage satisfies release
  evidence needs and keeps the deployment path simple.
- **Alternatives considered**:
  - Depend on an external logging or telemetry service: rejected because the
    spec explicitly excludes a heavy observability stack.
  - Use plain-text logs only: rejected because replay benchmarking and release
    gates need structured assertions.

## Decision: Reuse curated replay scenarios for quiet, noisy, bilingual, and degraded cases

- **Decision**: Validate telemetry and recovery through a repeatable scenario
  harness that replays curated local benchmark cases for quiet wake, noisy
  wake, bilingual wake, prompt-echo rejection, degraded providers, and
  repeated-fault recovery.
- **Rationale**: The team needs repeatable evidence rather than anecdotal
  operator testing, especially when Raspberry Pi hardware is not available in
  every environment.
- **Alternatives considered**:
  - Manual validation only: rejected because it is not reliable enough for
    release gating.
  - CI-only synthetic assertions with no replay corpus: rejected because the
    phase specifically needs field-like scenarios and telemetry outputs.

## Decision: Separate CI replay validation from Raspberry Pi 4 hardware qualification

- **Decision**: Let CI run replay, contract, and smoke checks, but require the
  latest passing Raspberry Pi 4 qualification run from real hardware before
  pilot or field-release approval.
- **Rationale**: CI often lacks the target hardware, but the phase requires the
  actual Raspberry Pi 4 resource, latency, and thermal behavior to influence
  release decisions.
- **Alternatives considered**:
  - Treat CI replay as sufficient for pilot approval: rejected because it would
    miss the device-budget and thermal constraints that motivate the phase.
  - Require Raspberry Pi hardware for every developer and CI run: rejected
    because it would slow iteration unnecessarily.

## Decision: Keep Pi qualification measurement lightweight and candidate-scoped

- **Decision**: Capture standby CPU, wake CPU spikes, listening and speaking
  CPU or memory, startup latency, repeated wake-cycle stability, and thermal
  behavior through lightweight runtime samples and candidate-scoped artifacts
  rather than a permanent monitoring agent.
- **Rationale**: The project needs repeatable qualification evidence, not a
  full telemetry platform running continuously on-device.
- **Alternatives considered**:
  - Add a persistent monitoring agent: rejected because it would exceed the
    phase scope and distort the device budget being measured.
  - Skip thermal and repeated-cycle measurement: rejected because the spec
    explicitly calls them out as release gates.
