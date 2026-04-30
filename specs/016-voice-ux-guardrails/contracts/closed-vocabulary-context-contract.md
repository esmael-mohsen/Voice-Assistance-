# Closed Vocabulary Context Contract

## Purpose

Define the registry payload used to describe a guided answer set shared by STT,
runtime validation, and resolver-safe dialog handling.

## Output Shape

```json
{
  "closed_vocabulary_id": "confirmation.yes_no_cancel",
  "flow_type": "confirmation",
  "usage_modes": ["confirmation"],
  "allow_mixed_language_aliases": true,
  "global_safety_preemption_only": true,
  "retry_limit": 1,
  "safe_fallback_strategy": "graceful_exit",
  "options": [
    {
      "option_id": "affirmative",
      "canonical_value": "yes",
      "persisted_value": "affirmative",
      "requires_confirmation": false,
      "alias_tokens": ["yes", "yes please", "okay"]
    },
    {
      "option_id": "cancel",
      "canonical_value": "cancel",
      "persisted_value": "cancel",
      "requires_confirmation": false,
      "alias_tokens": ["cancel", "stop"]
    }
  ]
}
```

## Rules

- `closed_vocabulary_id` must be unique and stable across runtime and tests.
- `retry_limit` must be positive and align with settings-backed retry policy.
- `safe_fallback_strategy` must be one of:
  `keep_default`, `keep_last_confirmed`, or `graceful_exit`.
- Each option must define a canonical value plus alias tokens.
- Alias groups must remain intentionally bounded so unsupported speech can be
  rejected safely.
- `global_safety_preemption_only=true` means unrelated non-safety commands do
  not escape the current guided context.

## Required Observability Fields

- `closed_vocabulary_id`
- `flow_type`
- `usage_modes`
- `allow_mixed_language_aliases`
- `global_safety_preemption_only`
- `retry_limit`
- `safe_fallback_strategy`
- `options[].option_id`
- `options[].canonical_value`
- `options[].persisted_value`
- `options[].requires_confirmation`
- `options[].alias_tokens`

## Validation Expectations

- Unit coverage for bilingual alias matching and unsupported-answer rejection.
- Integration coverage for out-of-domain answers and global-safety preemption
  boundaries.
- Contract validation to ensure every runtime `closed_vocabulary_id` maps to a
  registry entry.
