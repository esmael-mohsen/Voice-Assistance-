# Phase 14 Audio Fixture Registry

This folder contains curated offline fixture references for Phase 14
qualification. Runtime telemetry remains metadata-first and must not store live
user audio.

## Qualification Profiles

- `default`: Full local-first command stack with optional rescue enabled.
- `simplified`: Raspberry Pi 4 fallback profile with expensive enhancements
  demoted when needed.

## Curated Fixture Manifest (Metadata)

| Fixture ID | Scenario | Profile | Qualification | Expected |
|-----------|----------|---------|---------------|----------|
| `clip_start_en` | clipped_start | `command.default` | `default` | `start obstacle detection` |
| `clip_end_ar` | clipped_end | `command.default` | `default` | `شغل العوائق` |
| `bilingual_mix_1` | bilingual | `command.default` | `default` | `switch to english` |
| `closed_choice_yes_no` | closed_choice | `confirmation.default` | `simplified` | `yes` |
| `disagreement_sample_1` | disagreement | `command.default` | `default` | confirmation-required |

## Recommended Local-First Stack

- Capture: `SpeechRecognition` microphone input (16 kHz mono target)
- Local first recognizer: `Vosk`
- Bounded rescue: legacy compatibility path only on uncertainty
- Canonicalization: `core.command_post_processing`

## Raspberry Pi 4 Tradeoffs

- Keep rescue bounded and optional.
- Prefer `simplified` profile if latency or CPU budget is exceeded.
- Demote optional enhancements explicitly in release evidence.
