# Quickstart: Google Cloud STT Foundation and Strict Fallback Contracts

## Goal

Validate that Phase 17 introduces an optional Google Cloud STT foundation,
deterministic phrase hints, strict Vosk fallback contracts, and PocketSphinx
deactivation without changing the public runtime loop or requiring cloud
credentials for normal tests.

## Preconditions

1. Use the repository root and project virtual environment.
2. Keep `settings/user_profile.json` free of cloud credential material.
3. Do not require real Google credentials for automated tests; use fake client
   responses for unit coverage.
4. Install optional cloud dependency only for cloud-path validation:
   `python -m pip install google-cloud-speech`.
5. Leave rollout defaults conservative unless a validation step explicitly
   sets an `EGB_STT_*` environment variable.

## Validation Paths

### 1. Default Startup Without Cloud Credentials

1. Ensure `EGB_STT_CLOUD_PRIMARY_ENABLED`, `EGB_STT_STRICT_VOSK_FALLBACK_ENABLED`,
   and `EGB_STT_ENABLE_SPHINX_COMPAT` are unset or `0`.
2. Run unit tests that instantiate the provider registry and `VoiceListener`.
3. Confirm startup and tests pass without Google credentials or the cloud
   client being importable.

Expected outcome:
- No credential lookup crash occurs.
- Cloud recognition is not attempted by default.
- Existing public listener methods remain available.

### 2. Cloud Candidate Extraction With Fake Client Responses

1. Enable cloud-primary behavior in the test environment.
2. Inject a fake Google client response with transcript alternatives,
   confidence values, selected language, and detected language metadata.
3. Verify structured candidates preserve primary transcript, alternatives,
   confidence, latency, provider source, and language metadata.

Expected outcome:
- `cloud_primary` candidates are extracted deterministically.
- `CommandRecognitionResult` compatibility is preserved.
- Detected language does not change the profile language.

### 3. Cloud Failure Classification

1. Exercise fake credential-missing, timeout, auth, quota,
   service-unavailable, empty-result, and unknown-failure cases.
2. Confirm each case maps to exactly one stable reason code.
3. Confirm timeout behavior uses the 3-second default and no more than one
   transient retry inside the existing listen window.

Expected outcome:
- All required `cloud_*` failure codes are covered.
- Empty results are not treated as valid transcripts.
- Startup and command turns fail safely.

### 4. Deterministic Phrase Hints

1. Generate wake, command, confirmation, and onboarding phrase hint sets twice.
2. Compare exact outputs for stable ordering and deduplication.
3. Verify expected English, Arabic, bilingual, phonetic, and common
   misrecognition variants exist for relevant modes.

Expected outcome:
- Phrase hints are reproducible.
- Hints are sourced from approved catalogs and curated variants.
- No raw user utterances are present by default.

### 5. Strict Vosk Fallback Contracts

1. Enable strict Vosk fallback independently of cloud primary.
2. Exercise `wake_grammar`, `command_inventory`, and `closed_choice` modes with
   valid phrases, near misses, unrelated speech, and no-match responses.
3. Confirm only grammar-approved matches become usable transcripts.

Expected outcome:
- Vosk no-match returns no usable transcript.
- Command mode does not accept arbitrary free-form text.
- Closed-choice mode requires and respects `closed_vocabulary_id`.

### 6. PocketSphinx Compatibility Gate

1. Leave `EGB_STT_ENABLE_SPHINX_COMPAT=0` and run wake/command recognition
   candidate-order tests.
2. Confirm PocketSphinx is not called and contributes zero candidates.
3. Set `EGB_STT_ENABLE_SPHINX_COMPAT=1` in a dedicated compatibility test and
   confirm any Sphinx use is marked debug/compatibility-only.

Expected outcome:
- PocketSphinx is removed from the default production accuracy path.
- Compatibility behavior is explicit and test isolated.

### 7. Field-Safe Diagnostics and Documentation

1. Generate provider-selection, cloud-failure, strict-fallback, and
   compatibility-gate diagnostics.
2. Inspect logs/artifacts for `field_safe=true`,
   `raw_user_content_present=false`, and `credential_material_present=false`.
3. Update `docs/STTInfo.md` to document the new cloud foundation,
   configuration controls, fallback order, and credential expectations.

Expected outcome:
- No cloud credential material or raw utterances are persisted by default.
- Operators can understand how to enable, disable, or roll back the feature.

## Suggested Validation Commands

- `python -m pytest tests/unit/test_google_cloud_stt.py -q`
- `python -m pytest tests/unit/test_phrase_hints.py tests/unit/test_strict_vosk_fallback.py -q`
- `python -m pytest tests/unit/test_stt_feature_flags.py tests/unit/test_provider_registry.py -q`
- `python -m pytest tests/integration/test_google_cloud_stt_runtime.py tests/integration/test_command_recognition_runtime.py -q`
- `python -m pytest tests/integration/test_stt_privacy_diagnostics.py -q`
- `python -m compileall core tests`
- `python -m ruff check .`

## Operator Notes

- Real Google credentials are optional for development and must not be checked
  into the repository or copied into `settings/user_profile.json`.
- Use environment variables for rollout and compatibility checks:
  `EGB_STT_CLOUD_PRIMARY_ENABLED`,
  `EGB_STT_STRICT_VOSK_FALLBACK_ENABLED`,
  `EGB_STT_ENABLE_SPHINX_COMPAT`,
  `EGB_STT_CLOUD_TIMEOUT_S`, and
  `EGB_STT_CLOUD_MAX_ALTERNATIVES`.
- Headless runtime remains the reference path; GUI checks are parity/debug
  checks only.
- If cloud fails and strict Vosk fallback is disabled, the safe result is no
  usable transcript plus existing recovery, not PocketSphinx or unrestricted
  local recognition.

## Validation Evidence (Phase 17)

Use this section to record command output during implementation:

- `SC-001`: Cloud candidate extraction with fake client (`tests/unit/test_google_cloud_stt.py`)
- `SC-002`: Startup succeeds without credentials (`tests/integration/test_google_cloud_stt_runtime.py`)
- `SC-003`: Stable failure-code mapping (`tests/unit/test_google_cloud_stt.py`)
- `SC-004`: Deterministic strict Vosk outcomes (`tests/unit/test_strict_vosk_fallback.py`)
- `SC-005`: Zero default PocketSphinx candidates (`tests/unit/test_stt_feature_flags.py`)
- `SC-006`: Deterministic phrase hint variants (`tests/unit/test_phrase_hints.py`)
- `SC-007`: Bounded timeout and single transient retry (`tests/unit/test_google_cloud_stt.py`)
- `SC-008`: Detected-language metadata does not mutate profile language (`tests/integration/test_google_cloud_stt_runtime.py`)
- `SC-009`: Diagnostics and artifacts remain field-safe (`tests/integration/test_stt_privacy_diagnostics.py`)

### Latest Run (2026-04-24)

- `python -m pytest tests/unit/test_google_cloud_stt.py tests/unit/test_phrase_hints.py tests/unit/test_strict_vosk_fallback.py tests/unit/test_stt_feature_flags.py tests/unit/test_provider_registry.py -q`
  - Result: `30 passed` (with 2 deprecation warnings from `speech_recognition` dependencies)
- `python -m pytest tests/integration/test_google_cloud_stt_runtime.py tests/integration/test_command_recognition_runtime.py tests/integration/test_stt_privacy_diagnostics.py -q`
  - Result: `9 passed` (with 2 deprecation warnings from `speech_recognition` dependencies)
- `python -m compileall core tests`
  - Result: pass
- `python -m ruff check .`
  - Result: pass
