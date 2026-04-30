# voice_assistant Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-28

## Active Technologies
- Local JSON profile at `settings/user_profile.json` with persisted (002-speakkit-speech-adapter)
- Python 3.12.4 + SpeechRecognition, rapidfuzz, edge-tts, playsound, customtkinter, SpeakKit SDK integration (new adapter target) (002-speakkit-speech-adapter)
- Local JSON profile at `settings/user_profile.json` with persisted speech-provider selection and existing runtime settings (002-speakkit-speech-adapter)
- Python 3.12.4 + `rapidfuzz` for matching, `pytest` for regression (003-command-layer-hardening)
- In-memory command session context for follow-up and confirmation (003-command-layer-hardening)
- Python 3.12.4 + existing `core.assistant_runtime`, `core.dispatcher`, `core.resolver`, `core.command_models`, `pytest`, and standard-library concurrency for bounded capability execution (004-capability-refactor)
- In-memory capability registry, timeout policy metadata, and runtime capability status snapshots with no new persisted datastore (004-capability-refactor)
- Python 3.12.4 + existing runtime stack in `core/assistant_runtime.py`, `core/speech/*`, `core/stt.py`, `tts/tts_engine.py`, and `pytest` validation for wearable runtime behavior (005-wearable-readiness)
- Existing profile JSON at `settings/user_profile.json` with persisted runtime/speech-provider state and in-memory wearable policy state (005-wearable-readiness)
- Python 3.12.4 + existing runtime stack (`SpeechRecognition`, `rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`) plus release validation tooling with `pytest` and `ruff` (006-quality-gates-release)
- Local repository files (tests, docs, release artifacts) and `settings/user_profile.json` for runtime settings continuity (006-quality-gates-release)
- Python 3.12.4 + existing runtime stack (`SpeechRecognition`, `rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`), `core/release_localization.py`, and `pytest` coverage for prompt-catalog normalization and critical-surface validation (007-localization-prompt-hardening)
- `settings/user_profile.json` as the runtime baseline critical prompt catalog with seeded emergency fallbacks and repository-hosted docs/tests artifacts (007-localization-prompt-hardening)
- `settings/user_profile.json` for persisted user preferences, (008-offline-policy-alignment)
- No new persisted datastore; dialog vocabulary and temporary (009-confirmation-command-robustness)
- No new persisted datastore; interrupt vocabulary, playback (010-interrupt-safety-preemption)
- Existing persisted runtime profile in `settings/user_profile.json` (010-interrupt-safety-preemption)
- Repository-hosted release artifacts under `artifacts/<run-id>/`, (012-field-diagnostics-release)
- Existing persisted profile in `settings/user_profile.json` for (013-hybrid-command-recognition)
- Python 3.12.4 + existing runtime stack (`SpeechRecognition`, `rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`), current dialog runtime modules, and `pytest` validation for guided voice UX (017-voice-ux-guardrails)
- Existing persisted runtime profile and prompt catalog in `settings/user_profile.json` plus local pilot UX evidence under `artifacts/<run-id>/` (017-voice-ux-guardrails)
- Python 3.12.4 + existing runtime stack (`SpeechRecognition`, `rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`, Vosk when installed), optional `google-cloud-speech` for Google Cloud STT foundation, and `pytest`/`ruff` validation (018-google-cloud-stt-foundation)
- Existing local JSON profile at `settings/user_profile.json` for runtime settings continuity; Google credential material stays outside the profile and default logs/artifacts avoid raw utterances (018-google-cloud-stt-foundation)
- Python 3.12.4 + existing runtime stack (`SpeechRecognition`, `rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`), Phase 17 optional Google Cloud STT boundary, strict Vosk fallback, deterministic command phrase hints, existing parser/confidence policy, and `pytest`/`ruff` validation (019-cloud-command-recognition)
- No new persisted datastore; existing `settings/user_profile.json` remains settings-only, cloud rollout stays env/config-driven, and default diagnostics avoid raw utterances/credentials (019-cloud-command-recognition)
- Python 3.12.4 + Existing runtime stack (`SpeechRecognition`, `rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`), optional Google Cloud Speech boundary in `core/speech/google_cloud_stt.py`, Vosk strict fallback when installed, deterministic hint generation in `core/speech/phrase_hints.py`, wake scoring in `core/wake_word.py`, and `pytest`/`ruff` validation (021-cloud-primary-wake)
- No new persisted datastore; `settings/user_profile.json` remains settings-only, rollout controls stay environment/config driven, standby wake attempt state stays in-memory, and diagnostics remain field-safe metadata with no raw utterance retention by default (021-cloud-primary-wake)
- Python 3.12.4 + existing runtime stack (`SpeechRecognition`, `rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`), optional Google Cloud STT boundary in `core/speech/google_cloud_stt.py`, strict Vosk fallback in `core/stt.py`, deterministic command post-processing in `core/command_post_processing.py`, integrity checks in `core/text_integrity.py`, dialog safety helpers in `core/dialog_policy.py`, and `pytest`/`ruff` validation (022-arabic-command-safety)
- No new persisted datastore; `settings/user_profile.json` remains settings-only, curated supported-variant inventories stay repo-hosted, and diagnostics remain field-safe metadata with no raw utterance retention by default (022-arabic-command-safety)
- Python 3.12.4 + existing runtime stack (`SpeechRecognition`, `rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`), optional Google Cloud STT boundary in `core/speech/google_cloud_stt.py`, strict Vosk fallback in `core/stt.py`, release telemetry helpers in `core/release_metrics.py`, field-safe diagnostics in `core/runtime_diagnostics.py`, release gates in `core/release_gates.py` and `core/release_models.py`, and `pytest`/`ruff` validation (023-stt-rollout-observability)
- No new persisted datastore; field-safe STT events, per-run rollups, release summaries, Pi 4 evidence, and PocketSphinx decommission evidence stay in local release artifacts with existing 180-day retention and no raw audio or raw utterance retention by default (023-stt-rollout-observability)

- Python 3.12.4 + SpeechRecognition, rapidfuzz, edge-tts, playsound, (001-runtime-extraction)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.12.4: Follow standard conventions

## Recent Changes
- 023-stt-rollout-observability: Added Python 3.12.4 + existing runtime stack, cloud-primary STT observability, rollout gates, field-safe telemetry contracts, Pi 4 qualification evidence, PocketSphinx decommission evidence, and `pytest`/`ruff` validation
- 022-arabic-command-safety: Added Python 3.12.4 + existing runtime stack (`SpeechRecognition`, `rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`), optional Google Cloud STT boundary in `core/speech/google_cloud_stt.py`, strict Vosk fallback in `core/stt.py`, deterministic command post-processing in `core/command_post_processing.py`, integrity checks in `core/text_integrity.py`, dialog safety helpers in `core/dialog_policy.py`, and `pytest`/`ruff` validation
- 021-cloud-primary-wake: Added Python 3.12.4 + Existing runtime stack (`SpeechRecognition`, `rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`), optional Google Cloud Speech boundary in `core/speech/google_cloud_stt.py`, Vosk strict fallback when installed, deterministic hint generation in `core/speech/phrase_hints.py`, wake scoring in `core/wake_word.py`, and `pytest`/`ruff` validation


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
