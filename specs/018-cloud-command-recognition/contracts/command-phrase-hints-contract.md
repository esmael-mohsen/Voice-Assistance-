# Command Phrase Hints Contract

## Purpose

Define the command-specific phrase hint inventory used by cloud command
recognition and strict command fallback.

## Output Shape

```json
{
  "phrase_hint_set_id": "command.default",
  "mode": "command",
  "language_scope": "bilingual",
  "source_catalogs": [
    "safety_critical_commands",
    "core.parser.COMMAND_CATALOG",
    "assistive_phrases",
    "arabic_variants",
    "bilingual_variants",
    "phonetic_variants",
    "stt_mistake_variants"
  ],
  "priority_order": [
    "protected_safety",
    "parser_catalog",
    "assistive_wearable",
    "arabic",
    "bilingual_phonetic",
    "common_stt_mistakes"
  ],
  "variant_types": ["canonical", "english", "arabic", "bilingual", "phonetic", "stt_mistake"],
  "max_cloud_phrases": 72,
  "max_strict_grammar_phrases": 220,
  "phrases": [
    "stop system",
    "detect obstacle",
    "recognize face",
    "read text"
  ],
  "raw_user_content_present": false
}
```

## Required Command Families

- Stop/cancel/system stop.
- Obstacle detection.
- Face recognition.
- Emotion recognition.
- Money detection.
- Text reading.
- Help and emergency mode.
- Navigation mode.
- Settings-sensitive or reset commands where supported.

## Rules

- Generated phrase order must be deterministic for identical source catalogs.
- Duplicates and empty phrases must be removed after normalization.
- Protected and safety-critical phrases must remain high priority when caps
  are reached.
- Raw user utterances must not be included by default.
- English, Arabic, bilingual, phonetic, and common STT mistake variants should
  be curated and auditable.
- Cloud hint caps and strict fallback grammar caps may differ but must be
  documented and tested.
- Phrase hints bias recognition only; they do not authorize execution.

## Validation Expectations

- Exact-output or stable-order tests cover command mode.
- Tests assert required command families are represented.
- Tests assert Arabic and bilingual variants for high-value assistive commands.
- Tests assert cap behavior preserves priority order.
- Tests assert raw user content is absent by default.
