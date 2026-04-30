# Research: Google Cloud STT Foundation and Strict Fallback Contracts

## Decision: Use the official Google Cloud Speech client behind an optional local adapter

- **Decision**: Add `core/speech/google_cloud_stt.py` as the only module that
  imports and owns `google-cloud-speech` / `google.cloud.speech_v2.SpeechClient`
  behavior, with optional import handling so startup and tests continue without
  the package or credentials.
- **Rationale**: Google documents `google-cloud-speech` as the Python client
  library package and shows `speech_v2.SpeechClient` for current Speech-to-Text
  v2 recognizer flows. Keeping this in a dedicated adapter satisfies the
  project's replaceable speech-interface principle and prevents cloud behavior
  from leaking into `AssistantRuntime`.
- **Alternatives considered**:
  - Continue using `speech_recognition.recognize_google()`: rejected because it
    is a weak fallback path and does not provide the explicit client,
    credentials, timeout, retry, failure-code, or candidate control needed for
    production STT.
  - Register Google Cloud as a new provider ID immediately: rejected because
    Phase 17 explicitly preserves existing provider IDs and only introduces the
    cloud STT foundation behind current runtime contracts.
- **References**:
  - Google Cloud Python Speech client installation:
    https://docs.cloud.google.com/python/docs/reference/speech/latest
  - Google Cloud Speech-to-Text recognizers and `SpeechClient` examples:
    https://docs.cloud.google.com/speech-to-text/docs/recognizers

## Decision: Model cloud results as structured candidates before converting to runtime results

- **Decision**: Return internal structured cloud candidates that carry source,
  transcript, confidence, alternatives, selected language, detected language,
  latency, status, and stable failure reason before adapting successful command
  turns to `CommandRecognitionResult`.
- **Rationale**: `CommandRecognitionResult` is already the runtime-facing
  contract, but Phase 17 needs richer provider failure and alternative
  metadata. A local cloud-candidate contract lets tests validate provider
  behavior without changing the public runtime flow.
- **Alternatives considered**:
  - Return plain strings from the cloud adapter: rejected because it would lose
    confidence, alternatives, language, and failure-code detail.
  - Replace `CommandRecognitionResult`: rejected because downstream confidence,
    rescue, parser, resolver, and dispatcher behavior already depend on it.

## Decision: Keep rollout conservative with independent feature flags

- **Decision**: Default `EGB_STT_CLOUD_PRIMARY_ENABLED=0`,
  `EGB_STT_STRICT_VOSK_FALLBACK_ENABLED=0`, and
  `EGB_STT_ENABLE_SPHINX_COMPAT=0`, while exposing
  `EGB_STT_CLOUD_TIMEOUT_S` defaulting to 3 seconds and
  `EGB_STT_CLOUD_MAX_ALTERNATIVES` for candidate breadth.
- **Rationale**: This matches the clarified spec: cloud recognition and strict
  fallback must be independently reversible, and PocketSphinx must not remain
  in the default accuracy path.
- **Alternatives considered**:
  - Enable cloud primary by default after dependency installation: rejected
    because credentials/network availability varies and no-credential startup
    must remain safe.
  - Tie strict Vosk fallback enablement to cloud primary: rejected because
    fallback hardening should be testable and rollable independently.

## Decision: Bound cloud recognition with explicit timeout and one transient retry

- **Decision**: Use a 3-second default cloud timeout and at most one retry for
  transient cloud failures inside the existing listen window.
- **Rationale**: Assistive command turns must not hang, and the clarification
  explicitly sets this bound. Google client calls support timeout parameters;
  the adapter can map timeout and retry failures into stable reason codes.
- **Alternatives considered**:
  - No retry: rejected because a single transient network hiccup would degrade
    too aggressively.
  - Multiple retries or long timeouts: rejected because it would exceed the
    voice UX latency budget and make wearable interactions feel stuck.

## Decision: Generate phrase hints deterministically from approved inventories

- **Decision**: Add `core/speech/phrase_hints.py` to produce wake, command,
  confirmation, and onboarding phrase hint sets from `COMMAND_CATALOG`, closed
  vocabulary contexts, canonical wake aliases, curated assistive wearable
  phrases, safety-critical commands, and approved English/Arabic/bilingual,
  phonetic, and common STT-mistake variants.
- **Rationale**: Deterministic generation makes exact-output tests possible and
  avoids building hints from raw user utterances or runtime logs.
- **Alternatives considered**:
  - Maintain provider-specific hint lists manually in the cloud adapter:
    rejected because it would drift from parser and dialog inventories.
  - Learn hints from captured user transcripts: rejected because default
    artifacts must remain field-safe and avoid raw utterance retention.

## Decision: Treat Vosk fallback as strict mode-specific decoding

- **Decision**: Define explicit strict fallback modes:
  `wake_grammar`, `command_inventory`, and `closed_choice`. In these modes, a
  Vosk result is usable only when it matches the active grammar/inventory. A
  no-match returns no usable transcript and lets existing recovery decide the
  next prompt.
- **Rationale**: The current Vosk grammar is a helpful bias, but Phase 17 needs
  a contract that prevents arbitrary free-form command text in production
  fallback decisions.
- **Alternatives considered**:
  - Keep Vosk as grammar-biased but still free-form: rejected because weak
    fallback candidates can become unsafe commands.
  - Remove Vosk: rejected because the phase explicitly keeps Vosk as the
    strict local fallback.

## Decision: Remove PocketSphinx from default accuracy decisions

- **Decision**: Keep PocketSphinx code only behind
  `EGB_STT_ENABLE_SPHINX_COMPAT=1` for debugging/compatibility, and exclude
  it from normal wake and command candidate ranking.
- **Rationale**: Phase 17 requires PocketSphinx to stop competing with cloud
  and strict Vosk recognition in production decisions.
- **Alternatives considered**:
  - Keep PocketSphinx after Vosk when cloud fails: rejected because the
    clarified fallback contract requires no unrestricted local fallthrough when
    strict Vosk is disabled or cannot match.
  - Delete PocketSphinx immediately: rejected because compatibility/debugging
    paths may still help during transition and are safely gated.

## Decision: Report detected language as metadata only

- **Decision**: Preserve selected profile language as authoritative and expose
  cloud-detected language only as candidate/result metadata unless the user
  explicitly changes language settings.
- **Rationale**: This prevents cloud language detection from silently changing
  STT, prompt, or TTS behavior mid-session.
- **Alternatives considered**:
  - Auto-switch profile language on detected mismatch: rejected because a
    mixed Arabic/English utterance could accidentally change settings.
  - Ignore detected language entirely: rejected because metadata helps
    diagnostics and future confidence policy.

## Decision: Keep credentials and raw utterances out of persisted project artifacts by default

- **Decision**: Use environment/application-default credential discovery at
  runtime, never copy credential material into `settings/user_profile.json`,
  logs, or release artifacts, and keep phrase-hint/diagnostic artifacts
  metadata-only by default.
- **Rationale**: The spec and constitution both require field-safe observability
  and no raw utterance retention by default.
- **Alternatives considered**:
  - Store credential paths or JSON snippets in the profile: rejected because
    the profile is a user settings artifact and should not become a secret
    store.
  - Persist raw transcripts for easier debugging: rejected because it conflicts
    with privacy and field-safety requirements.
