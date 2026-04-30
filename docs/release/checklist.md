# Release Checklist

## Required Readiness Items

- [ ] Offline/degraded behavior validated
- [ ] Connectivity probe events reviewed (`status`, `latency_ms`, `failure_reason`)
- [ ] Startup override reset validated (`override_mode=auto`)
- [ ] Emergency stop/cancel behavior validated
- [ ] Audio input/output permissions validated
- [ ] Crash recovery expectations validated
- [ ] Lifecycle and primary journey validation evidence attached
- [ ] Localization integrity evidence attached
- [ ] Baseline comparison evidence attached

## Localization Evidence Minimums

- [ ] Localization validation output identifies failing `prompt_key` values
- [ ] Localization validation output identifies failing `surface_id` values
- [ ] Runtime integrity metadata was reviewed for any `fallback_used=true`
- [ ] `settings/user_profile.json` was confirmed as the approved catalog source
- [ ] No critical surface resolves through embedded text or an unapproved
  binding

## Recommended Validation Commands

- `python -m pytest tests/unit/test_release_localization_integrity.py tests/integration/test_release_localization_validation.py -q`
- `python -m pytest tests/integration/test_runtime_prompt_localization.py tests/integration/test_command_confirmation_localization.py -q`
- `python -m pytest tests/unit/test_connectivity_state_policy.py tests/integration/test_runtime_offline_policy_matrix.py tests/smoke/test_offline_truth_quickstart.py -q`

## Phase 16 Pilot Voice UX Checklist

- [ ] Allowed barge-in prompts accept early answers without forced repeats
- [ ] Protected confirmations, shutdown, and destructive flows block early input
- [ ] Closed-vocabulary prompts accept approved aliases only
- [ ] Out-of-domain responses are rejected with bounded recovery
- [ ] Prompt-echo suppression does not consume retry budget by itself
- [ ] Required settings continue with safe defaults after retry exhaustion
- [ ] Unconfirmed name candidates are discarded and never persisted
- [ ] Guided-context preemption is limited to approved global safety commands
- [ ] Pilot evidence includes completion, retries, barge-ins, suppressions, rejections, and fallback/exit reason
- [ ] Pilot evidence excludes raw user utterances by default

## Phase 16 Tuning Guidance

- Tune `closed_vocabulary_retry_limit` in `settings/user_profile.json` with caution; higher values improve recovery but may increase loop risk.
- Keep onboarding prompts short and directive; longer prompts increase prompt-echo overlap.
- Expand alias sets in `core/closed_vocabulary.py` only when tests prove no unsafe overlap.
- Preserve protected preemption boundaries when adjusting turn-taking prompt classes in `core/turn_taking.py`.

## Phase 16 Validation Evidence

- Date: `2026-04-23`
- SC-004 and SC-005 command: `python -m pytest tests/unit/test_assistant_runtime.py tests/unit/test_resolver.py tests/unit/test_runtime_contract.py tests/integration/test_command_dialog_robustness.py tests/integration/test_command_recognition_runtime.py tests/integration/test_release_journey_validation.py tests/smoke/test_runtime_quickstart.py -q`
- SC-004 and SC-005 result: `81 passed, 2 warnings in 17.82s`
- Full sweep confirmation:
  `python -m pytest tests/unit/test_turn_taking.py tests/unit/test_closed_vocabulary.py tests/unit/test_dialog_confirmation_policy.py tests/unit/test_assistant_runtime.py tests/unit/test_resolver.py tests/unit/test_runtime_contract.py tests/unit/test_tts_engine_interruptions.py -q` -> `77 passed, 2 warnings in 13.07s`
  `python -m pytest tests/integration/test_command_dialog_robustness.py tests/integration/test_closed_vocabulary_stt.py tests/integration/test_command_recognition_runtime.py tests/integration/test_runtime_interruptions.py tests/integration/test_runtime_failure_paths.py tests/integration/test_gui_runtime_bridge.py tests/integration/test_release_journey_validation.py -q` -> `29 passed, 2 warnings in 4.13s`
  `python -m pytest tests/smoke/test_runtime_quickstart.py -q` -> `14 passed, 2 warnings in 5.40s`
  `python -m compileall core tests` -> success
  `python -m ruff check .` -> `All checks passed!`
