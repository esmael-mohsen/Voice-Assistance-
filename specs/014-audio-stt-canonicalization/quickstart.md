# Quickstart: Audio Front-End, Hybrid STT, and Command Canonicalization

## Goal

Validate that the assistant captures full spoken commands more reliably,
prefers a practical local-first recognition path, uses rescue recognition only
when uncertainty requires it, normalizes noisy bilingual transcripts into the
supported command inventory, and publishes truthful Raspberry Pi 4
qualification evidence without storing live user audio in default artifacts.

## Preconditions

1. Use the project virtual environment and repository root.
2. Ensure local Vosk models and any compatibility fallback recognizers are
   available for the languages under test.
3. Keep curated offline benchmark fixtures available for noisy, clipped,
   bilingual, and closed-vocabulary scenarios.
4. Validate headless console mode first, then use GUI checks only as a parity
   pass.
5. Keep the active settings snapshot aligned with the qualification profile you
   want to validate (`default` or `simplified`).

## Validation Paths

### 1. Capture Profiles and Clipping Recovery

1. Exercise command capture with soft starts, short pauses, and quiet endings
   using the command profile.
2. Confirm the assistant emits capture metadata including speech start and end
   timing, utterance duration, and clipping hints.
3. Trigger a likely clipped utterance and verify the assistant performs at most
   one short relisten with a shorter reprompt.

Expected outcome:
- Command capture preserves full utterances more often than the pre-phase
  baseline.
- Capture metadata explains whether clipping or weak endpoint quality was
  suspected.
- The assistant does not loop on repeated relistens.

### 2. Local-First Command Recognition

1. Exercise representative supported Arabic and English commands that should
   resolve clearly through the local-first path.
2. Confirm the runtime records the local-first recognition path, a usable
   canonical command, and no unnecessary rescue step.
3. Verify the command reaches the parser and dispatcher with canonicalized
   text.

Expected outcome:
- Clear supported commands resolve locally without rescue latency.
- The runtime records which profile and dictionary mode were active.
- Canonicalized parser input stays closer to the supported command inventory
  than the raw transcript.

### 3. Rescue Recognition and Disagreement Handling

1. Exercise clipped, weak, or contradictory samples that should trigger the
   rescue path.
2. Confirm rescue is invoked only after the local-first result is judged
   uncertain or contradictory.
3. Exercise a case where local-first and rescue results map to different
   canonical commands.

Expected outcome:
- Rescue recognition stays bounded and does not become the default path.
- Disagreement between recognition paths never auto-executes a risky outcome.
- Non-protected disagreement flows require confirmation or end in safe refusal.

### 4. Closed-Vocabulary and Dictionary-Biased Flows

1. Exercise onboarding language, onboarding voice, onboarding speed, yes or no,
   and cancel flows using constrained vocabularies.
2. Confirm recognition stays biased to the valid options for the active mode.
3. Exercise out-of-set speech and confirm the assistant gives one short
   constrained retry, then returns to the prior safe step.

Expected outcome:
- Closed-vocabulary accuracy is materially better than unrestricted decoding.
- The assistant does not widen constrained flows into arbitrary free text after
  a failed answer.
- Confusion pairs such as language or gender choices remain safely bounded.

### 5. Bilingual Canonicalization

1. Run fixtures containing Arabic-English switching, known substitutions, and
   command aliases.
2. Verify canonicalization normalizes the transcript before parser matching.
3. Confirm mixed-language commands remain eligible for canonical mapping when
   enough supported tokens are present.

Expected outcome:
- Common Arabic and English substitutions are repaired consistently.
- Mixed-language commands map to stable parser-ready phrases when safe.
- Canonicalization does not bypass risky-command safeguards.

### 6. Simplified Mode and Degraded Truthfulness

1. Disable rescue recognition or optional enhancements to simulate the
   simplified profile.
2. Exercise representative supported commands and a constrained vocabulary flow.
3. Confirm the assistant continues using capture profiles, preprocessing,
   canonicalization, and dictionary bias while stating truthfully that the
   stronger rescue path is not active.

Expected outcome:
- Simplified mode remains usable and predictable for supported commands.
- Degraded behavior is explicit and truthful.
- No UI-only logic is required to recover or explain degraded speech behavior.

### 7. Raspberry Pi 4 Qualification Evidence

1. Run the maintained benchmark set against the `default` qualification
   profile.
2. Measure capture completeness, command-resolution accuracy,
   closed-vocabulary accuracy, canonicalization accuracy, and spoken-response
   latency.
3. If any optional enhancement breaches the declared Pi 4 budget, rerun with
   the `simplified` profile and publish the demotion decision.

Expected outcome:
- Qualification evidence names the supported profile used for the run.
- Any demoted enhancement is listed explicitly instead of hidden.
- Default artifacts contain metrics and flags only; curated offline fixtures
  remain the only place where audio samples are stored.

## Suggested Validation Commands

- `python -m pytest tests/unit/test_audio_preprocessing.py tests/unit/test_capture_profiles.py tests/unit/test_command_canonicalization.py -q`
- `python -m pytest tests/integration/test_command_capture_endpointing.py tests/integration/test_hybrid_command_recognition.py tests/integration/test_closed_vocabulary_stt.py -q`
- `python -m pytest tests/integration/test_runtime_modes.py tests/integration/test_runtime_offline_behavior.py tests/integration/test_gui_runtime_bridge.py -q`
- `python -m pytest tests/smoke/test_audio_frontend_quickstart.py tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_runtime_quickstart.py -q`
- `python -m compileall core tests`
- `ruff check .`

## Operator Notes

- Local-first remains the baseline behavior; rescue recognition is evidence of
  uncertainty, not the default command path.
- Default telemetry and qualification artifacts must remain metadata-first and
  must not include live user audio or raw transcripts.
- Closed-vocabulary retries stay bounded to one short constrained retry before
  returning to the prior safe step.
- Headless console behavior remains the reference wearable flow; GUI checks are
  for parity, not a separate speech policy.
- Qualification runs must publish both the supported profile and any optional
  enhancement that was disabled to stay within Raspberry Pi 4 limits.

## Success Criteria Evidence Ledger

- `SC-001` Capture completeness with bounded relisten: pending
- `SC-002` Local-first command resolution reliability: pending
- `SC-003` Rescue escalation only on uncertainty: pending
- `SC-004` Closed-vocabulary constrained-flow accuracy: pending
- `SC-005` Qualification profile selection (`default` vs `simplified`): pending
- `SC-006` Optional-enhancement demotion transparency: pending
- `SC-007` Field-safe telemetry defaults (no raw user audio): pending

## Qualification Command Log

- `python -m pytest tests/unit/test_audio_preprocessing.py tests/unit/test_capture_profiles.py tests/unit/test_capture_quality_metadata_contract.py tests/unit/test_hybrid_command_recognition_contract.py tests/unit/test_command_canonicalization.py -q`
- `python -m pytest tests/integration/test_command_capture_endpointing.py tests/integration/test_hybrid_command_recognition.py tests/integration/test_closed_vocabulary_stt.py tests/integration/test_runtime_modes.py tests/integration/test_runtime_offline_behavior.py tests/integration/test_gui_runtime_bridge.py -q`
- `python -m pytest tests/smoke/test_audio_frontend_quickstart.py tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_runtime_quickstart.py -q`
