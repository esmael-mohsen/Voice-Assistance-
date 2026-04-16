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
3. Measure latency and resource usage.
4. Write troubleshooting docs and prepare a startup script.
5. Pin dependencies to explicit versions.
6. Create a release checklist.

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

## Recommended Execution Order
1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4
6. Phase 5
7. Phase 6

## First Practical Backlog After Plan Approval
1. Fix the `stop` command bug.
2. Add initial parser and resolver tests.
3. Extract a standalone runtime from `assistant_worker`.
4. Define speech interfaces.
5. Build an initial SpeakKit adapter.

## Definition of Execution Success
This implementation plan is successful if the project reaches a cleaner version of the same core architecture, with an independent runtime, a replaceable speech pipeline, and capabilities that gradually move from mock implementations to real integrations without breaking momentum or forcing a restart from zero.
