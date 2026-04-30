# Implementation Plan

## Execution Goal
Deliver the next stage of development incrementally on top of the current project, while preserving the existing structure, reducing risk, and preparing the codebase for SpeakKit integration without a rewrite.

## Assumptions
- SpeakKit will be used as a layer or provider inside the speech pipeline, not as a complete replacement for the application.
- The current project remains the main repository.
- `ui/` stays as a local debug and demo interface during development.
- The final glasses version should be headless-first.

## Execution Rules
- Do not remove a complete layer until a working replacement exists.
- Do not move more than one major architectural concern in the same phase.
- Every phase must end with outputs that are runnable and measurable.
- Any change in the parser or runtime must be accompanied by a test or at least a smoke check.

## Phase 0: Baseline Stabilization

### Goal
Stabilize the current project before introducing any new integration.

### Tasks
1. Fix the conflict between `stop` commands and close-app protection inside `ui/assistant_worker.py`.
2. Unify behavior between `main.py --console` and the GUI runtime path.
3. Convert face recognition state in `core/resolver.py` into a structured state model instead of storing spoken strings.
4. Add smoke tests for the parser, resolver, and settings layers.
5. Improve logging for critical failures in the speech and runtime flow.

### Expected Files
- `main.py`
- `ui/assistant_worker.py`
- `core/resolver.py`
- `core/dispatcher.py`
- `settings/settings_manager.py`
- a new `tests/` directory

### Phase Outputs
- A more stable runtime
- Stop commands that behave as expected
- An initial baseline test suite

### Exit Criteria
- The project runs in both GUI and console mode without obvious bugs in the start, stop, and settings flow.

## Phase 1: Runtime Extraction

### Goal
Separate assistant runtime logic from the `customtkinter` UI layer.

### Tasks
1. Create a dedicated runtime layer such as:
   - `core/runtime.py`
   - or `core/assistant_runtime.py`
2. Move the core runtime loop out of `ui/assistant_worker.py` into a reusable runtime service.
3. Turn `assistant_worker.py` into a bridge between the UI and runtime events.
4. Define a unified event model for states such as:
   - standby
   - wake
   - listening
   - thinking
   - speaking
   - error
   - offline

### Expected Files
- new `core/assistant_runtime.py`
- `ui/assistant_worker.py`
- `ui/gui_app.py`
- `main.py`

### Phase Outputs
- The same behavior as today, but with a clearer separation between UI and runtime.

### Exit Criteria
- Both GUI and console mode run on the same runtime layer.

## Phase 2: Speech Abstraction and SpeakKit Adapter

### Goal
Introduce SpeakKit in a structured and replaceable way.

### Tasks
1. Define interfaces or abstract contracts for:
   - `WakeService`
   - `SpeechToTextService`
   - `TextToSpeechService`
2. Wrap `core/stt.py` and `tts/tts_engine.py` as legacy providers.
3. Add new SpeakKit adapters such as:
   - `core/speech/speakkit_stt.py`
   - `core/speech/speakkit_tts.py`
   - `core/speech/speakkit_wake.py`
4. Add configuration to select the active provider.
5. Prepare a fallback path if the primary provider fails.

### Expected Files
- `core/stt.py`
- `tts/tts_engine.py`
- `settings/settings_manager.py`
- new files under `core/speech/`

### Phase Outputs
- A replaceable speech pipeline
- SpeakKit integrated without polluting the rest of the architecture

### Exit Criteria
- The project can run in one of two modes:
  - legacy speech
  - SpeakKit speech

## Phase 3: Command Layer Hardening

### Goal
Move command processing from prototype quality to a layer that can be trusted.

### Tasks
1. Add real test coverage for the core commands in `core/parser.py`.
2. Reduce false positives through:
   - threshold tuning
   - command grouping
   - intent-specific validation
3. Introduce a unified command result model instead of returning strings only.
4. Improve `core/resolver.py` so it handles structured params and session state more clearly.
5. Separate system commands from capability commands.

### Expected Files
- `core/parser.py`
- `core/resolver.py`
- `core/dispatcher.py`
- `tests/test_parser.py`
- `tests/test_resolver.py`

### Phase Outputs
- More accurate command handling
- Clearer state management
- Easier extension for new commands

### Exit Criteria
- A command regression suite covers the most important Arabic and English commands.

## Phase 4: Capability Refactor

### Goal
Replace `mock_controllers.py` incrementally with real capabilities.

### Tasks
1. Split controllers into dedicated files:
   - `controllers/obstacle_controller.py`
   - `controllers/ocr_controller.py`
   - `controllers/money_controller.py`
   - `controllers/vision_controller.py`
   - `controllers/system_controller.py`
2. Define a unified controller contract for each capability:
   - `execute()`
   - `get_status()`
   - `start()`
   - `stop()`
3. Keep `mock_controllers.py` as a temporary fallback or mock backend for testing.
4. Introduce real integrations one by one based on priority.

### Suggested Priority Order
1. obstacle detection
2. OCR
3. system status
4. money detection
5. face recognition
6. emotion recognition

### Phase Outputs
- Independent and extensible capabilities
- A mock layer that is no longer the main bottleneck

### Exit Criteria
- At least the first real capability works end-to-end with clear voice feedback.

## Phase 5: Wearable Readiness

### Goal
Move behavior from a desktop demo toward wearable assistant behavior.

### Tasks
1. Reduce the length of spoken responses.
2. Introduce a message priority model:
   - warning
   - action confirmation
   - info
   - error
3. Prevent long blocking behavior in TTS and STT without controlled timeout handling.
4. Prepare a startup sequence suitable for the glasses.
5. Support low-power considerations in standby mode.
6. Consider tones or haptics if the hardware supports them.

### Expected Files
- `core/assistant_runtime.py`
- `settings/settings_manager.py`
- `tts/tts_engine.py`
- the real controller modules

### Phase Outputs
- Behavior closer to a real assistive product
- Shorter and clearer responses

### Exit Criteria
- A complete experience is usable without depending on the screen.

## Phase 6: Quality Gates and Release Preparation

### Goal
Prepare the pilot version for delivery and field testing.

### Tasks
1. Add tests for the runtime lifecycle.
2. Add integration tests for the primary usage scenarios.
3. Add localization regression checks for critical spoken prompts (Arabic/English) so text integrity cannot silently regress.
4. Measure latency and resource usage and record baselines relevant to wearables (wake → listen, listen → result, result → TTS-start).
5. Write troubleshooting docs and prepare a startup script.
6. Pin dependencies to explicit versions (runtime + dev tooling).
7. Add developer quality gates:
   - include `pytest` and a linter (e.g., `ruff`) as pinned dev dependencies
   - run compile + tests + lint in CI on every change
8. Create a release checklist with wearable-specific items:
   - offline / degraded-mode behavior
   - emergency stop / cancel behavior
   - audio I/O permissions and device access
   - crash recovery expectations

### Expected Files
- `requirements.txt`
- `tests/`
- `docs/`
- new runtime or startup scripts if needed

### Phase Outputs
- A more stable pilot build
- Clearer visibility into issues before running on real hardware

### Exit Criteria
- The build runs in an environment close to the glasses setup with a clear success checklist.

## Phase 7: Localization Integrity and Prompt Hardening

### Goal
Eliminate broken Arabic text (mojibake) and prevent it from ever returning through automated gates.

### Tasks
1. Inventory and replace mojibake strings in critical user-facing prompts (setup, offline guidance, interrupts, confirmations).
2. Consolidate critical prompts into a single source of truth (keep `settings/user_profile.json` catalog as the runtime baseline).
3. Strengthen localization validation so it detects mojibake patterns (not just empty strings or replacement characters).
4. Add a regression test that fails if mojibake is present in any shipped prompt surface.

### Expected Files
- `core/assistant_runtime.py`
- `controllers/mock_controllers.py`
- `core/release_localization.py`
- `settings/user_profile.json`
- new localization integrity tests under `tests/`

### Phase Outputs
- Correct Arabic output in onboarding and system guidance
- A localization gate that blocks mojibake regressions

### Exit Criteria
- A clean Arabic onboarding run (language, gender, speed, name) speaks readable Arabic.
- CI fails if mojibake strings are introduced.

## Phase 8: Offline Truth and Network Policy Alignment

### Goal
Make offline behavior truthful and safe by aligning provider metadata, network detection, and offline policy decisions.

### Tasks
1. Align provider `requires_network` with reality (Legacy STT/TTS currently depend on network).
2. Introduce a small, reliable network probe and keep `network_available` updated (with a safe manual override for development).
3. Tighten offline policy behavior and messaging:
   - safe refusal when a command cannot be executed safely offline
   - explicit degraded-mode guidance when the active provider cannot function without connectivity
4. Add regression tests for offline policy decisions across providers and allowlisted capabilities.

### Expected Files
- `core/speech/provider_registry.py`
- `core/speech/provider_resolver.py`
- `core/assistant_runtime.py`
- `settings/settings_manager.py`
- offline policy tests under `tests/`

### Phase Outputs
- Offline behavior that matches real dependencies
- Clear user guidance when offline or degraded

### Exit Criteria
- With `network_available=false`, network-required actions are refused safely with correct Arabic/English guidance.
- Provider metadata and offline decisions are consistent in logs and events.

## Phase 9: Confirmation, Clarification, and Command Robustness

### Goal
Make safety dialogs resilient to STT variation while preserving strict safety for protected commands.

### Tasks
1. Replace exact-match confirmation parsing with token/phrase-based matching for Arabic and English (e.g., accept "ايوه تمام", "yes please").
2. Unify yes/no/cancel parsing used by resolver and onboarding so behavior is consistent.
3. Improve clarification prompts for parameter-required intents (language/voice) to ask for explicit options and remain bounded (safe stop after retries).
4. Add regression tests for confirmation/clarification/follow-up flows.

### Expected Files
- `core/resolver.py`
- `core/assistant_runtime.py`
- tests for confirmation/clarification under `tests/`

### Phase Outputs
- Protected commands that are safer and more reliable to confirm
- Fewer false cancellations and fewer missed confirmations

### Exit Criteria
- Protected intents never execute without an explicit affirmative confirmation.
- Confirmation succeeds on common STT outputs in both Arabic and English.

## Phase 10: Interrupt Safety and TTS Preemption

### Goal
Provide a reliable, multilingual emergency stop/cancel behavior that can preempt speech output and in-flight work.

### Tasks
1. Expand interrupt detection to Arabic equivalents and common variants.
2. Replace blocking playback so TTS can be interrupted (no "finish the whole audio" behavior).
3. Wire interrupt events through the speech pipeline so STT/TTS/capabilities can stop quickly.
4. Add metrics + tests for preemption latency and ensure bounded behavior under load.

### Expected Files
- `core/assistant_runtime.py`
- `tts/tts_engine.py`
- interrupt-focused tests under `tests/`

### Phase Outputs
- True “stop now” behavior suitable for assistive use
- Measured interruption latency and regression protection

### Exit Criteria
- Saying "stop" or "وقف" interrupts speech quickly and returns to a safe state.
- Preemption latency is measured and remains within an acceptable target.

## Phase 11: Wake Strategy and Low-Power Standby

### Goal
Implement wake behavior appropriate for wearables by respecting wake modes and avoiding always-on STT in standby.

### Tasks
1. Make runtime honor the configured wake modes (keyword low power, hardware trigger, STT-based dev fallback).
2. Ensure STT-based wake is gated to development mode only when `stt_wake_allowed_in_production=false`.
3. Restructure standby so it can block on a hardware/keyword signal instead of continuously running STT.
4. Add smoke tests and latency baselines for wake → listening and listening → response.

### Expected Files
- `core/assistant_runtime.py`
- `core/speech/provider_resolver.py`
- `settings/user_profile.json`
- wake-mode smoke tests under `tests/`

### Phase Outputs
- Lower standby cost and more predictable wake behavior
- Clear dev vs production wake behavior

### Exit Criteria
- In production-like configuration, standby does not depend on STT-based wake.
- Wake behavior matches the configured modes and is measurable.

## Phase 12: Field Diagnostics and Release Consistency

### Goal
Make release validation reproducible and make field debugging practical for pilot deployments.

### Tasks
1. Ensure release scripts run tools via the active Python interpreter (avoid relying on PATH).
2. Standardize runtime diagnostic events for:
   - provider selection and degraded reasons
   - offline policy decisions
   - interrupt outcomes and preemption latency
3. Add a minimal “pilot log review” workflow in docs (what to check first, where to find artifacts).

### Expected Files
- `core/release_gates.py`
- `scripts/release_validate.py`
- `docs/release/troubleshooting.md`

### Phase Outputs
- More reliable validation runs
- Faster root-cause analysis in the field

### Exit Criteria
- A release validation run produces consistent results inside the venv.
- Field logs contain enough structured data to explain failures without a debugger.

## Phase 13: Dialog Stability, Clarification Safety, and Onboarding FSM

### Goal
Stabilize the spoken interaction journey so first-run setup and settings dialogs behave predictably, tolerate STT variation, and never trap the user in confusing retry loops.

### Why This Phase Exists
Current user experience issues are no longer limited to raw STT quality. A meaningful part of the failure rate comes from dialog logic:
- parameter-required intents such as `set language` can be rejected as ambiguous instead of entering clarification
- onboarding steps can accidentally consume prompt echo or unrelated speech
- retries can feel repetitive or mistimed
- language switching during setup can produce inconsistent STT and TTS behavior

This phase fixes the dialog contract first so later STT improvements land on a reliable runtime.

### Tasks
1. Replace ad hoc onboarding flow control with an explicit finite-state model covering:
   - intro
   - language
   - voice gender
   - speech speed
   - user name
   - name confirmation
   - completion
   - bounded failure / safe exit
2. Resolve parser ambiguity for parameter-required settings intents so generic intents such as `set language` and `set voice` prefer clarification instead of immediate rejection.
3. Add a dedicated dialog-policy layer that decides whether a turn should:
   - execute
   - clarify
   - confirm
   - retry
   - ignore as prompt echo
   - stop safely
4. Introduce grammar-constrained response handling for onboarding and clarification states:
   - language accepts only Arabic / English variants
   - voice accepts only male / female variants
   - speed accepts only normal / fast / slow / numeric speed values
   - confirmation accepts only yes / no / cancel variants
5. Improve turn-taking and barge-in behavior during setup:
   - allow the user to answer before the full prompt finishes when safe
   - block the runtime from treating TTS prompt text as a user answer
   - shorten reprompts after retries
6. Normalize setup policy defaults so the first-run flow starts from a deterministic baseline:
   - default language remains `en-US`
   - switching language updates prompt selection, STT language context, and TTS voice context in one place
   - the system does not oscillate between Arabic and English without an explicit accepted answer
7. Add bounded retry and recovery rules for every onboarding state:
   - first failure: short retry
   - second failure: tighter constrained prompt
   - final failure: safe fallback or exit with a clear spoken explanation
8. Add regression coverage for the complete onboarding and clarification journey, including:
   - ambiguous setting commands
   - prompt echo suppression
   - mid-dialog language changes
   - repeated invalid answers
   - barge-in during prompts

### Expected Files
- `core/parser.py`
- `core/resolver.py`
- `core/dispatcher.py`
- `core/assistant_runtime.py`
- `core/dialog_policy.py`
- a new onboarding/dialog state module under `core/`
- `settings/settings_manager.py`
- onboarding and clarification regression tests under `tests/`

### Phase Outputs
- A deterministic spoken setup flow
- Clarification that behaves like a guided dialog instead of a parser failure
- Fewer false retries caused by prompt echo, mistimed capture, or ambiguous generic commands

### Exit Criteria
- `set language` and `set voice` enter clarification reliably instead of being rejected as ambiguous.
- First-run onboarding completes end-to-end in both Arabic and English without looping indefinitely.
- Prompt echo is ignored in setup and clarification paths.
- Retry behavior is bounded, localized, and covered by regression tests.

## Phase 14: Audio Front-End, Hybrid STT, and Command Canonicalization

### Goal
Substantially improve recognition quality on Raspberry Pi 4 Model B using a free, local-first speech pipeline that captures complete utterances, reduces clipping, and maps noisy transcripts back into the supported command space with much higher reliability.

### Why This Phase Exists
After dialog-state stability, the main bottleneck becomes the raw speech path itself. Current quality gaps are not only parser issues:
- utterances can start or end clipped
- weak or noisy speech can produce partial words
- bilingual input can drift between Arabic and English variants
- unrestricted recognition often returns text outside the application's valid command set
- onboarding and closed-choice flows still pay the cost of broad free-text decoding even when the answer space is tiny

This phase upgrades the recognition stack without requiring paid APIs and without exceeding realistic Raspberry Pi 4 resource limits.

### Scope
- Improve the audio path before transcription
- Improve how transcripts are produced and scored
- Improve how noisy transcripts are normalized before command parsing
- Keep the architecture provider-based and compatible with the current runtime

### Non-Goals
- Do not introduce heavy cloud-only STT as the default path
- Do not replace the command layer with a large ML intent model
- Do not redesign the entire runtime loop in this phase

### Workstreams

#### Workstream A: Audio Capture and Pre-Processing
1. Introduce a dedicated audio pre-processing layer before STT that performs:
   - mono normalization
   - sample-rate normalization
   - DC offset removal
   - high-pass filtering for low-frequency rumble
   - lightweight loudness normalization / AGC
   - optional low-cost noise suppression only when it stays within Pi CPU budget
2. Separate microphone capture policy from transcription policy so the project can tune audio handling without constantly changing the parser/runtime.
3. Add configuration profiles for:
   - standby wake capture
   - onboarding capture
   - command capture
   - confirmation / yes-no capture

#### Workstream B: Endpointing and Full-Utterance Capture
1. Add configurable VAD and endpointing tuned for wearable speech:
   - early speech-start capture
   - adaptive trailing silence
   - anti-clipping pre-roll and post-roll padding
   - protection against cutting the final syllable or last word
2. Return explicit capture metadata from STT, including:
   - speech_started_at
   - speech_ended_at
   - utterance_duration_ms
   - clipping_start_suspected
   - clipping_end_suspected
3. Add recovery behavior for likely-clipped utterances:
   - one bounded re-listen when clipping is suspected
   - a shorter reprompt rather than a full repeated prompt

#### Workstream C: Hybrid STT on Raspberry Pi 4
1. Upgrade the STT contract so recognition returns structured data:
   - primary transcript
   - alternative transcripts
   - confidence when available
   - detected language or language candidates
   - provider/source metadata
   - endpoint quality hints
2. Build a local-first hybrid recognition flow:
   - a fast first-pass offline decode
   - a bounded second-pass rescue path when the first pass is weak, clipped, or inconsistent
   - predictable fallback behavior when stronger recognition is unavailable
3. Ensure the hybrid path can be disabled or simplified by configuration on lower-power deployments.

#### Workstream D: Canonicalization and Dictionary Bias
1. Add a command canonicalization layer before parsing that:
   - normalizes Arabic text variants
   - normalizes English casing, punctuation, and spacing
   - maps common STT substitutions into canonical command tokens
   - collapses known bilingual aliases into parser-friendly command phrases
2. Add dictionary filtering for closed or semi-closed contexts:
   - onboarding language answers
   - onboarding voice answers
   - onboarding speed answers
   - yes/no/cancel
   - wake-follow-up command vocabulary
3. Bias command-mode recognition toward the supported command inventory rather than arbitrary free text.
4. Preserve an escape hatch for future open-domain capabilities by keeping dictionary bias mode-specific, not global.

#### Workstream E: Confidence Policy and Benchmarks
1. Move from broad global thresholds toward per-intent or per-mode confidence policy.
2. Introduce confusion-pair handling for commonly misheard options such as:
   - `male` vs `female`
   - `Arabic` vs `English`
   - wake aliases and close phonetic variants
3. Add benchmark fixtures and regression scenarios for:
   - noisy room audio
   - clipped starts / ends
   - bilingual wake + command journeys
   - alternative transcript rescue
   - dictionary-filtered onboarding answers
4. Document the recommended free offline stack for Raspberry Pi 4, including expected CPU, RAM, and latency tradeoffs.

### Expected Files
- `core/stt.py`
- `core/speech/legacy_stt.py`
- `core/speech/provider_resolver.py`
- `core/assistant_runtime.py`
- `core/parser.py`
- a new audio pre-processing module under `core/audio/` or `core/speech/`
- a new transcript canonicalization module under `core/`
- `settings/settings_manager.py`
- STT quality, endpointing, and canonicalization tests under `tests/`

### Phase Outputs
- More complete utterance capture with fewer cut-off words
- A stronger local-first recognition path that remains practical on Raspberry Pi 4
- Cleaner transcripts that stay much closer to the project's supported command vocabulary
- A reusable canonicalization layer that later phases can reuse for wake, onboarding, and command execution

### Acceptance Metrics
- Reduced clipped-utterance rate versus the current baseline
- Improved command-resolution success rate on noisy local samples
- Improved closed-vocabulary answer accuracy in onboarding
- No unacceptable regression in command latency on Raspberry Pi 4

### Exit Criteria
- Command-mode recognition captures full spoken commands more reliably than the current baseline.
- Closed-vocabulary flows show a measurable accuracy gain over unrestricted free-text recognition.
- The local recognition path remains within acceptable Raspberry Pi 4 latency and resource limits.
- Benchmark tests and fixtures record measurable gains in transcript quality and command resolution accuracy.

## Phase 15: Wake Reliability, Telemetry, and Raspberry Pi Performance Qualification

### Goal
Turn the upgraded speech stack into a measurable wearable-ready baseline by hardening wake behavior, aligning runtime recovery rules, and qualifying performance against Raspberry Pi 4 constraints.

### Why This Phase Exists
Better transcripts alone do not create a production-like wearable experience. The remaining gap is operational:
- wake must be fast without becoming noisy
- standby must stay low-cost
- the assistant must recover safely after recognition failures
- the team needs hard numbers, not anecdotes, to know whether quality improved
- Raspberry Pi 4 CPU, memory, and thermal limits must directly influence design decisions

This phase adds the operational discipline needed before real pilot-style usage.

### Scope
- Wake behavior and wake recovery
- Runtime speech telemetry
- Raspberry Pi 4 qualification and release gating
- Failure handling for repeated speech-loop faults

### Non-Goals
- Do not introduce a heavy always-listening mode in production
- Do not add a large external observability stack
- Do not turn telemetry hooks into a full logging platform in this phase

### Workstreams

#### Workstream A: Wake Hardening
1. Upgrade wake behavior into a two-stage wearable-ready strategy:
   - low-cost standby wake detection
   - optional short confirmation window before full command capture
   - clear separation between production wake behavior and dev-only fallbacks
2. Tune wake scoring and alias handling for multilingual use without over-expanding false accepts.
3. Add bounded recovery rules for wake misses and weak wake detections.
4. Keep the wake path compatible with future hardware-trigger integration.

#### Workstream B: Runtime Interaction Reliability
1. Align wake, listening, and playback policies so speech interaction feels natural:
   - fast wake-to-listen transition
   - safe barge-in where appropriate
   - no unnecessary waiting for full prompt playback before listening can resume
2. Ensure ordinary STT failures and wake misses return the assistant to a safe standby state instead of leaving the runtime stalled or shutting down unexpectedly.
3. Harden degraded-mode behavior so the user gets truthful status when a provider or mode is unavailable.

#### Workstream C: Telemetry and Measurement Hooks
1. Add structured telemetry hooks for:
   - wake accepted / rejected
   - probable false accept and false reject review inputs
   - command confidence distributions
   - clarification-loop rate
   - prompt-echo suppression counts
   - clipped-utterance retries
   - wake-to-listen latency
   - listen-to-result latency
   - result-to-speech-start latency
2. Keep telemetry implementation lightweight:
   - no mandatory external service
   - hook-based interfaces that can later feed logs, files, or a dashboard
3. Add a repeatable benchmark harness that can replay known field-like scenarios against the telemetry path.

#### Workstream D: Raspberry Pi 4 Qualification
1. Create a repeatable Pi qualification workflow that measures:
   - standby CPU usage
   - wake CPU spike
   - listening-state CPU and RAM
   - speaking-state CPU and RAM
   - startup latency
   - sustained thermal behavior
2. Define acceptable operating envelopes for:
   - standby resource budget
   - command latency
   - wake latency
   - repeated wake-cycle stability
3. Add release-gate checks so a candidate build can fail qualification before field testing.

### Expected Files
- `core/wake_word.py`
- `core/speech/legacy_wake.py`
- `core/speech/speakkit_wake.py`
- `core/assistant_runtime.py`
- `core/stt.py`
- `tts/tts_engine.py`
- `core/release_gates.py`
- `docs/release/startup.md`
- `docs/release/troubleshooting.md`
- new telemetry, benchmark, and Pi qualification tests under `tests/`

### Phase Outputs
- More reliable wake behavior suitable for wearable usage
- Repeatable quality and latency measurements instead of anecdotal evaluation
- A Raspberry Pi 4 qualification baseline that can be rerun before every pilot build
- Stronger failure recovery for normal speech-loop issues

### Acceptance Metrics
- Wake latency and command latency recorded through a repeatable path
- Stable standby CPU budget on Raspberry Pi 4
- No unexpected runtime exit after ordinary STT or wake failure scenarios
- Repeatable benchmark output for quiet, noisy, bilingual, and degraded/offline cases

### Exit Criteria
- The assistant no longer exits unexpectedly after ordinary STT or wake misses; it returns to a safe standby state.
- Wake latency, command latency, and clarification rate are exposed through repeatable telemetry hooks.
- Raspberry Pi 4 qualification runs produce stable CPU, memory, startup, and thermal measurements.
- Release validation includes speech-quality and wearable-readiness gates, not only functional correctness.

## Phase 16: Continuous Turn-Taking, Closed-Vocabulary Guardrails, and Pilot-Grade Voice UX

### Goal
Make the spoken experience feel natural, forgiving, and controlled by combining continuous turn-taking, context-specific vocabulary constraints, and strong dialog guardrails suitable for assistive wearable use.

### Why This Phase Exists
Even after STT and wake improve, user experience can still feel weak if:
- the user must wait for a narrow response window
- the assistant captures its own prompts or partial user speech
- closed-choice questions are handled like open dictation
- retries feel repetitive and confusing
- name capture and confirmation remain fragile

This phase turns a technically improved speech stack into a much smoother human experience.

### Scope
- Turn-taking and barge-in rules
- Context-specific vocabulary constraints
- Prompt echo rejection and out-of-domain answer rejection
- Onboarding and settings UX refinement

### Non-Goals
- Do not attempt true open-microphone conversation at all times
- Do not remove bounded safety windows for protected or high-risk flows
- Do not introduce a general-purpose LLM conversation layer as the primary control path

### Workstreams

#### Workstream A: Turn-Taking and Barge-In
1. Introduce a centralized turn-taking coordinator that decides when the system is:
   - speaking only
   - speaking but barge-in allowed
   - actively listening
   - listening with closed vocabulary
   - waiting for confirmation
   - recovering after no-input or clipped input
2. Replace rigid "wait until prompt finishes" behavior with policy-based barge-in:
   - allow early answer capture for onboarding and simple settings prompts
   - keep protected flows stricter when interruption would be unsafe
3. Ensure STT capture and TTS playback are coordinated so the runtime does not punish the user for speaking naturally.

#### Workstream B: Closed-Vocabulary Guardrails
1. Build a shared closed-vocabulary registry for contexts such as:
   - language choice
   - voice gender choice
   - speed choice
   - yes / no / cancel
   - wake confirmation
   - retry / repeat / help
2. Apply dictionary filtering and candidate validation after STT and before dialog resolution.
3. Reject out-of-domain answers explicitly instead of trying to over-interpret them as valid options.
4. Keep the registry bilingual and alias-friendly so Arabic, English, and common mixed variants are accepted intentionally.

#### Workstream C: Prompt Echo and User-Journey Quality
1. Add stronger prompt-echo detection using:
   - recent prompt text memory
   - token overlap checks
   - timing proximity to TTS playback
2. Improve retry behavior by mode:
   - first retry: short clarification
   - second retry: narrower wording with explicit options
   - final retry: safe fallback or graceful exit
3. Refine onboarding prompts to be shorter, more directive, and easier to answer quickly.
4. Improve name capture and name confirmation behavior:
   - capture a fuller utterance before accepting
   - normalize likely STT artifacts
   - use confirmation wording that is robust in Arabic and English

#### Workstream D: Pilot-Grade UX Validation
1. Add end-to-end spoken journey tests covering:
   - user answers before prompt completion
   - user answers during playback
   - repeated invalid answers
   - mixed Arabic/English onboarding
   - prompt echo suppression
   - name capture and confirmation recovery
2. Add a practical acceptance checklist for pilot UX:
   - user can answer naturally in allowed phases
   - the assistant does not repeatedly trap the user in loops
   - closed-choice questions resolve quickly
   - failures degrade into short, understandable recovery prompts
3. Document tuning guidance for future field iteration without code churn:
   - barge-in enablement by mode
   - closed-vocabulary sets
   - retry limits
   - prompt length and style guidance

### Expected Files
- `core/assistant_runtime.py`
- `core/dialog_policy.py`
- `core/resolver.py`
- `core/stt.py`
- `tts/tts_engine.py`
- a new turn-taking or dialog coordination module under `core/`
- a new closed-vocabulary registry module under `core/`
- `settings/settings_manager.py`
- onboarding, barge-in, and UX regression tests under `tests/`
- `docs/plan.md` or related release docs for pilot behavior guidance

### Phase Outputs
- A smoother voice UX that feels less rigid and less frustrating
- Closed-vocabulary flows that are much harder to derail
- Safer and clearer retry behavior across onboarding and settings dialogs
- A stronger pilot-readiness definition focused on real user interaction quality

### Acceptance Metrics
- Reduced clarification-loop rate during onboarding and settings flows
- Reduced prompt-echo false captures
- Improved first-try resolution for language, voice, speed, and yes/no prompts
- Measurably better completion rate for first-run setup

### Exit Criteria
- Users can answer naturally during allowed barge-in windows without needing to wait for every prompt to finish.
- Closed-vocabulary prompts resolve reliably and reject out-of-domain answers safely.
- Prompt echo no longer drives repeated onboarding loops.
- End-to-end onboarding and settings journeys achieve a clearly improved completion rate in regression scenarios.

## Phase 17: Google Cloud STT Foundation and Strict Fallback Contracts

### Goal
Introduce a production-grade Google Cloud Speech-to-Text foundation while preserving the existing provider-aware runtime architecture and preparing Vosk to become a strict grammar fallback instead of the main free-speech path.

### Why This Phase Exists
The current STT stack is local-first and routes practical recognition through Vosk, PocketSphinx, and then `speech_recognition.recognize_google()` as a weak fallback. That order is not strong enough for Arabic commands, noisy wearable use, or safety-critical decisions. Before changing command or wake behavior, the project needs a clean cloud STT integration point, phrase-hint infrastructure, feature flags, and strict local fallback contracts.

This phase is intentionally foundational. It should not rewrite the runtime loop, parser, dispatcher, or provider model.

### Scope
- Add official Google Cloud STT integration behind the existing `SpeechToTextService` architecture.
- Add command and wake phrase-hint generation.
- Add strict Vosk grammar contracts by usage mode.
- Remove PocketSphinx from the default recognition decision path.
- Keep rollback possible through configuration and environment flags.

### Non-Goals
- Do not replace `AssistantRuntime`.
- Do not replace the existing `legacy` and `speakkit` provider IDs.
- Do not remove Vosk.
- Do not introduce an LLM or unrelated speech framework.
- Do not make cloud STT mandatory when credentials or network are unavailable.

### Workstreams

#### Workstream A: Google Cloud STT Client Boundary
1. Add a dedicated Google Cloud STT module that owns:
   - Google client creation
   - credential availability checks
   - synchronous short-utterance recognition
   - timeout handling
   - retry policy for transient errors
   - confidence extraction
   - alternative transcript extraction
   - detected or selected language metadata
2. Use the official Google Cloud Speech-to-Text client instead of `speech_recognition.recognize_google()` for production recognition.
3. Keep the module optional at import time so local development and CI do not fail without cloud credentials.
4. Return structured candidate data, not plain strings only.
5. Classify failures into stable reason codes:
   - `cloud_credentials_missing`
   - `cloud_network_timeout`
   - `cloud_auth_error`
   - `cloud_quota_error`
   - `cloud_service_unavailable`
   - `cloud_empty_result`
   - `cloud_unknown_failure`

#### Workstream B: Feature Flags and Compatibility Controls
1. Add configuration and environment controls for:
   - `EGB_STT_CLOUD_PRIMARY_ENABLED`
   - `EGB_STT_STRICT_VOSK_FALLBACK_ENABLED`
   - `EGB_STT_ENABLE_SPHINX_COMPAT`
   - `EGB_STT_CLOUD_TIMEOUT_S`
   - `EGB_STT_CLOUD_MAX_ALTERNATIVES`
2. Default the new code path conservatively during development:
   - cloud primary can be enabled explicitly
   - strict Vosk fallback can be enabled independently
   - Sphinx compatibility remains off by default
3. Preserve current public methods in `VoiceListener`:
   - `listen_any`
   - `listen_command`
   - `listen_command_result`
   - `listen_command_window`
4. Keep `CommandRecognitionResult` as the runtime-facing result contract.

#### Workstream C: Phrase Hints Infrastructure
1. Add a shared phrase-hints module that builds hints from:
   - `core.parser.COMMAND_CATALOG`
   - closed-vocabulary contexts
   - canonical wake aliases
   - curated assistive wearable phrases
   - safety-critical commands
2. Generate mode-specific phrase sets:
   - wake phrase hints
   - command phrase hints
   - confirmation phrase hints
   - onboarding phrase hints
3. Include English, Arabic, bilingual, phonetic, and common STT-mistake variants.
4. Keep hints deterministic and testable so Spec Kit can validate exact expected outputs.

#### Workstream D: Strict Vosk Fallback Contracts
1. Convert Vosk fallback usage into grammar-constrained decoding for:
   - `standby_wake`
   - `command`
   - `confirmation`
   - closed-choice onboarding turns
2. Prevent free-form Vosk fallback from producing arbitrary command text in command mode.
3. Add explicit fallback modes:
   - `wake_grammar`
   - `command_inventory`
   - `closed_choice`
4. Ensure Vosk fallback returns no usable transcript when it cannot match the strict grammar.

#### Workstream E: PocketSphinx Deactivation From Accuracy Path
1. Remove PocketSphinx from the default `_recognize_audio_candidates()` ranking path.
2. Keep existing Sphinx compatibility code only behind `EGB_STT_ENABLE_SPHINX_COMPAT=1` if needed for debugging.
3. Stop treating Sphinx output as a candidate for production command or wake decisions.
4. Document that PocketSphinx is no longer part of the accuracy path.

### Expected Files
- `requirements.txt`
- `core/stt.py`
- `core/speech/interfaces.py`
- `core/speech/legacy_stt.py`
- `core/speech/provider_registry.py`
- new `core/speech/google_cloud_stt.py`
- new `core/speech/phrase_hints.py`
- `docs/STTInfo.md`
- Google STT foundation tests under `tests/unit/`

### Phase Outputs
- A production-grade Google Cloud STT integration point.
- A deterministic phrase-hint generation layer.
- A strict grammar fallback contract for Vosk.
- PocketSphinx removed from normal recognition decisions.
- Runtime architecture remains unchanged from the outside.

### Acceptance Metrics
- Google Cloud candidate extraction is covered by unit tests with fake client responses.
- Missing credentials do not crash startup or tests.
- Strict Vosk grammar payloads are deterministic for wake, command, and confirmation contexts.
- Sphinx is not called unless explicitly enabled by compatibility flag.

### Exit Criteria
- `VoiceListener.listen_command_result()` can run with cloud-primary recognition when configured.
- If cloud recognition fails, the fallback path is strict Vosk grammar, not Sphinx.
- Existing runtime tests still pass without requiring Google credentials.
- `requirements.txt` and docs clearly describe the Google Cloud dependency and credential expectation.

## Phase 18: Cloud-Primary Command Recognition and Safety-Aware Fallback

### Goal
Make command recognition use Google Cloud STT as the primary recognizer with command phrase hints, while preserving the existing parser, post-processing, confidence policy, rescue recognition, dispatcher, and resolver flow.

### Why This Phase Exists
Commands are the highest-value recognition target in the assistant. The current local-first command path can miss Arabic commands, produce partial phrases in noisy environments, and let weak local candidates compete with better cloud candidates. This phase changes the command recognition order without changing the runtime command contract.

### Scope
- Command-mode recognition only.
- Cloud-first command recognition with phrase hints.
- Strict Vosk command grammar fallback.
- Improved confidence metadata passed into the existing runtime policy.
- Better failure handling for low confidence, timeout, and language mismatch.

### Non-Goals
- Do not redesign `core.parser`.
- Do not remove `process_command_transcript`.
- Do not bypass `AssistantRuntime._evaluate_confidence_decision`.
- Do not execute commands directly from STT output.

### Workstreams

#### Workstream A: Command Engine Ordering
1. Change command recognition order in `core/stt.py` from:
   - Vosk
   - PocketSphinx
   - Google fallback
2. To:
   - Google Cloud STT primary with command phrase hints
   - strict Vosk command grammar fallback
   - retry / confirmation through existing runtime policy
3. Make the command path source explicit in metadata:
   - `cloud_primary`
   - `strict_vosk_fallback`
   - `rescue_strict_vosk`
   - `cloud_unavailable`
4. Keep `recognition_path` values compatible with current runtime:
   - `local_first`
   - `rescue`
   - `fallback`

#### Workstream B: Command Phrase Hints and Model Adaptation
1. Use parser catalog keywords as the baseline command hint inventory.
2. Add curated assistive wearable phrases:
   - `stop system`
   - `detect obstacle`
   - `recognize face`
   - `recognize emotion`
   - `money detection`
   - `read text`
   - `help me`
   - `emergency mode`
   - `navigation mode`
   - `call help`
3. Add Arabic command hints:
   - Arabic stop-system variants
   - obstacle detection variants
   - face recognition variants
   - text reading variants
   - emergency-mode variants
   - help variants
   - money detection variants
   - navigation variants
4. Add spoken and phonetic variants for mixed speech:
   - `stop السيستم`
   - `ستوب سيستم`
   - `recognize face`
   - `ريكوجنايز فيس`
   - `obstacle`
   - `اوبستاكل`
   - `read text`
   - `اقرا النص`
5. Keep boost values mode-specific and measurable.

#### Workstream C: Command Fallback Decision Rules
1. Run strict Vosk fallback when:
   - cloud returns no transcript
   - cloud times out
   - cloud confidence is below command threshold
   - cloud language conflicts with the command context
   - cloud result is rejected by post-processing/parser
2. Do not run broad local fallback for arbitrary dictation.
3. Keep fallback bounded by the same runtime command timeout.
4. Preserve existing rescue recognition loop in `AssistantRuntime`.

#### Workstream D: Confidence and Alternatives Handling
1. Use cloud confidence as the primary confidence source when available.
2. Preserve alternative transcripts and feed them into runtime reranking.
3. Penalize candidates with:
   - language mismatch
   - no command-like tokens
   - endpoint clipping hints
   - out-of-vocabulary command shape
4. Promote strict grammar fallback candidates only when they parse into a known command or closed vocabulary option.

#### Workstream E: Command Safety Rules
1. Preserve protected command behavior:
   - high-risk commands require explicit confirmation
   - ambiguous protected commands refuse or retry instead of executing
2. Ensure low-risk commands can still execute directly when confidence is high and parser acceptance is clean.
3. Ensure medium-risk commands use confirmation when cloud confidence is borderline or alternatives conflict.
4. Add tests for protected commands:
   - `stop system`
   - emergency-related commands
   - reset/settings-sensitive commands

### Expected Files
- `core/stt.py`
- `core/assistant_runtime.py`
- `core/command_models.py` if metadata needs extension
- `core/command_post_processing.py`
- `core/parser.py`
- `core/speech/phrase_hints.py`
- command recognition tests under `tests/unit/` and `tests/integration/`

### Phase Outputs
- Command recognition becomes cloud-primary.
- Vosk becomes strict command fallback.
- Parser and confidence policy continue to own execution safety.
- Command alternatives and confidence become more useful and measurable.

### Acceptance Metrics
- Improved command-resolution success on Arabic and bilingual command fixtures.
- Reduced fallback-to-retry rate for common commands.
- No protected command executes without required confirmation.
- Cloud failures produce strict fallback, not runtime crashes.

### Exit Criteria
- Command-mode recognition never uses PocketSphinx in the default path.
- Cloud-primary command recognition feeds `CommandRecognitionResult` without breaking runtime consumers.
- Strict Vosk fallback is used for command rescue and returns only grammar-constrained candidates.
- Regression tests cover cloud success, cloud low confidence, cloud timeout, fallback success, fallback failure, and protected-command confirmation.

### Implementation Notes (2026-04-24)
- `core/command_models.py` now includes Phase 18 source labels `rescue_strict_vosk` and `cloud_unavailable`, plus a field-safe `build_command_fallback_decision(...)` helper.
- `core/stt.py` now emits no-usable-command metadata for cloud-unavailable and strict-no-match paths, preserves selected/detected language on fallback outcomes, and keeps strict fallback bounded to capped command grammar.
- `core/assistant_runtime.py` now routes parser rejection and language-family mismatch through recovery reasons (`parser_rejected_recovery`, `language_mismatch_recovery`) instead of raw execution fallback.
- `core/command_post_processing.py` strips wake prefixes in command mode with traceable substitution id `wake.prefix_removed`.
- `core/speech/phrase_hints.py` now uses deterministic command priority ordering and documented caps (cloud: 72, strict grammar: 220).
- Diagnostics coverage now includes command fallback trigger/status/reason assertions without raw utterance or credential persistence by default.

## Phase 19: Cloud-Primary Wake Recognition and Standby Fallback Reliability

### Goal
Upgrade wake detection so STT-based wake uses Google Cloud STT primary with wake phrase hints, then strict Vosk wake grammar fallback, while keeping the existing wake service and runtime standby flow intact.

### Why This Phase Exists
Wake reliability is critical for wearable usability. Current wake flow can depend on weak STT behavior and broad recognition paths. This phase improves wake accuracy without replacing the wake state machine, local keyword support, or hardware-trigger path.

### Scope
- STT-based wake and wake fallback only.
- Cloud primary wake recognition.
- Strict Vosk wake grammar fallback.
- Canonical wake matcher remains the authority for acceptance.
- Standby returns safely when both cloud and local fallback fail.

### Non-Goals
- Do not remove hardware-trigger wake.
- Do not remove local keyword wake.
- Do not make always-on cloud streaming mandatory.
- Do not accept wake directly from raw STT text without canonical wake matching.

### Workstreams

#### Workstream A: Wake Recognition Ordering
1. Update wake listening in `core/speech/legacy_wake.py` to request wake-specific STT behavior.
2. Use `usage_mode="standby_wake"` and `capture_profile_id="standby_wake.default"`.
3. For wake STT, run:
   - Google Cloud STT wake recognition with wake phrase hints
   - strict Vosk wake grammar fallback
   - no PocketSphinx
4. Return to standby when both recognition paths fail or return non-canonical wake text.

#### Workstream B: Wake Phrase Hints
1. Build wake hints from canonical wake aliases and known variants.
2. Include bilingual wake patterns:
   - `hi egb`
   - `hey egb`
   - Arabic equivalents
   - common STT approximations
3. Keep the hint set small enough to reduce false accepts.
4. Keep canonical wake matcher as the final gate.

#### Workstream C: Wake Fallback Grammar
1. Add Vosk wake grammar that only includes approved wake aliases and safe variants.
2. Reject non-wake fallback transcripts.
3. Emit a wake miss event when both cloud and strict fallback fail.
4. Emit source metadata:
   - `wake_cloud_primary`
   - `wake_strict_vosk_fallback`
   - `wake_rejected_noncanonical`

#### Workstream D: Runtime Wake Compatibility
1. Keep `AssistantRuntime._await_standby_wake_attempt()` behavior compatible.
2. Preserve `is_canonical_wake_phrase()` and `detect_wake()` as wake acceptance gates.
3. Keep `WAKE_MODE_KEYWORD_LOW_POWER`, `WAKE_MODE_HARDWARE_TRIGGER`, and `WAKE_MODE_STT_BASED`.
4. Ensure network-down behavior can still preserve local strict wake fallback where allowed.

#### Workstream E: Wake Safety and False Trigger Control
1. Track false wake review markers through telemetry.
2. Reject broad or unrelated cloud transcripts even if confidence is high.
3. Refuse wake acceptance if the transcript contains command text but no wake phrase.
4. Add tests for wake confusion cases:
   - short noise
   - similar-sounding non-wake words
   - wake plus command in one utterance
   - Arabic wake variants
   - cloud timeout then Vosk fallback success

### Expected Files
- `core/speech/legacy_wake.py`
- `core/wake_word.py`
- `core/stt.py`
- `core/speech/phrase_hints.py`
- `core/speech/provider_resolver.py`
- `core/assistant_runtime.py`
- wake recognition tests under `tests/unit/` and `tests/integration/`

### Phase Outputs
- Wake STT becomes cloud-primary.
- Wake fallback becomes strict Vosk grammar.
- Wake acceptance remains canonical and safety-gated.
- Failed wake attempts return to standby predictably.

### Acceptance Metrics
- Reduced wake false rejects in bilingual wake fixtures.
- No increase in false accepts from non-wake phrases.
- Cloud timeout wake scenarios recover through strict local fallback.
- Standby remains stable after repeated wake misses.

### Exit Criteria
- STT-based wake uses Google Cloud first when configured and available.
- Vosk fallback for wake is grammar-only.
- Wake misses do not stall the runtime or exit unexpectedly.
- Wake telemetry can distinguish accepted, rejected, cloud failed, and fallback used cases.

## Phase 20: Arabic, Bilingual Canonicalization, and Safety Confidence Hardening

### Goal
Strengthen Arabic and bilingual command readiness after cloud-primary STT is introduced, so transcripts from both Google Cloud and strict Vosk fallback map safely into parser-ready command text.

### Why This Phase Exists
Cloud STT improves raw recognition, but production accuracy still depends on normalization and command canonicalization. Arabic commands, Egyptian variants, English phonetics inside Arabic speech, and mixed utterances need explicit handling before parser and confidence decisions can be trusted.

### Scope
- Arabic and bilingual text normalization.
- Command post-processing.
- Parser keyword expansion for supported commands.
- Confidence-policy tuning using recognition metadata.
- Confirmation policy hardening for safety-critical commands.

### Non-Goals
- Do not introduce an open-domain language model.
- Do not bypass closed-vocabulary guardrails.
- Do not lower protected-command safety requirements to improve convenience.

### Workstreams

#### Workstream A: Arabic Normalization Hardening
1. Strengthen Arabic normalization in `core/command_post_processing.py`:
   - hamza normalization
   - alef variants normalization
   - alef maqsoora normalization
   - ta marbuta normalization
   - tatweel removal
   - punctuation cleanup
   - whitespace normalization
2. Add mojibake protection checks that reject corrupted Arabic-like text safely.
3. Keep normalized output parser-ready while preserving enough metadata for diagnostics.

#### Workstream B: Spoken Variants and Phonetic Confusions
1. Add correction rules for common bilingual STT outputs:
   - `ستوب سيستم`
   - `وقف النظام`
   - `اوبستاكل`
   - `ريكوجنايز فيس`
   - `اقرا النص`
   - `كشف النقود`
   - `وضع الطوارئ`
2. Add useful Arabizi and mixed forms where they match supported commands.
3. Expand confusion-pair handling for:
   - obstacle / optical / obsticle
   - read text / red text
   - face / phase
   - money / many
   - male / female
   - Arabic / English

#### Workstream C: Parser Inventory Expansion
1. Expand `COMMAND_KEYWORDS` with high-value Arabic and bilingual variants.
2. Keep additions tied to existing intent IDs.
3. Avoid adding vague phrases that could increase false positives.
4. Add tie-break rules for safety-critical commands when scores are close.
5. Use recognition metadata to detect language mismatch and ambiguity.

#### Workstream D: Confirmation Policy Tuning
1. Preserve low-risk direct execution when recognition is high confidence and parser acceptance is clean.
2. Move medium-risk commands to confirmation when:
   - confidence is medium
   - alternatives conflict
   - language mismatch exists
   - post-processing applied high-impact substitutions
3. Keep high-risk commands under strict confirmation.
4. Require explicit affirmative confirmation for:
   - `stop_system`
   - emergency mode
   - reset/settings-sensitive actions
   - critical wearable actions

#### Workstream E: Regression and Safety Validation
1. Add tests for Arabic commands, bilingual commands, and phonetic command variants.
2. Add negative tests for near-command phrases that should not execute.
3. Add confirmation tests for protected commands after cloud-primary recognition.
4. Add language-mismatch tests where command execution should retry or confirm.

### Expected Files
- `core/command_post_processing.py`
- `core/parser.py`
- `core/dialog_policy.py`
- `core/assistant_runtime.py`
- `core/closed_vocabulary.py`
- `core/text_integrity.py`
- parser and post-processing tests under `tests/unit/`
- command safety integration tests under `tests/integration/`

### Phase Outputs
- Stronger Arabic and mixed-language transcript normalization.
- Safer parser readiness for cloud and Vosk fallback transcripts.
- Fewer false rejects on supported Arabic commands.
- No safety regression for protected commands.

### Acceptance Metrics
- Increased parser acceptance for supported Arabic command fixtures.
- Reduced ambiguous-parser outcomes for common bilingual commands.
- Zero protected-command execution without explicit confirmation.
- Corrupted Arabic text is rejected safely rather than misinterpreted.

### Exit Criteria
- Arabic and bilingual command fixtures resolve to the intended existing intent IDs.
- Near-miss and unsafe phrases do not execute protected commands.
- Confirmation policy remains strict for high-risk commands.
- Post-processing outputs include enough metadata to explain major normalization decisions.

### Implementation Notes (2026-04-26)
- Command normalization and safety decisions remain anchored in
  `core/command_post_processing.py`, `core/parser.py`, and
  `core/assistant_runtime.py`; no separate command system was introduced.
- Regression validation passed for Arabic/bilingual mapping, protected-command
  confirmation safety, corrupted-text rejection, and field-safe diagnostics.
- Field-safe command metadata now remains visible end-to-end for major
  normalization and ambiguity decisions without persisting raw utterance
  content by default.

## Phase 21: STT Observability, Rollout Gates, and PocketSphinx Decommission

### Goal
Make the new cloud-primary STT architecture measurable, safely deployable on Raspberry Pi 4, and ready for field iteration by adding observability, rollout controls, and final PocketSphinx decommissioning.

### Why This Phase Exists
Accuracy improvements must be measured in production-like conditions. Without telemetry and rollout gates, the team cannot know whether cloud-primary STT improved wake reliability, command accuracy, Arabic handling, fallback behavior, latency, and safety outcomes.

### Scope
- STT telemetry and diagnostic events.
- Raspberry Pi 4 validation for latency and resource cost.
- Safe rollout strategy.
- PocketSphinx decommission from active dependencies after compatibility window.
- Documentation for field operation and failure analysis.

### Non-Goals
- Do not require an external telemetry service.
- Do not store raw user audio.
- Do not log raw user utterances in field-safe diagnostics.
- Do not remove rollback flags until field validation is complete.

### Workstreams

#### Workstream A: STT Telemetry Events
1. Add lightweight telemetry for:
   - cloud recognition attempts
   - cloud failure categories
   - strict Vosk fallback frequency
   - confidence distribution by source
   - rescue recognition frequency
   - retry rate
   - clipping frequency
   - timeout frequency
   - Arabic recognition failure markers
   - language mismatch rate
2. Reuse existing `core/release_metrics.py` and `core/runtime_diagnostics.py` patterns.
3. Keep telemetry field-safe:
   - no raw audio
   - no raw utterance content by default
   - source, mode, status, confidence bucket, and reason codes only

#### Workstream B: Release Gates and Qualification
1. Add release checks for:
   - cloud-primary configuration validity
   - fallback availability
   - no default PocketSphinx path
   - wake fallback correctness
   - protected-command confirmation
   - bilingual command regression
2. Add Pi 4 qualification metrics:
   - wake latency
   - command recognition latency
   - fallback latency
   - CPU usage during recognition windows
   - memory usage during cloud and Vosk paths
3. Fail release validation when a safety-critical gate regresses.

#### Workstream C: Failure Scenario Handling
1. Validate behavior for:
   - no network
   - missing credentials
   - expired credentials
   - cloud quota/rate errors
   - cloud timeout
   - Vosk model missing
   - microphone timeout
   - repeated clipped utterances
   - language mismatch
2. Ensure each failure returns a bounded runtime result:
   - fallback
   - retry
   - safe refusal
   - standby
3. Ensure no scenario causes an unhandled runtime crash.

#### Workstream D: Safe Rollout Controls
1. Support staged rollout modes:
   - `shadow`: call cloud and log metadata without changing behavior
   - `wake_only`: cloud-primary wake, old command behavior
   - `commands_low_risk`: cloud-primary for low-risk commands
   - `full_cloud_primary`: wake and commands cloud-primary with strict local fallback
2. Keep rollback possible through settings or environment variables.
3. Document the recommended pilot rollout order.

#### Workstream E: PocketSphinx Decommission
1. Remove PocketSphinx from the normal runtime dependency story after validation.
2. Keep a documented compatibility note if the import path remains for old environments.
3. Remove Sphinx-related tests from the required accuracy baseline.
4. Update STT docs to reflect:
   - Google Cloud primary
   - strict Vosk fallback
   - PocketSphinx no longer in main path

### Expected Files
- `core/stt.py`
- `core/assistant_runtime.py`
- `core/release_metrics.py`
- `core/runtime_diagnostics.py`
- `core/release_gates.py`
- `scripts/release_validate.py`
- `requirements.txt`
- `docs/STTInfo.md`
- `docs/release/troubleshooting.md`
- `docs/release/audio_frontend_qualification.md`
- release, telemetry, and failure-path tests under `tests/`

### Phase Outputs
- Field-safe visibility into STT behavior and failures.
- Repeatable Pi 4 qualification for cloud-primary STT.
- Safe rollout modes and rollback controls.
- PocketSphinx removed from active recognition and release expectations.

### Acceptance Metrics
- Fallback frequency, cloud failure frequency, confidence buckets, retry rate, and timeout rate are measurable.
- Release validation catches missing cloud configuration and missing Vosk fallback.
- Pi 4 latency remains within wearable interaction targets.
- No raw audio or raw utterance content is stored by default.

### Exit Criteria
- Cloud-primary STT can be deployed with measurable behavior and safe fallback.
- Release validation proves protected-command safety and fallback readiness.
- PocketSphinx is no longer part of the required production accuracy path.
- Field diagnostics explain whether recognition failed because of cloud, fallback, audio capture, language mismatch, or confidence policy.

## Recommended Execution Order
1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4
6. Phase 5
7. Phase 6
8. Phase 7
9. Phase 8
10. Phase 9
11. Phase 10
12. Phase 11
13. Phase 12
14. Phase 13
15. Phase 14
16. Phase 15
17. Phase 16
18. Phase 17
19. Phase 18
20. Phase 19
21. Phase 20
22. Phase 21

## First Practical Backlog After Plan Approval
1. Fix the `stop` command bug.
2. Add initial parser and resolver tests.
3. Extract a standalone runtime from `assistant_worker`.
4. Define speech interfaces.
5. Build an initial SpeakKit adapter.

## Definition of Execution Success
This implementation plan is successful if the project reaches a cleaner version of the same core architecture, with an independent runtime, a replaceable speech pipeline, and capabilities that gradually move from mock implementations to real integrations without breaking momentum or forcing a restart from zero.

## Phase 19 Rollout Notes (Cloud-Primary Wake)

### Operator Controls
- Keep cloud-primary wake opt-in with `EGB_STT_CLOUD_PRIMARY_ENABLED=1`.
- Keep strict local wake fallback enabled for resilience with `EGB_STT_STRICT_VOSK_FALLBACK_ENABLED=1`.
- Keep PocketSphinx compatibility disabled in rollout baselines with `EGB_STT_ENABLE_SPHINX_COMPAT=0`.
- Tune wake timeout bounds with `EGB_STT_CLOUD_TIMEOUT_S` and keep bounded alternatives via `EGB_STT_CLOUD_MAX_ALTERNATIVES`.

### Runtime Outcome Expectations
- `wake_accepted` with `source_classification=cloud_primary` for canonical cloud wake.
- `wake_accepted` with `source_classification=wake_strict_vosk_fallback` when fallback succeeds.
- `wake_rejected` with `source_classification=noncanonical_rejected` for non-canonical or command-only wake-like speech.
- `wake_missed` when cloud + strict fallback do not return a canonical wake.

### Field Safety Guardrails
- Keep `payload.field_safe=true` and `payload.raw_user_content_present=false` for wake outcomes.
- Do not persist raw wake utterances or cloud credential material in `settings/user_profile.json`.
- Keep release evidence metadata-only under `artifacts/<run-id>/`.
