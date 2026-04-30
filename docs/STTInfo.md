# STT Foundation (Phase 17 + Phase 18 Command Rollout)

This document describes the current STT behavior after Phase 17 foundations:

- Optional Google Cloud STT boundary (`core/speech/google_cloud_stt.py`)
- Deterministic phrase hints (`core/speech/phrase_hints.py`)
- Strict Vosk fallback contracts in `core/stt.py`
- PocketSphinx compatibility gate (disabled by default)

## 1. Runtime Surface

Public listener methods are unchanged:

- `listen_any(...)`
- `listen_command(...)`
- `listen_command_result(...)`
- `listen_command_window(...)`

`CommandRecognitionResult` now carries additional metadata when available:

- `recognition_source` (`cloud_primary`, `strict_vosk_fallback`, `wake_strict_vosk_fallback`, `rescue_strict_vosk`, `cloud_unavailable`, `local_vosk`, `sphinx_compat`, `legacy_local`, `keyword_low_power`, `hardware_trigger`, `noncanonical_rejected`)
- `failure_reason_code` (stable cloud/strict reason code)
- `selected_language` (profile language used for recognition request)
- `command_suffix_ignored` (wake accepted but trailing command text was dropped)

`StandbyWakeOutcome` emits a field-safe wake taxonomy for runtime state flow:

- `status`: `wake_accepted`, `wake_rejected`, `wake_missed`, `degraded_standby`
- `source_classification`: `cloud_primary`, `wake_strict_vosk_fallback`, `noncanonical_rejected`, `keyword_low_power`, `hardware_trigger`
- `payload.field_safe=true` and `payload.raw_user_content_present=false` by default

## 2. Recognition Order

For command listening:

1. If `EGB_STT_CLOUD_PRIMARY_ENABLED=1`, try Google Cloud STT first.
2. If cloud fails and `EGB_STT_STRICT_VOSK_FALLBACK_ENABLED=1`, try strict Vosk with bounded grammar.
3. If cloud fails and strict fallback is disabled, return no usable transcript and emit `recognition_source=cloud_unavailable`.
4. Runtime-level low confidence, language mismatch, alternatives conflict, and parser rejection use existing bounded rescue/retry/confirm/refuse policy.
4. PocketSphinx is excluded from default production ranking unless explicitly enabled.

For standby wake (`usage_mode="standby_wake"`):

1. Cloud-primary wake candidate path runs first when rollout is enabled.
2. Strict wake grammar fallback runs for cloud failure/empty/unavailable outcomes and
   reports `wake_strict_vosk_fallback`.
3. Canonical wake gating remains the final acceptance authority.
4. Wake-plus-command utterances are treated as wake-only (`command_suffix_ignored=true`).

For wake/general listening (`listen_any`), Vosk remains available locally; PocketSphinx is compatibility-only.

## 3. Environment Controls

Phase 17 controls:

- `EGB_STT_CLOUD_PRIMARY_ENABLED` (default `0`)
- `EGB_STT_STRICT_VOSK_FALLBACK_ENABLED` (default `0`)
- `EGB_STT_ENABLE_SPHINX_COMPAT` (default `0`)
- `EGB_STT_CLOUD_TIMEOUT_S` (default `3.0`)
- `EGB_STT_CLOUD_MAX_ALTERNATIVES` (default `3`)

Legacy controls still supported:

- `EGB_STT_ENGINE` (`auto|vosk|google` with safe fallback to `auto`)
- `EGB_STT_VOSK_ONLY`
- `EGB_VOSK_MODEL_AR`
- `EGB_VOSK_MODEL_EN`
- `EGB_VOSK_MODEL_DIR`

## 4. Optional Cloud Dependency

Install optional cloud package:

```bash
python -m pip install google-cloud-speech
```

Credentials are read from normal Google ADC paths (for example `GOOGLE_APPLICATION_CREDENTIALS`).

Important privacy boundary:

- Do not store credentials in `settings/user_profile.json`.
- Do not persist raw utterances in default diagnostics/artifacts.

## 5. Failure Reason Codes

Cloud reason codes:

- `cloud_credentials_missing`
- `cloud_network_timeout`
- `cloud_auth_error`
- `cloud_quota_error`
- `cloud_service_unavailable`
- `cloud_empty_result`
- `cloud_unknown_failure`

Strict fallback reason codes:

- `strict_grammar_no_match`
- `strict_vosk_unavailable`
- `strict_vosk_failed`

## 6. Phrase Hints and Strict Fallback

Phrase hints are deterministic and mode-specific:

- `wake`
- `command`
- `confirmation`
- `onboarding`

Strict Vosk modes:

- `wake_grammar`
- `command_inventory`
- `closed_choice`

Command-mode hint governance:

- Cloud command hint cap: `72` phrases (`DEFAULT_CLOUD_COMMAND_HINT_CAP`).
- Strict grammar cap: `220` phrases (`DEFAULT_COMMAND_HINT_CAP`).
- Priority keeps protected/safety commands first, then parser catalog, then assistive/Arabic/bilingual/phonetic/mistake variants.
- No raw user utterance history is included in default hint sets.

No-match outcomes return no usable transcript instead of free-form command text.

## 7. Diagnostics

STT diagnostics are emitted with field-safe metadata:

- `field_safe=true`
- `raw_user_content_present=false`
- stable `reason_code`
- provider source, fallback mode, fallback trigger, and confidence-band-safe outcomes

No raw utterance or credential material is stored by default.

## 8. Phase 20 Command Safety Notes

Phase 20 keeps command understanding improvements inside the existing
post-processing, parser, and runtime decision pipeline:

- Supported Arabic, bilingual, and phonetic variants are curated and mapped to
  existing intent boundaries only.
- Corrupted Arabic-like text and mojibake are treated as non-executable before
  parser execution.
- Medium-risk command handling uses stable-candidate evidence, language
  mismatch, alternatives conflict, and substitution markers when deciding
  confirm/retry/refuse.
- Protected commands remain confirmation-gated; no direct execution path is
  added for ambiguous or corrupted protected-command input.

Field-safe command metadata remains required for diagnostics:

- `integrity_status`
- `substitution_ids`
- `confidence_band`
- `language_mismatch` markers
- alternatives-conflict markers
- `field_safe=true`, `raw_user_content_present=false`

## 9. Phase 21 Rollout Observability and PocketSphinx Decommission

Phase 21 adds release-safe STT observability and rollout gate contracts while
keeping the existing runtime boundaries:

- Event-level STT telemetry and per-run rollups are field-safe and keyed by
  session and candidate run.
- Rollout progression is conservative: `shadow` -> `wake_only` ->
  `commands_low_risk` -> `full_cloud_primary`.
- Rollback override can force `effective_mode=rollback` at any time during
  field validation.
- STT failure scenarios are classified into bounded outcomes:
  `fallback`, `retry`, `safe_refusal`, or `standby`.
- Release gates block pilot and field readiness for:
  cloud configuration regressions, missing strict fallback, unsafe wake
  fallback, protected-command regression, bilingual regression, bounded
  recovery regression, default PocketSphinx usage, or missing/failed Pi 4
  evidence.

PocketSphinx status after Phase 21:

- Default production readiness requires zero PocketSphinx candidates and zero
  default PocketSphinx invocations.
- Compatibility-only behavior remains available only when explicitly enabled.
- Production accuracy baseline excludes PocketSphinx-specific checks.
