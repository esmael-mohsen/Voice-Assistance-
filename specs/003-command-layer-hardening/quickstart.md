# Quickstart: Command Layer Hardening

## Goal

Validate that the assistant recognizes the current high-priority bilingual
command set more safely, returns structured command outcomes, and preserves
equivalent behavior across GUI and console runtime paths.

## Prerequisites

1. Create and activate the project virtual environment.
2. Install the project's Python dependencies, including `rapidfuzz` and
   `pytest`.
3. Ensure the runtime can be started in both GUI and console modes.
4. Prepare representative Arabic and English utterances for:
   - protected system commands
   - everyday assistant commands
   - high-value capability commands

## Coverage Baseline

Use this phase's minimum regression set:

- Protected system commands: `stop_system`, `reset_settings`
- Lower-risk system commands: `start_system`, `get_system_status`
- Everyday assistant commands: language, voice, and speech-speed controls
- High-value capability commands: obstacle detection on or off, OCR on or off,
  face recognition, emotion recognition as a one-turn follow-up, and money
  detection on or off

## Validation Matrix

| Scenario | Expected Result |
|---|---|
| Clear everyday Arabic or English command | Structured `success` result with correct spoken response |
| Weak or noisy near-match | Structured `rejected` result with safe guidance |
| Missing required parameter | Structured `clarification_required` result, one retry maximum |
| Protected system command first turn | Structured `confirmation_required` result |
| Protected system confirmation turn | Command executes only after explicit confirmation |
| Provider degradation during command flow | Safe structured failure guidance and preserved fallback behavior |
| Face recognition then emotion follow-up | Follow-up uses stored face context once, then clears it |
| Same regression flow in GUI and console | Equivalent command outcome and spoken behavior |

## Path 1: Parser and Resolver Regression

1. Run focused unit tests for parser and resolver behavior.
2. Confirm bilingual command families pass their acceptance cases.
3. Confirm ambiguous or near-match phrases are rejected instead of routed.
4. Confirm protected system commands require confirmation.

## Path 2: Structured Dispatch Contract

1. Execute dispatcher integration tests for representative command families.
2. Confirm every dispatch path returns a structured result with `status` and
   `spoken_text`.
3. Confirm success, clarification, confirmation, rejection, and failure states
   all use the same result model.

## Path 3: GUI and Console Runtime Parity

1. Run console mode with representative command scenarios.
2. Run GUI mode or GUI worker integration coverage for the same scenarios.
3. Confirm the structured command outcome is normalized into equivalent
   user-visible spoken behavior in both paths.

## Path 4: Follow-Up and Safety Flows

1. Trigger `recognize_face` and then an immediate emotion follow-up.
2. Confirm the follow-up context is consumed exactly once.
3. Trigger a protected system command and verify confirmation is required.
4. Trigger an ambiguous phrase near a protected system command and confirm the
   action is rejected or clarified, never executed.

## Measurement Targets

| Check | Threshold |
|---|---|
| Curated Arabic and English regression success rate | >= 90% |
| Unintended protected system activations in near-match coverage | 0 |
| Ambiguous or invalid scenarios returning structured safe outcome | 100% |
| GUI and console parity across high-priority regression set | 100% |
| Follow-up context reuse after one immediate command | 0 cases |
| Baseline capture coverage for wake/STT/TTS/dispatch/recovery | 1 representative sample per path |

## Suggested Validation Commands

- `python -m compileall main.py core settings tts ui tests`
- `python -m pytest tests/unit/test_parser.py tests/unit/test_resolver.py -q`
- `python -m pytest tests/integration/test_command_dispatch.py -q`
- `python -m pytest tests/smoke/test_command_layer_quickstart.py -q`
- `python -m pytest tests -q`

## Baseline Capture Notes

1. Record one representative timing sample each for:
   - wake detection
   - STT response
   - TTS start
   - command dispatch completion
   - recoverable provider-failure handling
2. Compare command dispatch timing to the prior recorded baseline and flag if
   the median regresses by more than 10%.
3. If `pytest` or speech-provider dependencies are unavailable in the active
   shell, capture compile and dependency errors and rerun once the environment
   is prepared.

## Latest Validation Snapshot (2026-04-18)

- SC-001 curated regression success rate: `0.909`
- SC-002 unintended protected activations: `0`
- SC-003 safe structured outcomes for ambiguous or invalid requests: `1.000`
- SC-004 GUI/console parity check result: `1` (parity preserved)
- Representative wake baseline: `0.032 ms`
- Representative STT baseline: `0.005 ms`
- Representative TTS-start baseline: `0.003 ms`
- Representative dispatch baseline: `1.233 ms`
- Representative recoverable-failure baseline: `15.224 ms`

If the targeted files do not exist yet, create them as part of implementation
before relying on the focused commands above.
