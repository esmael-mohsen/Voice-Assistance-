# Quickstart: Cloud-Primary Command Recognition and Safety-Aware Fallback

## Purpose

Validate that command-mode recognition can use cloud primary with command
phrase hints, strict grammar fallback, existing command safety policy, and
field-safe diagnostics without changing wake recognition or requiring live
cloud credentials in the default test suite.

## Prerequisites

1. Use Python 3.12.4 in the project virtual environment.
2. Keep Google Cloud credentials outside `settings/user_profile.json`.
3. Keep cloud-primary command recognition disabled unless a validation step
   explicitly enables it.
4. Use fake cloud clients or monkeypatched recognizers for automated tests.
5. Optional live cloud validation may install `google-cloud-speech`, but live
   credentials are not required for the default validation path.

## Configuration Controls

Use the Phase 17 controls:

```powershell
$env:EGB_STT_CLOUD_PRIMARY_ENABLED="1"
$env:EGB_STT_STRICT_VOSK_FALLBACK_ENABLED="1"
$env:EGB_STT_ENABLE_SPHINX_COMPAT="0"
$env:EGB_STT_CLOUD_TIMEOUT_S="3.0"
$env:EGB_STT_CLOUD_MAX_ALTERNATIVES="3"
```

Reset or remove the variables to validate disabled rollout parity.

## Validation Steps

### 1. Disabled Rollout Parity

1. Ensure `EGB_STT_CLOUD_PRIMARY_ENABLED` is unset or `0`.
2. Run existing command-recognition regression fixtures.
3. Confirm `recognition_source` remains compatible with the previous local
   command path and no cloud client is required.

Expected result:
- Existing command behavior remains unchanged for covered fixtures.
- Startup and tests pass without Google credentials.

### 2. Cloud Command Success

1. Enable cloud primary and use a fake cloud response for a supported command,
   such as `detect obstacle`.
2. Include alternatives and confidence in the fake response.
3. Call `VoiceListener.listen_command_result(...)` or the runtime bounded
   command-listen path.

Expected result:
- `CommandRecognitionResult.primary_transcript` is populated.
- `recognition_source=cloud_primary`.
- Confidence, alternatives, selected language, detected language, and latency
  metadata are preserved.
- Parser and confidence policy still decide execution.

### 2A. Baseline Comparison Fixtures

1. Run the same Arabic, bilingual, and common-command fixture set with
   cloud-primary disabled to record the local-first baseline.
2. Re-run the fixture set with cloud-primary enabled and fake cloud responses.
3. Record these counts in the validation notes:
   - Arabic and bilingual command-resolution successes.
   - Common-command fallback-to-retry outcomes.

Expected result:
- Cloud-primary Arabic and bilingual command-resolution success count is
  strictly higher than the local-first baseline for the same fixtures.
- Cloud-primary common-command fallback-to-retry count is strictly lower than
  the local-first baseline for the same fixtures.

### 3. Cloud Failure To Strict Fallback

1. Enable cloud primary and strict Vosk fallback.
2. Simulate cloud timeout, unavailable, empty result, and missing transcript.
3. Return a strict grammar match for one fixture and no match for another.

Expected result:
- Provider failures try strict fallback only when enabled.
- Matched fallback candidates use `recognition_source=strict_vosk_fallback`.
- No-match fallback returns no usable transcript and routes to existing
  recovery.
- No broad dictation or PocketSphinx default command candidate appears.

### 4. Low Confidence And Parser Rejection

1. Simulate a cloud transcript with low confidence.
2. Simulate a cloud transcript that post-processing or parser validation
   rejects.
3. Verify runtime policy requests retry, confirmation, fallback, or refusal
   instead of direct execution.

Expected result:
- Existing confidence thresholds determine the action.
- Provider confidence alone never executes a command.
- Rescue/fallback stays bounded by the command listen window.

### 5. Command Phrase Hint Governance

1. Generate command phrase hints repeatedly.
2. Assert deterministic order and deduplication.
3. Verify required protected, assistive, Arabic, bilingual, phonetic, and
   common misrecognition variants.
4. Verify cloud hint cap and strict grammar cap behavior.

Expected result:
- Protected/safety-critical commands retain high priority.
- Raw user utterances are not included by default.
- Hint output is stable across runs.

### 6. Protected Command Safety

1. Simulate high-confidence cloud recognition for protected commands such as
   `stop system`, emergency actions, reset, and settings-sensitive changes.
2. Include alternatives that conflict with the protected intent.
3. Include wake wording before the command while already in command mode.

Expected result:
- Protected commands require explicit affirmative confirmation.
- Ambiguous protected commands confirm, retry, or refuse.
- Wake wording never bypasses validation or confirmation.

### 7. Diagnostics And Privacy

1. Generate cloud success, cloud failure, strict fallback match, strict
   fallback no-match, and protected-command confirmation events.
2. Inspect runtime logs, release diagnostics, and any artifact serializers.

Expected result:
- Diagnostics include recognition source, fallback decision, confidence band,
  language mismatch, failure reason, and latency category.
- Diagnostics do not persist raw utterances or credential material by default.

## Suggested Automated Checks

```powershell
python -m pytest tests/unit/test_phrase_hints.py tests/unit/test_strict_vosk_fallback.py tests/unit/test_stt_feature_flags.py -q
python -m pytest tests/unit/test_command_confidence_policy.py tests/unit/test_command_post_processing.py tests/unit/test_parser.py -q
python -m pytest tests/integration/test_google_cloud_stt_runtime.py tests/integration/test_command_recognition_runtime.py tests/integration/test_stt_privacy_diagnostics.py -q
python -m compileall core tests
python -m ruff check .
```

If a listed test file does not exist yet, create it during implementation tasks
for the corresponding scenario instead of skipping the scenario.

## Manual Smoke Check

1. Start the assistant with cloud primary disabled and confirm normal command
   behavior.
2. Start the assistant with cloud primary enabled and fake/fallback-safe
   recognition wiring.
3. Speak a low-risk command, a protected command, and unrelated speech.
4. Confirm the terminal or logs clearly show field-safe source/fallback
   diagnostics.

Expected result:
- Low-risk clean commands can execute normally.
- Protected commands ask for confirmation.
- Unrelated speech does not produce a command.
- Runtime returns to listening/standby without crashes.

## Success Criteria Mapping

- `SC-001`: Cloud-primary command candidate with unchanged command flow.
- `SC-002`: Arabic and bilingual command fixtures produce a strictly higher
  success count than the recorded local-first baseline for the same fixtures.
- `SC-003`: Common fixtures produce a strictly lower fallback-to-retry count
  than the recorded local-first baseline for the same fixtures.
- `SC-004`: Zero default PocketSphinx command candidates.
- `SC-005`: Cloud timeout/empty/low-confidence/unavailable recover safely.
- `SC-006`: Strict fallback no-match returns no usable transcript.
- `SC-007`: Protected commands never execute without confirmation.
- `SC-008`: Alternatives remain available to downstream policy.
- `SC-009`: Diagnostics are field-safe and source-aware.
- `SC-010`: Disabled rollout preserves covered regression behavior.
- `SC-011`: No-match strict fallback routes to existing recovery.
- `SC-012`: Wake-plus-protected-command fixtures require confirmation.

## Phase 18 Validation Notes (2026-04-24)

### Baseline Comparison Summary

- Arabic and bilingual fixture command-resolution successes:
  - Local-first baseline: `1/4`
  - Cloud-primary run: `4/4`
- Common-command fallback-to-retry proxy count:
  - Local-first baseline: `2/3`
  - Cloud-primary run: `0/3`

### Executed Validation Commands

```powershell
venv\Scripts\python.exe -m pytest tests/unit/test_cloud_command_recognition.py tests/unit/test_stt_feature_flags.py tests/unit/test_strict_vosk_fallback.py tests/unit/test_phrase_hints.py tests/unit/test_command_confidence_policy.py tests/unit/test_command_post_processing.py -q
```

Result: `38 passed, 2 warnings`

```powershell
venv\Scripts\python.exe -m pytest tests/integration/test_command_recognition_runtime.py tests/integration/test_stt_privacy_diagnostics.py -q
```

Result: `12 passed, 2 warnings`

```powershell
venv\Scripts\python.exe -m compileall core tests
```

Result: `success (no compile errors)`

```powershell
venv\Scripts\python.exe -m ruff check .
```

Result: `All checks passed!`
