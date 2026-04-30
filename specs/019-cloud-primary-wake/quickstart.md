# Quickstart: Cloud-Primary Wake Recognition and Standby Fallback Reliability

## Purpose

Validate that standby wake can use cloud-primary STT with wake-specific phrase
hints, strict local wake grammar fallback, canonical wake acceptance, and
field-safe diagnostics without breaking keyword/hardware wake or requiring live
cloud credentials in the default test suite.

## Prerequisites

1. Use Python 3.12.4 in the project virtual environment.
2. Keep Google Cloud credentials outside `settings/user_profile.json`.
3. Use a runtime/test settings snapshot that enables STT-based wake when
   validating the speech wake path.
4. Keep cloud-primary wake opt-in unless a validation step explicitly enables
   it.
5. Prefer fake cloud clients or monkeypatched recognizers for automated tests.

## Configuration Controls

Use the existing STT rollout controls when validating the cloud wake path:

```powershell
$env:EGB_STT_CLOUD_PRIMARY_ENABLED="1"
$env:EGB_STT_STRICT_VOSK_FALLBACK_ENABLED="1"
$env:EGB_STT_ENABLE_SPHINX_COMPAT="0"
$env:EGB_STT_CLOUD_TIMEOUT_S="3.0"
$env:EGB_STT_CLOUD_MAX_ALTERNATIVES="3"
```

Use a settings snapshot or fixture that keeps wake mode compatible with speech
wake validation:

- `wake_primary_mode="stt_based_wake"`
- `stt_wake_allowed_in_production=true` for production-like wake validation
- `standby_capture_profile_id="standby_wake.default"`

Reset or remove the environment variables to validate disabled-rollout parity.

## Validation Steps

### 1. Disabled Rollout Parity

1. Disable `EGB_STT_CLOUD_PRIMARY_ENABLED`.
2. Run existing keyword, hardware-trigger, and non-cloud STT wake regression
   fixtures.
3. Confirm standby behavior remains compatible with the prior wake path.

Expected result:
- Existing non-cloud wake behavior remains intact.
- Cloud credentials are not required.
- Keyword and hardware-trigger wake are unaffected.

### 2. Cloud Wake Success

1. Enable cloud primary and strict local fallback.
2. Use a fake cloud response that returns a canonical wake transcript such as
   `hi egb` or `مرحبا`.
3. Exercise the standby wake attempt through the runtime or wake service.

Expected result:
- The wake attempt is accepted within the bounded wake window.
- The accepted source classification is `cloud_primary`.
- Canonical wake matching remains the final acceptance gate.

### 3. Cloud Failure To Strict Local Wake Fallback

1. Keep cloud primary and strict local fallback enabled.
2. Simulate cloud timeout, unavailable, empty result, and non-canonical cloud
   transcript cases.
3. Return a strict grammar wake match for one fixture and a no-match for
   another.

Expected result:
- Strict local wake fallback runs only after the allowed cloud failure or
  non-canonical cases.
- Matched fallback attempts classify the accepted source as
  `wake_strict_vosk_fallback`.
- No-match fallback produces `wake_missed`, not a crash or a broad free-form
  transcript.

### 4. Non-Canonical And Command-Only Rejection

1. Simulate high-confidence unrelated speech.
2. Simulate command-like speech that contains no canonical wake phrase.
3. Simulate similar-sounding non-wake words and short noise bursts.

Expected result:
- The runtime produces `wake_rejected` for non-canonical speech.
- Command-only speech never wakes the assistant.
- The assistant remains in standby safely.

### 5. Wake-Plus-Command Safety

1. Simulate a transcript such as `hi egb open navigation`.
2. Repeat the scenario in English, Arabic, and mixed fixtures.

Expected result:
- Wake may be accepted only if the wake portion is canonical.
- The runtime treats the utterance as wake-only.
- The command portion is not executed or queued from the same utterance.

### 6. Wake Hint And Grammar Governance

1. Generate the wake phrase-hint set repeatedly.
2. Assert deterministic order and deduplication.
3. Verify canonical, Arabic, bilingual, phonetic, and safe STT-mistake
   entries.
4. Verify the wake cloud hint cap and strict grammar cap behavior.

Expected result:
- Canonical wake aliases always remain present.
- The wake inventory stays bounded and deterministic.
- Raw user utterances are not included by default.

### 7. Network-Down And Repeated-Miss Stability

1. Simulate network loss while speech wake remains enabled and strict local
   fallback is available.
2. Run at least 50 consecutive wake misses in standby.

Expected result:
- Speech wake still uses strict local wake fallback where configured.
- Repeated misses do not stall, crash, or exit the runtime unexpectedly.
- Each attempt returns to standby within the bounded wake window.

### 8. Diagnostics And Privacy

1. Generate cloud success, cloud failure, strict fallback success, strict
   fallback no-match, non-canonical rejection, and repeated-miss outcomes.
2. Inspect runtime logs, diagnostics payloads, and any artifact serializers.

Expected result:
- Outcomes distinguish accepted, rejected, missed, degraded, and fallback-used
  cases.
- Diagnostics do not persist raw utterances or credential material by default.
- Source classification and failure reason are visible in a field-safe form.

## Suggested Automated Checks

```powershell
python -m pytest tests/unit/test_cloud_wake_recognition.py tests/unit/test_phrase_hints.py tests/unit/test_strict_vosk_fallback.py tests/unit/test_wake_word_canonical.py -q
python -m pytest tests/unit/test_wake_strategy_runtime.py tests/integration/test_wake_strategy_modes.py tests/integration/test_stt_privacy_diagnostics.py -q
python -m compileall core tests
python -m ruff check .
```

If a listed test file does not exist yet, create it during implementation for
the corresponding scenario rather than skipping the scenario.

## Validation Evidence (2026-04-26)

- `T020`: `python -m pytest tests/unit/test_cloud_wake_recognition.py tests/unit/test_strict_vosk_fallback.py tests/integration/test_wake_strategy_modes.py tests/integration/test_google_cloud_stt_runtime.py tests/smoke/test_wake_strategy_quickstart.py -q`  
  Result: `40 passed, 2 warnings` (SC-001, SC-002, SC-006 evidence).
- `T029`: `python -m pytest tests/unit/test_cloud_wake_recognition.py tests/unit/test_wake_word_profiles.py tests/unit/test_wake_word_canonical.py tests/unit/test_phrase_hints.py tests/integration/test_wake_strategy_modes.py tests/integration/test_runtime_modes.py tests/integration/test_stt_privacy_diagnostics.py -q`  
  Result: `62 passed, 2 warnings` (SC-003 plus FR-010 and FR-020 evidence).
- `T037`: `python -m pytest tests/unit/test_provider_resolver.py tests/unit/test_stt_feature_flags.py tests/unit/test_wake_strategy_runtime.py tests/unit/test_assistant_runtime.py tests/integration/test_runtime_modes.py tests/integration/test_wake_strategy_modes.py tests/smoke/test_wake_strategy_quickstart.py -q`  
  Result: `90 passed, 2 warnings` (SC-004 plus FR-011, FR-013, and FR-019 evidence).
- `T044`: `python -m pytest tests/unit/test_runtime_contract.py tests/integration/test_stt_privacy_diagnostics.py tests/integration/test_google_cloud_stt_runtime.py tests/integration/test_speech_telemetry_pipeline.py -q`  
  Result: `31 passed, 2 warnings` (SC-005 evidence).
- `T047`: `python -m pytest tests/unit/test_cloud_wake_recognition.py tests/unit/test_strict_vosk_fallback.py tests/unit/test_phrase_hints.py tests/unit/test_wake_word_canonical.py tests/unit/test_wake_word_profiles.py tests/unit/test_provider_resolver.py tests/unit/test_stt_feature_flags.py tests/unit/test_wake_strategy_runtime.py tests/unit/test_assistant_runtime.py tests/unit/test_runtime_contract.py -q`  
  Result: `112 passed, 2 warnings`.
- `T048`: `python -m pytest tests/integration/test_google_cloud_stt_runtime.py tests/integration/test_wake_strategy_modes.py tests/integration/test_runtime_modes.py tests/integration/test_stt_privacy_diagnostics.py tests/integration/test_speech_telemetry_pipeline.py tests/smoke/test_wake_strategy_quickstart.py -q`  
  Result: `49 passed, 2 warnings`.
- `T049`: `python -m compileall core tests` and `python -m ruff check .`  
  Result: compile completed, `ruff` reports `All checks passed!`.

Warnings observed in all pytest runs: Python 3.12 deprecation warnings from
`speech_recognition` imports (`aifc`, `audioop`).

## Contract Reconciliation (2026-04-26)

- `wake-recognition-result-contract.md`: verified `recognition_source`,
  `failure_reason_code`, `command_suffix_ignored`, and field-safe defaults via
  `tests/unit/test_cloud_wake_recognition.py`,
  `tests/integration/test_google_cloud_stt_runtime.py`, and
  `tests/integration/test_wake_strategy_modes.py`.
- `strict-wake-fallback-contract.md`: verified strict wake grammar boundaries
  and no-match behavior via `tests/unit/test_strict_vosk_fallback.py` and
  `tests/unit/test_stt_feature_flags.py`.
- `standby-wake-outcome-contract.md`: verified accepted/rejected/missed
  outcomes and source classifications via `tests/unit/test_runtime_contract.py`,
  `tests/unit/test_assistant_runtime.py`, and
  `tests/integration/test_wake_strategy_modes.py`.

## Privacy Audit (2026-04-26)

- Reviewed `core/stt.py`, `core/assistant_runtime.py`,
  `core/runtime_diagnostics.py`, `settings/user_profile.json`, and
  `docs/STTInfo.md`.
- Confirmed runtime diagnostics and wake outcomes default to
  `field_safe=true` and `raw_user_content_present=false`.
- Confirmed no cloud credential payload is persisted in
  `settings/user_profile.json`; credentials remain external.

## Manual Smoke Check

1. Start the assistant with cloud primary disabled and confirm existing wake
   behavior still works.
2. Start the assistant with cloud primary enabled and strict fallback enabled.
3. Exercise a canonical wake, a cloud-timeout-to-fallback wake, unrelated
   speech, and a wake-plus-command utterance.
4. Watch the terminal or diagnostics output for source classification and safe
   return-to-standby behavior.

Expected result:
- Canonical wake succeeds quickly.
- Cloud failure recovers through strict local wake fallback when configured.
- Unrelated speech does not wake the assistant.
- Wake-plus-command does not execute the command immediately.

## Success Criteria Mapping

- `SC-001`: Canonical wake fixtures succeed through cloud primary within the
  7-second wake window.
- `SC-002`: Canonical wake fixtures still succeed through strict local
  fallback when cloud is unavailable.
- `SC-003`: Covered negative fixtures produce zero false accepts.
- `SC-004`: Repeated wake misses remain stable for at least 50 attempts.
- `SC-005`: Every covered attempt emits a field-safe structured outcome with
  source classification.
- `SC-006`: Covered attempts always return the runtime to wake or standby
  within the bounded wake window.

