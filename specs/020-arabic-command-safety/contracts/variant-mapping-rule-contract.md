# Variant Mapping Rule Contract

## Purpose

Define the curated allowlist record used to map a supported Arabic,
bilingual, or phonetic phrase to an existing command meaning.

## Record Shape

```json
{
  "rule_id": "ar.stop.waqef_al_nizam",
  "source_phrase": "وقف النظام",
  "canonical_command_text": "stop system",
  "intent_id": "stop_system",
  "variant_type": "arabic",
  "risk_level": "protected",
  "language_scope": "arabic",
  "enabled_by_default": true,
  "notes": "Curated protected-command alias; remains confirmation-gated."
}
```

## Rules

- `canonical_command_text` must map to an existing supported command boundary.
- The contract must not be used to invent new executable intent IDs.
- Protected-command aliases remain protected after mapping; the rule cannot
  lower their confirmation requirements.
- Duplicate or overly broad `source_phrase` entries are rejected after
  normalization review.
- Field utterances must not auto-create new mapping rules by default.

## Validation Expectations

- Parser and post-processing tests verify that each curated mapping resolves
  only to the intended existing command meaning.
- Negative tests verify unsupported near-miss phrases do not inherit the rule.
