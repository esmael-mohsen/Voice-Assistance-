# Quickstart: Hybrid Command Recognition and Post-Processing

## Goal

Validate that the assistant uses a fast local-first command-recognition path,
normalizes noisy bilingual transcripts before parsing, escalates to fallback or
bounded confirmation only when uncertainty requires it, and preserves safe
offline behavior and protected-command safeguards.

## Preconditions

1. Use the project virtual environment and repository root.
2. Keep the active speech-provider configuration aligned with the runtime path
   you want to validate.
3. Enable both Arabic and English command coverage in the local test fixtures.
4. Preserve headless console validation as the reference flow, then use GUI
   validation only as a parity check.

## Validation Paths

### 1. High-Confidence Local-First Commands

1. Exercise representative supported Arabic and English commands that should
   match clearly through the first local recognition path.
2. Confirm the runtime records a local-first recognition result and does not
   invoke fallback or extra confirmation.
3. Verify the command reaches the parser and dispatcher with canonicalized text
   and completes normally.

Expected outcome:
- Supported high-confidence commands execute on the first attempt.
- The runtime does not add unnecessary confirmation or fallback latency.
- Telemetry records the local-first path and a high-confidence decision band.

### 2. Missing-Confidence and Medium-Confidence Handling

1. Exercise a recognition result with no usable confidence score for an
   ordinary non-protected command.
2. Exercise medium-confidence or ambiguous commands that should trigger
   fallback or clarification.
3. Verify the runtime allows at most one additional retry or clarification
   cycle before refusing or deferring the command.

Expected outcome:
- Missing-confidence results are treated as uncertain by default.
- Medium-confidence flows stay bounded and do not loop indefinitely.
- Protected commands never bypass explicit confirmation because of an
  uncertainty edge case.

### 3. Fallback Escalation and Offline Truth

1. Exercise a case where the local path is uncertain but fallback is available.
2. Exercise the same case with network fallback unavailable.
3. Compare the resulting spoken guidance, decision outcome, and telemetry.

Expected outcome:
- Fallback is used only when local evidence is insufficient.
- Offline mode preserves a safe local-only command path for supported commands.
- When fallback is unavailable and the command remains unsafe, the assistant
  refuses truthfully rather than hanging or pretending success.

### 4. Bilingual Normalization and Canonicalization

1. Run a regression set containing noisy transcripts, Arabic-English switching,
   and common substitution patterns.
2. Verify post-processing normalizes transcripts before parser matching.
3. Confirm canonical command text stays stable across equivalent variants.

Expected outcome:
- Common Arabic and English STT substitutions are corrected consistently.
- Mixed-language commands still reach the intended canonical command phrasing
  before parsing.
- Parser keyword coverage can stay focused on canonical phrasing instead of
  endless raw STT variants.

### 5. Protected-Command Confidence Safety

1. Exercise low-confidence and ambiguous transcripts for protected commands such
   as shutdown or reset flows.
2. Confirm the assistant requests explicit affirmative confirmation.
3. Confirm refusal occurs safely when confirmation is not given.

Expected outcome:
- No protected command executes silently under low confidence.
- Protected-command confirmation remains explicit and bounded.
- Telemetry clearly records the protected-command flag and final decision.

### 6. Headless and GUI Parity

1. Exercise the same uncertain command scenario in headless console mode.
2. Repeat it through the GUI runtime bridge.
3. Compare the resulting recognition-path telemetry and decision outcome.

Expected outcome:
- Confidence-band handling and fallback meaning remain the same across entry
  paths.
- GUI presentation does not redefine runtime recognition behavior.

### 7. Latency Baseline Protocol

1. Run 30 representative high-confidence local-first command trials and 30
   representative fallback-assisted command trials in the same validation run.
2. Record timing from recognition start to spoken-response start for every
   trial.
3. Compute the 95th percentile separately for local-first and
   fallback-assisted trials.
4. Store the percentile results and trial counts in the Phase 13 quickstart
   validation evidence.

Expected outcome:
- The 95th percentile for local-first trials is at or below 2 seconds.
- The 95th percentile for fallback-assisted trials is at or below 4 seconds.
- The evidence shows trial counts, percentile method, and measured outcomes.

## Suggested Validation Commands

- `python -m pytest tests/unit/test_parser.py tests/unit/test_resolver.py tests/unit/test_assistant_runtime.py -q`
- `python -m pytest tests/integration/test_command_dispatch.py tests/integration/test_command_dialog_robustness.py tests/integration/test_command_confirmation_localization.py -q`
- `python -m pytest tests/integration/test_runtime_modes.py tests/integration/test_runtime_offline_behavior.py tests/integration/test_gui_runtime_bridge.py -q`
- `python -m pytest tests/smoke/test_command_layer_quickstart.py tests/smoke/test_confirmation_clarification_quickstart.py tests/smoke/test_runtime_quickstart.py -q`
- `python -m compileall core tests`
- `ruff check .`

## Operator Notes

- Local-first remains the default recognition strategy; fallback is evidence of
  uncertainty, not the primary path for every command.
- Missing-confidence results should be reviewed as uncertain decisions unless
  the runtime proves they were unambiguous and non-protected.
- Default telemetry must stay metadata-first and must not expose raw user
  utterances in the normal validation bundle.
- Headless behavior is the reference wearable path; GUI checks are for parity,
  not a separate command-recognition model.
- Record Phase 13 latency evidence with separate 30-trial local-first and
  fallback-assisted batches so `SC-005` stays reviewable and repeatable.

## Validation Evidence (Phase 13)

### Automated Unit Validation

- Command:
  `python -m pytest tests/unit/test_command_recognition_contract.py tests/unit/test_command_post_processing.py tests/unit/test_command_confidence_policy.py tests/unit/test_parser.py tests/unit/test_resolver.py tests/unit/test_assistant_runtime.py -q`
- Result: `53 passed`
- Notes:
  - Covers structured recognition result shaping, missing-confidence handling,
    post-processing substitutions, confidence-band decisions, parser canonical
    input, resolver safety flow, and runtime telemetry emission.

### Automated Integration Validation

- Command:
  `python -m pytest tests/integration/test_command_recognition_runtime.py tests/integration/test_command_dispatch.py tests/integration/test_command_dialog_robustness.py tests/integration/test_command_confirmation_localization.py tests/integration/test_gui_runtime_bridge.py tests/integration/test_runtime_modes.py tests/integration/test_runtime_offline_behavior.py -q`
- Result: `45 passed`
- Notes:
  - Covers local-first recognition orchestration, fallback escalation, protected
    command confirmation behavior, GUI/headless metadata parity, and offline
    safe handling.

### Automated Smoke Validation

- Command:
  `python -m pytest tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_command_layer_quickstart.py tests/smoke/test_confirmation_clarification_quickstart.py tests/smoke/test_runtime_quickstart.py -q`
- Result: `25 passed`
- Notes:
  - Covers high-confidence local-first path, protected-command safety smoke
    behavior, bilingual normalization, and metadata-safe telemetry expectations.

### Tooling Validation

- Command: `python -m compileall core tests`
- Result: `success`
- Command: `ruff check .`
- Result: `not available in environment (ruff command not found)`

### SC Evidence Mapping

- `SC-001`: Covered by local-first unit/integration/smoke path assertions.
- `SC-002` and `SC-003`: Covered by confidence decision and protected-command
  confirmation tests.
- `SC-004`: Covered by runtime offline integration tests plus command
  recognition runtime refusal tests.
- `SC-005`: Latency protocol implementation is wired to telemetry; full
  30/30 percentile field run still required on target hardware.
- `SC-006`: Covered by telemetry payload checks asserting metadata-first records
  with `raw_utterance_present=false`.
