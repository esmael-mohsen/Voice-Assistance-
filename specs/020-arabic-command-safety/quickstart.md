# Quickstart: Arabic, Bilingual Canonicalization, and Safety Confidence Hardening

## Purpose

Validate that supported Arabic, Egyptian-Arabic, Arabizi, and mixed-language
commands normalize into safe parser-ready command text, while corrupted text,
language mismatch, and protected-command uncertainty still route through
retry, confirmation, or refusal without exposing raw utterances in default
diagnostics.

## Prerequisites

1. Use Python 3.12.4 in the project virtual environment.
2. Keep command diagnostics field-safe by default; do not persist raw
   utterances during validation.
3. Use settings and environment snapshots that reflect the current command
   confidence thresholds.
4. Prefer fake or fixture-driven recognition metadata instead of live cloud
   dependencies for the default validation path.

## Configuration Controls

Phase 20 depends on the existing command-recognition controls rather than a
new rollout surface. Validate with the current settings snapshot values for:

- `command_confidence_high_threshold`
- `command_confidence_medium_threshold`
- `command_protected_threshold`
- `command_allow_missing_confidence_for_unprotected`
- `command_fallback_enabled`
- `command_rescue_enabled`
- `command_capture_profile_id`
- `confirmation_capture_profile_id`

If you need cloud-primary command metadata in a runtime smoke check, keep the
existing STT controls aligned with the current branch:

```powershell
$env:EGB_STT_CLOUD_PRIMARY_ENABLED="1"
$env:EGB_STT_STRICT_VOSK_FALLBACK_ENABLED="1"
$env:EGB_STT_ENABLE_SPHINX_COMPAT="0"
```

## Validation Steps

### 1. Supported Arabic Command Mapping

1. Feed supported Arabic fixtures for existing commands such as OCR, obstacle
   detection, language switching, and system status.
2. Exercise both parser-only tests and runtime command-recognition flows.

Expected result:
- Supported Arabic phrases resolve to the intended existing intent IDs.
- Canonicalized command text stays within the existing command catalog.
- No new executable intent surface is introduced.

### 2. Bilingual And Arabizi Variant Mapping

1. Run mixed Arabic/English and phonetic fixtures that are explicitly curated
   in the supported inventory.
2. Include near-neighbor forms that should map and forms that should stay out
   of scope.

Expected result:
- Curated bilingual and Arabizi phrases map to the intended existing command
  meaning.
- Unsupported near-miss phrases do not silently execute.
- Variant handling remains deterministic and auditable.

### 3. Corrupted Arabic-Like Text And Mojibake Rejection

1. Feed corrupted Arabic-like text, mojibake samples, and encoding-damaged
   transcripts into post-processing and runtime safety evaluation.
2. Repeat the scenarios for low-risk and protected-command candidates.

Expected result:
- Corrupted text is classified as non-executable before parser execution.
- Protected-command corruption paths refuse safely rather than retry toward
  execution.
- Non-protected corruption paths retry only when the policy still allows a
  safe bounded recovery.

### 4. Confidence And Language-Mismatch Recovery

1. Exercise command-recognition results with medium confidence,
   conflicting alternatives, and selected/detected language mismatch.
2. Include cases where a stable supported candidate remains and cases where it
   does not.

Expected result:
- Stable medium-risk candidates trigger confirmation instead of direct
  execution.
- Unstable or conflicting candidates trigger retry, fallback, or refusal.
- Language mismatch remains visible in field-safe metadata.

### 5. Protected-Command Safety

1. Exercise `stop system`, reset/settings-sensitive commands, and any critical
   wearable actions under clean, ambiguous, corrupted, and mixed-language
   transcripts.
2. Validate both initial command resolution and the confirmation reply.

Expected result:
- Protected commands never execute without explicit affirmative confirmation.
- Near-miss or corrupted protected-command phrases do not execute directly.
- Confirmation behavior stays consistent across Arabic, English, and mixed
  replies.

### 6. Closed-Vocabulary And Confirmation Parity

1. Run bilingual yes/no/cancel fixtures through `dialog_policy.py` and
   runtime confirmation flows.
2. Include mixed replies where cancel or negative language should safely
   outrank a stray affirmative marker.

Expected result:
- Confirmation handling remains closed-vocabulary-aware and safe.
- Safe precedence still favors cancel or decline when mixed cues appear.
- Confirmation prompts and outcomes remain understandable without a GUI.

### 7. Diagnostics And Privacy

1. Generate accepted, confirmed, retried, refused, and rejected command
   outcomes that depend on normalization, ambiguity, or language mismatch.
2. Inspect runtime diagnostics and metadata payloads.

Expected result:
- Metadata surfaces integrity status, substitution markers, confidence band,
  language mismatch markers, and alternative-conflict markers when relevant.
- Raw utterance content is not persisted by default.
- Decision trails remain understandable enough for field debugging.

## Suggested Automated Checks

```powershell
python -m pytest tests/unit/test_command_post_processing.py tests/unit/test_command_canonicalization.py tests/unit/test_parser.py tests/unit/test_command_confidence_policy.py tests/unit/test_command_safety_evaluation_contract.py tests/unit/test_dialog_confirmation_policy.py -q
python -m pytest tests/integration/test_command_recognition_runtime.py tests/integration/test_hybrid_command_recognition.py tests/integration/test_command_dialog_robustness.py tests/integration/test_command_confirmation_localization.py tests/integration/test_stt_privacy_diagnostics.py -q
python -m pytest tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_command_layer_quickstart.py -q
python -m compileall core tests
python -m ruff check .
```

If a scenario-specific test file does not exist yet during implementation,
create it for the missing scenario rather than dropping the scenario from the
validation sweep.

## Manual Smoke Check

1. Start the assistant in console or GUI-bridge mode with the current command
   confidence settings.
2. Speak a supported Arabic command, a supported mixed-language command, an
   unsupported near-command phrase, and a corrupted/noisy phrase.
3. Repeat with a protected command that should require confirmation.
4. Inspect the resulting runtime behavior and field-safe diagnostics.

Expected result:
- Supported commands resolve cleanly.
- Unsupported or corrupted phrases do not misexecute.
- Protected commands remain confirmation-gated.
- Diagnostics explain the major decision factors without exposing raw content.

## Success Criteria Mapping

- `SC-001`: Covered supported Arabic command fixtures resolve to the intended
  existing command identifier.
- `SC-002`: Covered bilingual and phonetic fixtures resolve with no more than
  one retry.
- `SC-003`: Protected commands never execute without explicit affirmative
  confirmation when uncertainty or corruption is present.
- `SC-004`: Covered corrupted Arabic-like and mojibake fixtures are rejected
  safely.
- `SC-005`: Normalization, ambiguity, and language-mismatch-driven decisions
  emit field-safe explanatory metadata.

## Validation Evidence (2026-04-26)

- `T020`: `python -m pytest tests/unit/test_command_post_processing.py tests/unit/test_command_canonicalization.py tests/unit/test_parser.py tests/integration/test_command_recognition_runtime.py tests/integration/test_hybrid_command_recognition.py tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_command_layer_quickstart.py -q`  
  Result: `38 passed, 2 warnings`.
- `T029`: `python -m pytest tests/unit/test_command_confidence_policy.py tests/unit/test_command_safety_evaluation_contract.py tests/unit/test_parser.py tests/unit/test_command_post_processing.py tests/integration/test_command_dialog_robustness.py tests/integration/test_command_confirmation_localization.py tests/smoke/test_command_layer_quickstart.py -q`  
  Result: `47 passed, 2 warnings`.
- `T038`: `python -m pytest tests/unit/test_command_post_processing.py tests/unit/test_parser.py tests/unit/test_command_safety_evaluation_contract.py tests/unit/test_command_confidence_policy.py tests/integration/test_command_recognition_runtime.py tests/integration/test_hybrid_command_recognition.py tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_command_layer_quickstart.py -q`  
  Result: `45 passed, 2 warnings`.
- `T045`: `python -m pytest tests/unit/test_command_recognition_contract.py tests/unit/test_command_fallback_decision_contract.py tests/integration/test_stt_privacy_diagnostics.py tests/integration/test_command_recognition_runtime.py tests/smoke/test_hybrid_command_recognition_quickstart.py -q`  
  Result: `25 passed, 2 warnings`.
- `T048`: `python -m pytest tests/unit/test_command_post_processing.py tests/unit/test_command_canonicalization.py tests/unit/test_parser.py tests/unit/test_command_confidence_policy.py tests/unit/test_command_safety_evaluation_contract.py tests/unit/test_command_recognition_contract.py tests/unit/test_command_fallback_decision_contract.py tests/unit/test_dialog_confirmation_policy.py tests/unit/test_closed_vocabulary.py -q`  
  Result: `50 passed, 2 warnings`.
- `T049`: `python -m pytest tests/integration/test_command_recognition_runtime.py tests/integration/test_hybrid_command_recognition.py tests/integration/test_command_dialog_robustness.py tests/integration/test_command_confirmation_localization.py tests/integration/test_stt_privacy_diagnostics.py tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_command_layer_quickstart.py -q`  
  Result: `39 passed, 2 warnings`.
- `T050`: `python -m compileall core tests` and `python -m ruff check .`  
  Result: compile completed and `ruff` reported `All checks passed!`.

Warnings observed in pytest runs: Python 3.12 deprecation warnings from
`speech_recognition` imports (`aifc`, `audioop`).

## Contract Reconciliation (2026-04-26)

- `normalized-command-candidate-contract.md`: validated normalized vs rejected
  candidate shapes, substitution visibility, and field-safe defaults through
  `tests/unit/test_command_post_processing.py`,
  `tests/unit/test_command_canonicalization.py`, and
  `tests/unit/test_command_recognition_contract.py`.
- `variant-mapping-rule-contract.md`: validated curated supported-phrase
  mapping boundaries and unsupported near-miss protection through
  `tests/unit/test_parser.py` and
  `tests/integration/test_hybrid_command_recognition.py`.
- `safety-decision-record-contract.md`: validated confirm/retry/refuse routing,
  stable-candidate handling, and protected-command safety through
  `tests/unit/test_command_confidence_policy.py`,
  `tests/unit/test_command_safety_evaluation_contract.py`, and
  `tests/integration/test_command_dialog_robustness.py`.
- `confirmation-dialog-safety-contract.md`: validated bilingual yes/no/cancel
  precedence and confirmation localization integrity through
  `tests/unit/test_dialog_confirmation_policy.py`,
  `tests/unit/test_closed_vocabulary.py`, and
  `tests/integration/test_command_confirmation_localization.py`.

## Privacy Audit (2026-04-26)

- Reviewed `core/assistant_runtime.py`, `core/command_post_processing.py`,
  `core/text_integrity.py`, `core/runtime_diagnostics.py`,
  `core/command_models.py`, and `settings/user_profile.json`.
- Confirmed command diagnostics and decision payloads keep
  `field_safe=true` and `raw_user_content_present=false` by default.
- Confirmed no credential material or raw utterance content is persisted in
  `settings/user_profile.json` for Phase 20 command flows.

## Validation Evidence (2026-04-28)

- `T021`: `python -m pytest tests/unit/test_command_post_processing.py tests/unit/test_command_canonicalization.py tests/unit/test_parser.py tests/integration/test_command_recognition_runtime.py tests/integration/test_hybrid_command_recognition.py tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_command_layer_quickstart.py -q`  
  Result: `38 passed, 2 warnings`.
- `T030`: `python -m pytest tests/unit/test_command_confidence_policy.py tests/unit/test_command_safety_evaluation_contract.py tests/unit/test_parser.py tests/unit/test_command_post_processing.py tests/integration/test_command_dialog_robustness.py tests/integration/test_command_confirmation_localization.py tests/smoke/test_command_layer_quickstart.py -q`  
  Result: `47 passed, 2 warnings`.
- `T039`: `python -m pytest tests/unit/test_command_post_processing.py tests/unit/test_parser.py tests/unit/test_command_safety_evaluation_contract.py tests/unit/test_command_confidence_policy.py tests/integration/test_command_recognition_runtime.py tests/integration/test_hybrid_command_recognition.py tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_command_layer_quickstart.py -q`  
  Result: `45 passed, 2 warnings`.
- `T046`: `python -m pytest tests/unit/test_command_recognition_contract.py tests/unit/test_command_fallback_decision_contract.py tests/integration/test_stt_privacy_diagnostics.py tests/integration/test_command_recognition_runtime.py tests/smoke/test_hybrid_command_recognition_quickstart.py -q`  
  Result: `25 passed, 2 warnings`.
- `T049`: `python -m pytest tests/unit/test_command_post_processing.py tests/unit/test_command_canonicalization.py tests/unit/test_parser.py tests/unit/test_command_confidence_policy.py tests/unit/test_command_safety_evaluation_contract.py tests/unit/test_command_recognition_contract.py tests/unit/test_command_fallback_decision_contract.py tests/unit/test_dialog_confirmation_policy.py tests/unit/test_closed_vocabulary.py -q`  
  Result: `50 passed, 2 warnings`.
- `T050`: `python -m pytest tests/integration/test_command_recognition_runtime.py tests/integration/test_hybrid_command_recognition.py tests/integration/test_command_dialog_robustness.py tests/integration/test_command_confirmation_localization.py tests/integration/test_stt_privacy_diagnostics.py tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_command_layer_quickstart.py -q`  
  Result: `39 passed, 2 warnings`.
- `T051`: `python -m compileall core tests` and `python -m ruff check .`  
  Result: compile completed and `ruff` reported `All checks passed!`.

Warnings observed in pytest runs: Python 3.12 deprecation warnings from
`speech_recognition` imports (`aifc`, `audioop`).

## Contract Reconciliation (2026-04-28)

- `normalized-command-candidate-contract.md`: reconciled and validated
  field-safe transcript reference keys (`source_transcript_ref`,
  `normalized_transcript_ref`) with
  `tests/unit/test_command_post_processing.py` and
  `tests/unit/test_command_recognition_contract.py`.
- `variant-mapping-rule-contract.md`: reconfirmed curated phrase boundaries
  and protected-command mapping behavior through
  `tests/unit/test_parser.py` and
  `tests/integration/test_hybrid_command_recognition.py`.
- `safety-decision-record-contract.md`: reconfirmed confirm/retry/refuse
  routing, stable-candidate handling, and protected-command safeguards through
  `tests/unit/test_command_confidence_policy.py`,
  `tests/unit/test_command_safety_evaluation_contract.py`, and
  `tests/integration/test_command_dialog_robustness.py`.
- `confirmation-dialog-safety-contract.md`: reconfirmed multilingual
  yes/no/cancel precedence and localization safety through
  `tests/unit/test_dialog_confirmation_policy.py`,
  `tests/unit/test_closed_vocabulary.py`, and
  `tests/integration/test_command_confirmation_localization.py`.

## Privacy Audit (2026-04-28)

- Reviewed `core/assistant_runtime.py`, `core/command_post_processing.py`,
  `core/text_integrity.py`, `core/runtime_diagnostics.py`,
  `core/command_models.py`, and `settings/user_profile.json`.
- Confirmed runtime diagnostics still sanitize utterance fields and enforce
  `field_safe=true` with `raw_user_content_present=false` by default.
- Confirmed no raw utterance payload or transcript persistence was added to
  `settings/user_profile.json` for Phase 20 command flows.
