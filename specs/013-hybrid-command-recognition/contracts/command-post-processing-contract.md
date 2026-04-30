# Command Post-Processing Contract

## Purpose

Define the normalized command payload produced after transcript repair and
canonicalization, before parser matching.

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
  "ambiguity_flags": [],
  "post_processing_status": "normalized"
}
```

## Rules

- `normalized_transcript` must always be present when
  `post_processing_status` is `normalized` or `unchanged`.
- `canonical_command_text` must be the text handed to the parser for intent
  matching.
- `substitution_ids` may be empty, but when present they must reference known
  normalization or substitution rules.
- `ambiguity_flags` must be populated when post-processing cannot reduce the
  transcript to one safe parser-ready interpretation.
- Typical ambiguity flags include `conflicting_alternatives` and
  `mixed_language_connector`.
- `post_processing_status=rejected` is allowed only when the transcript cannot
  be safely normalized into a parser-ready command candidate.

## Required Observability Fields

- `source_transcript`
- `normalized_transcript`
- `canonical_command_text`
- `substitution_ids`
- `language_hints`
- `ambiguity_flags`
- `post_processing_status`

## Validation Expectations

- Unit coverage for Arabic substitutions, English substitutions, and mixed
  bilingual canonicalization.
- Integration coverage proving parser inputs come from canonicalized text
  instead of raw transcripts.
- Regression coverage for noisy transcript samples that previously caused
  misclassification or missed intent recognition.
