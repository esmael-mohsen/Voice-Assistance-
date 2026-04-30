# Critical Prompt Catalog Contract

## Purpose

Define the approved runtime catalog shape, critical surface bindings, and the
structured runtime prompt-resolution payload for Phase 7.

## Approved Catalog Entry Contract

```json
{
  "prompt_key": "offline_guidance",
  "category": "offline",
  "approved_text": {
    "ar": "[approved Arabic text]",
    "en": "Network unavailable. Try again later."
  },
  "emergency_fallback": {
    "ar": "[approved Arabic fallback]",
    "en": "Network unavailable. Try again later."
  },
  "criticality": "blocking"
}
```

### Rules

- `prompt_key` must be stable and unique.
- Both `approved_text` languages are required.
- Both `emergency_fallback` languages are required.
- The persisted runtime baseline for approved entries is
  `settings/user_profile.json`.
- Bootstrap defaults in `settings/settings_manager.py` may seed or repair the
  baseline but must not become a competing runtime source of truth.

## Critical Surface Binding Contract

```json
{
  "surface_id": "runtime.offline.safe_refusal",
  "module_path": "core.assistant_runtime",
  "flow": "offline",
  "prompt_key": "offline_guidance",
  "resolution_method": "catalog_lookup",
  "fallback_allowed": true
}
```

### Rules

- Every critical surface must have exactly one binding.
- Every binding must point to an approved `prompt_key`.
- Critical surfaces must not bypass the catalog with embedded ad-hoc text.
- `fallback_allowed` must be `true` for accessibility-critical spoken
  guidance.

## Runtime Prompt Resolution Contract

```json
{
  "surface_id": "runtime.offline.safe_refusal",
  "prompt_key": "offline_guidance",
  "language": "ar-EG",
  "integrity_status": "fallback_used",
  "fallback_used": true,
  "failure_reason": "mojibake_pattern",
  "text": "[spoken Arabic fallback text]",
  "signal_emitted": true
}
```

### Rules

- `integrity_status` must be one of `valid`, `repaired`, or `fallback_used`.
- `fallback_used=true` requires `failure_reason` and `signal_emitted=true`.
- Arabic runtime resolution must not degrade to English text.
- The final `text` is the only string allowed to reach the speech engine for a
  critical surface.

## Required Critical Surface Families

The Phase 7 catalog and bindings must cover at least:

- Startup readiness and startup degraded/offline guidance
- Onboarding intro plus language, voice, speed, and name prompts
- Interrupt acknowledgements
- Offline safe-refusal guidance
- Protected-command confirmation prompts

## Bound Surface Inventory

The current implementation binds these critical surfaces through the catalog:

- `runtime.startup.ready`
- `runtime.startup.provider_unavailable`
- `runtime.startup.degraded`
- `runtime.startup.wake_hint`
- `runtime.onboarding.*`
- `runtime.interrupt.stop`
- `runtime.interrupt.cancel`
- `runtime.interrupt.emergency`
- `runtime.offline.safe_refusal`
- `resolver.confirmation.required`
- `resolver.confirmation.declined`
- `resolver.confirmation.expired`

## Validation Expectations

- Unit tests for catalog normalization and fallback behavior
- Integration tests for runtime surface bindings
- Regression tests ensuring no critical surface emits embedded unapproved text
