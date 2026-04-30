# Recognition Configuration Contract

## Purpose

Define the effective rollout and compatibility configuration used by the STT
foundation at runtime.

## Effective Configuration Shape

```json
{
  "cloud_primary_enabled": false,
  "strict_vosk_fallback_enabled": false,
  "sphinx_compat_enabled": false,
  "cloud_timeout_s": 3.0,
  "cloud_max_alternatives": 3,
  "selected_profile_language": "en-US",
  "configured_from_environment": true,
  "field_safe": true,
  "credential_material_present": false
}
```

## Environment Controls

- `EGB_STT_CLOUD_PRIMARY_ENABLED`
- `EGB_STT_STRICT_VOSK_FALLBACK_ENABLED`
- `EGB_STT_ENABLE_SPHINX_COMPAT`
- `EGB_STT_CLOUD_TIMEOUT_S`
- `EGB_STT_CLOUD_MAX_ALTERNATIVES`

## Rules

- Defaults are cloud primary off, strict Vosk fallback off, and PocketSphinx
  compatibility off.
- `cloud_timeout_s` defaults to `3.0` and must be positive.
- `cloud_max_alternatives` must be at least `1`.
- Credential material must not be copied into this configuration snapshot.
- The snapshot may include selected profile language but must not allow
  detected cloud language to mutate that selected language automatically.
- The configuration must be safe to emit in startup diagnostics.
- Provider metadata surfaces may embed this snapshot under a field such as
  `recognition_configuration`, preserving the same field-safe shape.

## Validation Expectations

- Unit tests cover default values, enabled values, invalid numeric values, and
  compatibility gating.
- Integration tests prove effective configuration is reflected in recognition
  source and fallback decisions.
- Privacy tests prove credential material is not present in logs, profile
  state, or release artifacts by default.
