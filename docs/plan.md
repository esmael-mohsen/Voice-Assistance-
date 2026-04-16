# Project Development Plan

## Goal
Evolve the current project from a voice assistant prototype into a usable assistant for smart glasses designed for blind users, while preserving the current structure and improving it incrementally instead of deleting everything and starting over.

## Working Principle
- No full rewrite.
- Keep the current layers `main.py`, `core/`, `settings/`, `tts/`, and `ui/`, then reorganize responsibilities inside them step by step.
- The GUI remains a debug and demo tool, not the primary runtime path for the final glasses version.
- Any SpeakKit integration should be introduced through an adapter or service layer instead of tightly coupling it to the rest of the codebase.

## Current State
- `main.py` runs the application in GUI or console mode.
- `ui/assistant_worker.py` contains the actual runtime loop: wake phrase, then listen, then dispatch.
- `core/stt.py` depends on `SpeechRecognition` and `recognize_google`.
- `tts/tts_engine.py` depends on `edge-tts` and then `playsound`.
- `core/parser.py` contains a large command dictionary driven by fuzzy matching.
- `core/resolver.py` maps command keys to controller functions.
- `controllers/mock_controllers.py` is still mock-based and not a real integration layer.
- `settings/settings_manager.py` and `settings/profile_store.py` are a strong base for storing preferences and centralizing runtime behavior.

## Problems the Plan Must Build Around
- The current cloud-based STT and TTS setup is not ideal for a wearable assistant that needs speed and reliability.
- Runtime behavior is currently mixed with UI logic.
- The current controllers are still mock implementations, so the project is not yet product-ready.
- The parser is large but not well protected by tests.
- There are no clear quality gates yet: tests, logging strategy, profiling, or release checklist.

## Target Vision
- A fast, stable, clear, and safe voice assistant for a blind user.
- A wake flow with low power usage that can still work under weak or unreliable network conditions.
- A replaceable speech pipeline: SpeakKit, a local fallback, or a remote provider.
- System and vision commands that return structured results instead of plain strings only.
- Clear separation between:
  - Voice runtime
  - Command understanding
  - Capability controllers
  - Device and hardware integrations
  - Debug UI

## Core Goals
- Reduce internet dependency as much as possible.
- Reduce latency in wake detection, STT, TTS, and command execution.
- Prevent dangerous or confusing commands from breaking the glasses experience.
- Make the project scalable without further bloating `assistant_worker.py` and `parser.py`.
- Keep all changes incremental and testable after every phase.

## Non-Goals for Now
- Deleting the current project and rebuilding from scratch.
- Turning the project into a general-purpose chatbot assistant.
- Delivering every real vision capability in the first sprint.
- Spending time on major UI polish before the runtime is stable.

## Proposed Development Path

## Phase 0: Stabilize the Foundation
- Fix the obvious runtime bugs in the current implementation.
- Add docs, smoke tests, and parser and resolver tests.
- Unify the behavior between GUI and console mode.
- Establish baseline metrics: startup time, command latency, and failure rate.

## Phase 1: Separate Runtime from UI
- Treat `ui/assistant_worker.py` as a temporary host for runtime logic.
- Move voice runtime behavior into a dedicated service or runtime layer.
- Keep `gui_app.py` as a debug UI that consumes runtime events.
- Prepare a headless mode that becomes the closest path to the glasses runtime.

## Phase 2: Introduce Speech Pipeline Abstractions
- Create clear interfaces for wake detection, STT, and TTS.
- Integrate SpeakKit through adapters instead of rewriting the whole project around it.
- Keep the current implementation as a temporary fallback.
- Allow provider switching through settings or configuration.

## Phase 3: Replace Mock Controllers with Real Capabilities
- Each capability should have a clear service, runtime state, and unified response format.
- Obstacle detection, OCR, money detection, face recognition, and emotion recognition should move out of `mock_controllers.py` into dedicated modules.
- Each capability should return:
  - `spoken_text`
  - `status`
  - `payload`
  - `error_code` when needed

## Phase 4: Wearable Usability
- Shorten spoken messages and make them task-oriented.
- Introduce response priorities: warning, confirmation, information, and failure.
- Support full low-vision and no-screen operation.
- Add non-verbal feedback when appropriate, such as tones or haptics if the hardware supports them.

## Phase 5: Pilot Readiness
- End-to-end testing.
- Testing for timeout conditions, network loss, and noisy environments.
- Packaging and startup automation.
- A release checklist for field testing.

## Success Indicators
- Wake-to-response time is stable and measurable.
- Speech failures do not break the main runtime loop.
- Language, voice, and speed switching work without breaking the current session.
- Stop, start, and system commands do not conflict with close-app protection.
- Capabilities can be enabled and disabled in a clear and observable way.
- The headless version works at least as well as the GUI-driven version.

## Important Architecture Decisions
- `settings_manager` remains the central place for runtime settings, but it should not accumulate extra business logic.
- `dispatcher` and `resolver` remain part of the architecture, but they should evolve to support structured commands and structured results.
- `parser` should not be removed now; it should first be protected by tests and then improved incrementally.
- `mock_controllers.py` should not be deleted immediately; it should remain as a transition layer until real controllers are ready.
- Files under `ui/` should not drive the final glasses architecture, but they remain useful for debugging and local validation.

## Main Risks
- `assistant_worker.py` grows even larger.
- SpeakKit gets integrated too directly, making it hard to replace later.
- Cloud STT and TTS remain in place for too long.
- Real vision capabilities are introduced before lifecycle management and error handling are stable.
- Refactoring continues without test coverage.

## Risk Handling Strategy
- Refactor in small steps.
- End every phase with real execution and a small repeatable validation pass.
- Do not move more than one major responsibility at the same time.
- Any new integration must enter behind a clear interface.

## Definition of Success for This Plan
This plan is successful if the project reaches a stable headless runtime suitable for smart glasses, with a replaceable speech pipeline and real controllers for at least the core capabilities, without throwing away the value of the current codebase.
