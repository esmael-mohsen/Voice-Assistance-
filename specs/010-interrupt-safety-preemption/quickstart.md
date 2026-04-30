# Quickstart: Interrupt Safety and TTS Preemption

## Goal

Validate that approved Arabic and English interrupt phrases can stop active
speech quickly, interrupt safe-to-cancel in-flight work, and emit measurable
recovery outcomes without leaving the runtime in an unsafe state.

## Preconditions

1. Use the project virtual environment and repository root.
2. Run validation in console or headless runtime mode as the reference path.
3. Use a runtime configuration with audible speech enabled and critical prompt
   catalog entries available for interrupt acknowledgement.
4. Reset runtime session state between scenarios so prior interrupts do not
   leak into the next validation path.
5. Use the canonical Phase 10 interrupt vocabulary for validation: English
   `stop`, `cancel`, `stop now`; Arabic `قف`, `توقف`, `إلغاء`.

## Validation Paths

### 1. English Interrupt During Active Speech

1. Start a spoken response long enough to observe interruption.
2. Say `stop` or `cancel` while speech is actively playing.
3. Verify the assistant stops the audio before the original message fully
   completes.
4. Verify the runtime emits a recovery outcome and returns to standby.

Expected outcome:
- Audible speech stops quickly.
- A short acknowledgement is emitted.
- No follow-up speech from the interrupted response resumes afterward.

### 2. Arabic Interrupt During Active Speech

1. Start a spoken response while the runtime language is Arabic.
2. Say an approved Arabic interrupt phrase such as `وقف` or another approved
   variant from the interrupt vocabulary.
3. Verify the interrupt is accepted even if the active prompt language and the
   spoken safety phrase differ across the validation matrix.
4. Confirm the acknowledgement text remains readable and catalog-backed.

Expected outcome:
- Arabic safety phrases interrupt speech just as reliably as English phrases.
- Prompt integrity remains valid or falls back safely through approved prompt
  surfaces.

### 3. Interrupt While Work Is In Flight

1. Start a command or capability flow that produces spoken output and active
   work.
2. Interrupt during the speaking or thinking phase.
3. Verify the runtime suppresses follow-on work from the interrupted flow.
4. Repeat with a near-complete or non-reversible operation and confirm the
   result is reported as best-effort instead of a false full cancellation.

Expected outcome:
- Safe-to-cancel work is cancelled promptly.
- Non-reversible work still stops speech and reports the safest truthful
  outcome.
- The runtime ends in a stable state instead of hanging between modes.

### 4. Latency and Observability Checks

1. Run the interrupt-focused automated suite.
2. Inspect emitted recovery outcomes for `interrupt_signal_type`,
   `completion_status`, and `preemption_latency_ms`.
3. Validate that accepted interrupt latency stays within the release target.

Expected outcome:
- Every accepted interrupt path emits a measurable latency value.
- At least 95% of validated interrupt paths stop audible speech within 500 ms.
- No accepted interrupt path exceeds 1 second.

### 5. Moderate-Load Interrupt Validation

1. Start one spoken response that lasts at least 5 seconds.
2. While that response is active, run one concurrent thinking or safe-to-cancel
   capability operation in the same runtime session with structured logging
   enabled.
3. Interrupt using one English and one Arabic phrase from the canonical
   vocabulary in separate runs.
4. Confirm the recorded latency and final recovery state remain within the
   release target for both runs.

Expected outcome:
- The defined moderate-load profile remains reproducible across runs.
- Accepted interrupts still stop local speech within the approved latency
  bounds.
- Recovery outcomes stay deterministic and do not leave follow-on speech
  running.

### 6. Weak-Network / Provider-Stall Validation

1. Run a speech or capability path that depends on a network-backed provider.
2. Simulate provider delay, timeout, or temporary unavailability while local
   speech is active.
3. Issue a canonical interrupt phrase during the stalled or delayed path.
4. Verify local speech stops immediately, follow-on speech is suppressed, and
   the emitted outcome reports degraded or best-effort recovery truthfully.

Expected outcome:
- Local interrupt responsiveness does not depend on the remote provider
  finishing cleanly.
- The runtime returns to a safe state even if remote work may still be
  completing.
- Structured outcomes make the degraded condition visible to validation.

### 7. Suggested Validation Commands

- `python -m pytest tests/unit/test_runtime_interrupt_preemption.py -q`
- `python -m pytest tests/integration/test_runtime_interruptions.py tests/integration/test_runtime_prompt_localization.py -q`
- `python -m pytest tests/smoke/test_wearable_readiness_quickstart.py -q`
- `python -m compileall core tests`

## Operator Notes

- Interrupt behavior is safety-first and should remain globally available in
  Arabic and English.
- Accepted interrupts must preempt audible speech, not merely report an
  interruption after playback already finished.
- Best-effort cancellation is valid when an operation cannot be fully reversed,
  but post-interrupt follow-on speech from the interrupted flow must still be
  suppressed.

## Validation Evidence

- US1 validation (`tests/unit/test_runtime_interrupt_preemption.py`, `tests/unit/test_tts_engine_interruptions.py`, `tests/integration/test_runtime_interruptions.py`, `tests/integration/test_runtime_modes.py`, `tests/smoke/test_interrupt_safety_quickstart.py`, `tests/smoke/test_wearable_readiness_quickstart.py`): `24 passed`.
- US2 validation (`tests/unit/test_assistant_runtime.py`, `tests/unit/test_runtime_interrupt_preemption.py`, `tests/integration/test_runtime_interruptions.py`, `tests/integration/test_capability_runtime.py`, `tests/smoke/test_interrupt_safety_quickstart.py`, `tests/smoke/test_runtime_quickstart.py`): `45 passed`.
- US3 validation (`tests/unit/test_runtime_contract.py`, `tests/unit/test_release_latency_baselines.py`, `tests/integration/test_runtime_interruptions.py`, `tests/integration/test_release_latency_pipeline.py`, `tests/integration/test_runtime_prompt_localization.py`, `tests/smoke/test_interrupt_safety_quickstart.py`): `19 passed`.
- Full Phase 10 sweep: unit `40 passed`, integration `21 passed`, smoke `17 passed`, `python -m compileall core tests` succeeded.
