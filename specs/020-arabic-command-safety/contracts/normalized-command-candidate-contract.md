# Normalized Command Candidate Contract

## Purpose

Define the parser-ready command payload emitted by
`core/command_post_processing.py` after normalization, curated variant
mapping, and integrity gating.

## Usable Shape

```json
{
  "candidate_id": "cmd-123",
  "source_transcript_ref": "field-safe-transcript-ref",
  "normalized_transcript_ref": "field-safe-normalized-ref",
  "canonical_command_text": "read text",
  "integrity_status": "trusted",
  "substitution_ids": ["ar.ocr.eqra_al_nass"],
  "high_impact_substitution": true,
  "ambiguity_flags": [],
  "language_hints": ["ar"],
  "matched_variant_rule_ids": ["ar.ocr.eqra_al_nass"],
  "dictionary_mode": "command_inventory",
  "closed_vocabulary_id": null,
  "post_processing_status": "normalized",
  "field_safe": true,
  "raw_user_content_present": false
}
```

## Rejected Shape

```json
{
  "candidate_id": "cmd-124",
  "source_transcript_ref": "field-safe-corrupted-ref",
  "normalized_transcript_ref": "",
  "canonical_command_text": "",
  "integrity_status": "mojibake",
  "substitution_ids": [],
  "high_impact_substitution": false,
  "ambiguity_flags": ["integrity_rejected"],
  "language_hints": ["ar"],
  "matched_variant_rule_ids": [],
  "dictionary_mode": "command_inventory",
  "closed_vocabulary_id": null,
  "post_processing_status": "rejected",
  "field_safe": true,
  "raw_user_content_present": false
}
```

## Rules

- `post_processing_status=normalized` or `unchanged` requires a non-empty
  `canonical_command_text`.
- `post_processing_status=rejected` must not expose executable parser-ready
  text.
- Default diagnostic payloads must use field-safe transcript references or
  omitted transcript fields instead of raw utterance content.
- `high_impact_substitution=true` is reserved for mappings or substitutions
  that materially change command interpretation and therefore must remain
  visible to downstream safety policy.
- `field_safe` must remain `true` and `raw_user_content_present` must remain
  `false` in default diagnostics.

## Validation Expectations

- Unit tests cover supported Arabic, bilingual, phonetic, and corruption
  scenarios.
- Integration tests prove runtime consumers preserve substitution, ambiguity,
  and integrity metadata through safety decisions.
