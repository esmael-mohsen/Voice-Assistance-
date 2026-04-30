# Wake Phrase Hints Contract

## Purpose

Define the bounded deterministic wake hint inventory used for cloud-primary
wake recognition and strict local wake grammar generation.

## Output Shape

```json
{
  "phrase_hint_set_id": "wake.default",
  "mode": "wake",
  "language_scope": "bilingual",
  "source_catalogs": ["canonical_wake_aliases", "approved_safe_variants"],
  "variant_types": ["canonical", "english", "arabic", "bilingual", "phonetic", "stt_mistake"],
  "max_cloud_phrases": 24,
  "max_strict_grammar_phrases": 32,
  "phrases": ["hi egb", "hey egb", "marhaba", "مرحبا", "hi agency", "hi hgb"],
  "raw_user_content_present": false
}
```

## Rules

- Hint generation must be deterministic for identical source inputs.
- Canonical wake aliases must always remain in the generated set.
- Empty phrases and duplicates must be removed after normalization.
- The cloud wake hint inventory must remain within `max_cloud_phrases`.
- The strict wake grammar inventory must remain within
  `max_strict_grammar_phrases`.
- All phrases must come from the approved wake alias catalog; raw user
  utterance history is not allowed by default.

## Validation Expectations

- Unit tests verify deterministic ordering, deduplication, and bounded caps.
- Unit tests verify canonical, Arabic, bilingual, phonetic, and safe STT-
  mistake entries remain present.
- Integration tests verify generated wake hints align with strict fallback
  grammar inputs.
