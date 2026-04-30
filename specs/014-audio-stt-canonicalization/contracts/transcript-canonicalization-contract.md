# Transcript Canonicalization Contract

## Purpose

Define the normalized transcript payload produced after transcript repair,
dictionary filtering, and bilingual canonicalization, before parser matching.

## Output Shape

```json
{
  "source_transcript": "reed txt",
  "normalized_transcript": "read text",
  "canonical_command_text": "read text",
  "substitution_ids": [
    "en.read_text.reed_to_read",
    "en.read_text.txt_to_text"
  ],
  "language_hints": [
    "en-US"
  ],
  "dictionary_mode": "command_inventory",
  "closed_vocabulary_id": null,
  "confusion_pair_id": null,
  "ambiguity_flags": [],
  "canonicalization_status": "normalized"
}
```

## Rules

- `canonicalization_status` must be one of `unchanged`, `normalized`,
  `constrained_retry`, or `rejected`.
- Runtime compatibility note: internal model field name is
  `post_processing_status`; emitted payloads include
  `canonicalization_status` alias.
- `canonical_command_text` must be populated for `unchanged` and `normalized`
  outcomes.
- `closed_vocabulary_id` is required when `dictionary_mode=closed_choice`.
- `constrained_retry` is allowed only for closed-vocabulary or similarly
  constrained modes.
- `ambiguity_flags` must explain why the runtime cannot map the result safely.
- `confusion_pair_id` must reference a known confusion pair when present.

## Required Observability Fields

- `source_transcript`
- `normalized_transcript`
- `canonical_command_text`
- `substitution_ids`
- `language_hints`
- `dictionary_mode`
- `closed_vocabulary_id`
- `confusion_pair_id`
- `ambiguity_flags`
- `canonicalization_status`

## Validation Expectations

- Unit coverage for Arabic normalization, English cleanup, bilingual alias
  handling, and constrained-mode filtering.
- Integration coverage proving parser inputs come from canonicalized text
  rather than raw transcripts.
- Regression coverage for confusion pairs and out-of-set closed-vocabulary
  answers.
