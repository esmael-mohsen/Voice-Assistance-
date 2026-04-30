# Phrase Hints Contract

## Purpose

Define deterministic phrase hint sets used by cloud recognition and strict Vosk
fallback modes.

## Output Shape

```json
{
  "phrase_hint_set_id": "command.default",
  "mode": "command",
  "language_scope": "bilingual",
  "source_catalogs": [
    "core.parser.COMMAND_CATALOG",
    "core.closed_vocabulary",
    "wake_aliases",
    "assistive_phrases",
    "safety_critical_commands"
  ],
  "variant_types": ["canonical", "english", "arabic", "bilingual", "phonetic", "stt_mistake"],
  "phrases": [
    "detect obstacle",
    "recognize face",
    "stop system"
  ],
  "raw_user_content_present": false
}
```

## Modes

- `wake`
- `command`
- `confirmation`
- `onboarding`

## Rules

- Generated phrase order must be deterministic for identical source catalogs.
- Duplicate and empty phrases must be removed after normalization.
- Hints must be sourced only from approved static catalogs and curated variants
  by default.
- `raw_user_content_present` must be `false` for default outputs.
- `confirmation` and `onboarding` modes must include closed-vocabulary aliases
  for the active context.
- `command` mode must include parser catalog phrases and curated assistive
  wearable phrases.
- `wake` mode must include canonical wake aliases and common recognition
  variants.
- Implementations must preserve stable insertion ordering after deduplication
  so repeated runs yield identical phrase arrays.

## Validation Expectations

- Exact-output unit tests cover all modes.
- Tests assert required Arabic, English, bilingual, phonetic, and
  misrecognition variants for relevant modes.
- Tests assert no raw utterance-derived phrases are included by default.
