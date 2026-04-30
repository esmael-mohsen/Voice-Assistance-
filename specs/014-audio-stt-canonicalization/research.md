# Research: Audio Front-End, Hybrid STT, and Command Canonicalization

## Decision: Add a focused `core/audio/` package instead of growing `core/stt.py` into a monolith

- **Decision**: Introduce a small `core/audio/` package for capture profiles,
  raw audio normalization, and endpoint-quality helpers while keeping
  orchestration and recognizer selection in `core/stt.py`.
- **Rationale**: Phase 14 adds enough audio-domain behavior that keeping every
  step inside `core/stt.py` would make future tuning harder. A focused
  subpackage preserves the current architecture while creating a clean boundary
  for reusable audio utilities.
- **Alternatives considered**:
  - Put all audio logic directly into `core/stt.py`: rejected because the file
    is already responsible for recognizer orchestration and cancellation flow.
  - Add a new top-level `audio/` package: rejected because the existing `core/`
    package is already the runtime authority and a new top-level package is not
    necessary.

## Decision: Keep microphone capture local and apply lightweight pre-processing before transcription

- **Decision**: Continue using the existing microphone capture path, but insert
  profile-driven mono normalization, sample-rate normalization, DC offset
  removal, high-pass filtering, and loudness leveling before transcription.
- **Rationale**: The repo already captures audio locally through the current
  speech stack. Adding a lightweight preprocessing stage is the smallest change
  that directly addresses clipped, weak, and noisy utterances without forcing a
  new capture backend.
- **Alternatives considered**:
  - Skip audio pre-processing and focus only on transcript cleanup: rejected
    because missing or distorted audio cannot be repaired reliably after the
    fact.
  - Add heavy always-on noise suppression: rejected because Phase 14 must stay
    realistic for Raspberry Pi 4 CPU limits.

## Decision: Use WebRTC VAD plus bounded padding to drive endpointing and clipping hints

- **Decision**: Reuse the existing `webrtcvad` dependency for speech-boundary
  scoring, combine it with profile-specific pre-roll and post-roll padding, and
  emit explicit capture metadata including suspected clipping at the start or
  end of the utterance.
- **Rationale**: The dependency is already present, and VAD-based boundary
  hints are a practical way to improve full-utterance capture while preserving
  the current recognizer flow.
- **Alternatives considered**:
  - Rely only on `SpeechRecognition` pause timing: rejected because the current
    phase specifically targets clipped starts and endings.
  - Add repeated re-listen loops until clipping disappears: rejected because
    the spec requires bounded recovery and short prompts.

## Decision: Make Vosk the preferred local-first recognizer for command and closed-vocabulary modes

- **Decision**: Use Vosk as the preferred local-first decode path for command,
  onboarding, and confirmation capture when models are available, with the
  broader recognizer path reserved for bounded rescue behavior or compatibility
  fallback.
- **Rationale**: The repository already includes `vosk` and local model support
  in `core/stt.py`. Vosk is well suited to local command recognition, works
  offline, and can support grammar-constrained decoding for closed vocabularies
  without making cloud recognition the default.
- **Alternatives considered**:
  - Keep Google or broad recognition as the first path: rejected because the
    phase requires a free, local-first baseline.
  - Always run both local and rescue recognizers: rejected because it would add
    unnecessary latency to every interaction.

## Decision: Keep rescue recognition bounded and driven by uncertainty, clipping, or disagreement

- **Decision**: Invoke the stronger rescue path only when the local-first
  result is weak, clipped, contradictory, or outside the valid answer set for a
  constrained mode; do not treat rescue recognition as the default path.
- **Rationale**: The feature goals emphasize responsiveness, truthful degraded
  behavior, and Raspberry Pi practicality. Selective rescue improves quality
  without turning every command into a high-latency dual-pass interaction.
- **Alternatives considered**:
  - Disable rescue recognition completely: rejected because noisy or clipped
    utterances need a bounded recovery path.
  - Prefer rescue recognition for all commands: rejected because it weakens the
    offline-first design and exceeds the intended latency budget.

## Decision: Expand the existing command post-processing boundary instead of inventing a second normalization layer

- **Decision**: Extend `core/command_post_processing.py` into the primary Phase
  14 canonicalization boundary for Arabic normalization, English cleanup,
  bilingual alias collapsing, confusion-pair handling, and mode-specific
  dictionary filtering.
- **Rationale**: Phase 13 already introduced a dedicated post-processing stage.
  Extending it is more coherent than creating an overlapping normalization
  module that would duplicate substitution and parser-bridge logic.
- **Alternatives considered**:
  - Push more variants directly into `core/parser.py`: rejected because parser
    keyword sprawl is exactly what Phase 14 is trying to avoid.
  - Add a second standalone canonicalization service: rejected because it would
    fragment the transcript-to-parser path.

## Decision: Store capture profiles and hybrid-policy toggles in existing settings snapshots

- **Decision**: Surface capture-profile defaults, rescue enablement, optional
  enhancement toggles, and qualification-profile selection through
  `settings/settings_manager.py` and `settings/profile_store.py`, with no new
  datastore.
- **Rationale**: Runtime policy already lives in the settings boundary.
  Extending that snapshot keeps configuration testable, consistent across GUI
  and headless flows, and aligned with the repository constitution.
- **Alternatives considered**:
  - Hard-code capture profiles inside recognizer modules: rejected because it
    makes deployment tuning and qualification harder.
  - Add a separate configuration store: rejected because the project already
    has a central persisted profile.

## Decision: Keep qualification evidence metadata-first and benchmark with curated offline samples only

- **Decision**: Default runtime telemetry and qualification artifacts will
  store derived metrics, flags, and profile identifiers only. Any audio-bearing
  benchmark assets used for regression must come from curated offline fixtures,
  not captured live-user utterances from normal operation.
- **Rationale**: The clarification pass established this privacy rule, and it
  fits the broader project pattern of safe observability for an assistive
  wearable runtime.
- **Alternatives considered**:
  - Record live user audio in normal qualification bundles: rejected because it
    expands data exposure without being required by the phase goals.
  - Skip benchmark fixtures entirely: rejected because Phase 14 success
    criteria require measurable gains on noisy, clipped, and bilingual samples.

## Decision: Qualify deployment profiles by demoting expensive enhancements instead of weakening the baseline silently

- **Decision**: If optional enhancement steps such as noise suppression or
  rescue recognition exceed Raspberry Pi 4 qualification budgets, mark them as
  optional-disabled in the default deployment profile and publish evidence for
  the simpler qualified profile.
- **Rationale**: This preserves truthful deployment guidance and avoids
  shipping a default configuration that looks better on paper than it behaves
  on the target device.
- **Alternatives considered**:
  - Keep every enhancement enabled regardless of hardware cost: rejected
    because the target device budget is an explicit project constraint.
  - Remove optional enhancements entirely: rejected because some deployments
    may still benefit from them when the hardware budget allows.
