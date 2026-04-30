# Data Model: Localization Integrity and Prompt Hardening

## CriticalPromptCatalogEntry

- **Purpose**: Defines one approved critical prompt entry stored in
  `settings/user_profile.json`.
- **Fields**:
  - `prompt_key`: stable identifier such as `startup_ready` or
    `confirmation_required`
  - `category`: `startup | onboarding | interrupt | offline | confirmation`
  - `approved_ar_text`
  - `approved_en_text`
  - `emergency_fallback_ar_text`
  - `emergency_fallback_en_text`
  - `criticality`: `blocking`
  - `version_tag`: optional plan/release revision label
- **Validation Rules**:
  - `prompt_key` must be unique.
  - Both approved language texts are required.
  - Both emergency fallback texts are required.
  - Emergency fallback must stay in the same language as the resolved prompt.
- **Relationships**:
  - referenced by many `PromptSurfaceBinding`
  - referenced by many `PromptIntegrityFinding`
  - referenced by many `RuntimePromptResolution`

## PromptSurfaceBinding

- **Purpose**: Maps one critical runtime surface to its approved prompt key.
- **Fields**:
  - `surface_id`: unique binding identifier such as
    `runtime.offline.safe_refusal`
  - `module_path`: source module owning the call site
  - `flow`: `startup | onboarding | interrupt | offline | confirmation`
  - `prompt_key`
  - `resolution_method`: `catalog_lookup`
  - `fallback_allowed`: boolean
  - `notes`: optional description of the user-visible surface
- **Validation Rules**:
  - `surface_id` must be unique.
  - Every critical surface must bind to exactly one `prompt_key`.
  - Critical surfaces must not use embedded ad-hoc text once bound.
  - `fallback_allowed` must be `true` for blocking user guidance surfaces.
- **Relationships**:
  - belongs to one `CriticalPromptCatalogEntry`
  - referenced by many `PromptIntegrityFinding`
  - referenced by many `RuntimePromptResolution`

## RuntimePromptResolution

- **Purpose**: Captures one runtime attempt to resolve and speak a critical
  prompt.
- **Fields**:
  - `resolution_id`
  - `surface_id`
  - `prompt_key`
  - `language`: `ar-EG | en-US`
  - `integrity_status`: `valid | repaired | fallback_used`
  - `fallback_used`: boolean
  - `failure_reason`: optional
    (`missing`, `replacement_character`, `mojibake_pattern`,
    `language_mismatch`)
  - `text`: final spoken text
  - `signal_emitted`: boolean
  - `occurred_at`
- **Validation Rules**:
  - `fallback_used=true` requires `failure_reason`.
  - `signal_emitted` must be `true` when `fallback_used=true`.
  - Arabic runtime resolutions must not fall back to English text.
- **Relationships**:
  - belongs to one `PromptSurfaceBinding`
  - belongs to one `CriticalPromptCatalogEntry`

### Runtime Resolution State Transitions

- `valid -> spoken`
- `repaired -> spoken`
- `fallback_used -> spoken_with_integrity_signal`

## PromptIntegrityFinding

- **Purpose**: Represents one release-validation or normalization finding for a
  catalog entry or surface binding.
- **Fields**:
  - `finding_id`
  - `scope`: `catalog_entry | surface_binding | runtime_fallback`
  - `prompt_key`
  - `surface_id`: optional for catalog-only findings
  - `language`: optional for surface-binding findings
  - `status`: `passed | failed`
  - `failure_reason`: optional
    (`missing`, `replacement_character`, `mojibake_pattern`,
    `language_mismatch`, `unapproved_surface`, `embedded_text`)
  - `observed_text`
  - `expected_source`
  - `blocking`: boolean
- **Validation Rules**:
  - `failure_reason` is required when `status=failed`.
  - Any failed blocking finding must fail the localization release gate.
  - `scope=surface_binding` requires `surface_id`.
- **Relationships**:
  - may reference one `CriticalPromptCatalogEntry`
  - may reference one `PromptSurfaceBinding`

## CatalogNormalizationRecord

- **Purpose**: Audits automatic repair actions applied to the persisted runtime
  baseline.
- **Fields**:
  - `record_id`
  - `prompt_key`
  - `language`
  - `action`: `kept | seeded | repaired`
  - `source`: `user_profile | settings_default`
  - `reason`: optional
  - `persisted_at`
- **Validation Rules**:
  - `seeded` and `repaired` actions require a reason.
  - Records should be emitted whenever Phase 7 modifies the baseline catalog
    automatically.
- **Relationships**:
  - belongs to one `CriticalPromptCatalogEntry`
