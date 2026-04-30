# Quickstart: Wearable Readiness

## Goal

Validate Phase 5 wearable behavior by proving that priority-aware messaging,
interruptible bounded speech sessions, wake strategy defaults, offline safety
policy, localization integrity, and startup/standby readiness all work in
headless-first runtime flows.

## Prerequisites

1. Create and activate the project virtual environment.
2. Install dependencies from `requirements.txt`.
3. Ensure microphone and speaker access are available for runtime checks.
4. Confirm the active feature branch is `005-wearable-readiness`.
5. Keep deterministic test doubles available for provider/network-state
   simulation.

## Validation Matrix

| Scenario | Expected Result |
|---|---|
| High-priority message competes with lower-priority message | High-priority message is delivered first |
| Same-priority duplicates arrive in burst | Duplicates coalesce into one concise output within 2 seconds |
| `stop/cancel/emergency` during speaking/listening | Active session preempted within 1 second target window |
| Interrupted non-critical speech | Not auto-resumed unless explicitly re-requested |
| Network-required command while offline and not allowlisted | Safe refusal with brief next-step guidance |
| Allowlisted offline command | On-device fallback executes safely with explicit degraded signal |
| Startup from cold boot | Non-visual ready signal emitted within target window |
| 2-hour standby run | Wake responsiveness remains usable in low-power standby mode |
| Critical Arabic/English prompts | No garbled output in critical prompt checks |

## Path 1: Priority Routing and Coalescing

1. Trigger mixed-priority runtime messages in rapid sequence.
2. Verify delivery order respects `warning/error` ahead of `action confirmation`
   and `info`.
3. Trigger duplicate same-priority events within 2 seconds.
4. Confirm one concise coalesced message is spoken and logged.

## Path 2: Interruption and Session Bounds

1. Start a speaking session and issue `stop`.
2. Start a listening session and issue `cancel` and `emergency`.
3. Confirm preemption latency meets target and runtime remains responsive.
4. Force listening/speaking timeout paths and verify safe recovery outcomes.

## Path 3: Wake Strategy and Standby Behavior

1. Start runtime in standby mode with default wake policy.
2. Confirm low-power keyword wake is selected as primary mode.
3. Simulate keyword wake unavailability and verify hardware trigger fallback.
4. Confirm STT-based wake is available only in development/test composition.

## Path 4: Offline/Degraded Safety Policy

1. Simulate network loss for network-required provider actions.
2. Confirm non-allowlisted actions produce explicit safe refusal.
3. Confirm allowlisted commands use on-device fallback only.
4. Verify no risky fuzzy execution occurs in offline mode.

## Path 5: Localization Integrity

1. Run critical prompt integrity checks for Arabic and English prompt set.
2. Simulate corrupted critical prompt content.
3. Confirm runtime blocks/replaces corrupted prompt before speech output.
4. Confirm fallback prompt remains concise and understandable.

## Path 6: Startup and Non-Visual Readiness

1. Perform repeated cold starts and capture readiness timestamps.
2. Verify non-visual readiness target (`<= 8s`) is met in target percentile.
3. Run extended standby session and periodically verify wake responsiveness.
4. On hardware that supports tones/haptics, run cue-identification checks for
   key runtime states.

## Measurement Targets

| Check | Threshold |
|---|---|
| Interrupt preemption (`stop/cancel/emergency`) | <= 1.0s in >=95% of attempts |
| Same-priority duplicate coalescing | <= 2.0s in >=95% of bursts |
| Concise wearable responses | >=95% responses at <=12 spoken words |
| Offline safety behavior | 100% explicit safe guidance, 0 risky executions |
| Critical prompt integrity (AR/EN) | 100% pass, no garbled output |
| Startup non-visual readiness | <= 8.0s in >=95% of boots |
| Standby wake responsiveness | Stable through 2-hour run |
| Non-speech cue identification (supported hardware) | >=90% correct state identification |

## Suggested Validation Commands

- `python -m compileall main.py core settings tts ui tests`
- `python -m pytest tests/unit -q`
- `python -m pytest tests/integration -q`
- `python -m pytest tests/smoke -q`

If some tests are not yet present, run the available subset plus deterministic
manual checks for priority/coalescing, interruption, offline policy, and
startup readiness, then record the coverage gap in implementation notes.

## Implementation Evidence (2026-04-18)

### Automated Validation

- `python -m pytest tests/unit -q` -> `90 passed`
- `python -m pytest tests/integration -q` -> `36 passed`
- `python -m pytest tests/smoke -q` -> `26 passed`
- `python -m compileall main.py core settings tts ui tests` -> `success`

### Success-Criteria Traceability

- **SC-001 / SC-007 (concise + coalescing)**: covered by
  `tests/unit/test_wearable_priority_feedback.py` and
  `tests/smoke/test_wearable_readiness_quickstart.py`.
- **SC-002 (interrupt preemption <=1s)**: covered by
  `tests/unit/test_runtime_interrupt_preemption.py` and
  `tests/integration/test_runtime_interruptions.py` using
  `preemption_latency_ms` assertions.
- **SC-003 (offline safe behavior)**: covered by
  `tests/unit/test_offline_allowlist_policy.py`,
  `tests/integration/test_runtime_offline_behavior.py`, and
  `tests/smoke/test_wearable_readiness_quickstart.py`.
- **SC-004 (critical prompt integrity)**: covered by
  `tests/unit/test_wearable_priority_feedback.py` corrupted-catalog fallback
  check.
- **SC-005 (startup readiness + standby wake)**: covered by
  `tests/integration/test_wearable_startup_readiness.py`.
- **SC-006 (non-speech cues)**: covered by cue mapping and ready-cue emission
  checks in `tests/unit/test_wearable_priority_feedback.py` and
  `tests/integration/test_wearable_startup_readiness.py`.
