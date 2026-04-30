# Research: Localization Integrity and Prompt Hardening

## Decision: Keep `settings/user_profile.json` as the approved runtime baseline

- **Decision**: Treat `settings/user_profile.json` as the authoritative runtime
  baseline for `critical_prompt_catalog`, and use the clean defaults in
  `settings/settings_manager.py` only as bootstrap and emergency-fallback seed
  data when repairing missing or corrupted entries.
- **Rationale**: The clarified spec explicitly keeps the runtime source of
  truth in `settings/user_profile.json`, and the current settings pipeline
  already persists and reloads the catalog from that file.
- **Alternatives considered**:
  - Move the catalog into a dedicated code/config module: rejected because it
    would split prompt authority away from the persisted runtime baseline.
  - Maintain a separate release-only catalog: rejected because runtime and
    release validation could drift apart.

## Decision: Repair persisted catalog entries during load/save normalization

- **Decision**: Normalize the persisted catalog when settings are loaded or
  applied, ensuring required keys and both languages exist and replacing known
  corrupted values with approved seeded content before the repaired baseline is
  persisted back to `settings/user_profile.json`.
- **Rationale**: The repository already contains corrupted persisted prompt
  values, so Phase 7 must recover existing profiles safely without requiring
  users to delete their settings manually.
- **Alternatives considered**:
  - Trust persisted values without repair: rejected because current corrupted
    profiles would continue to speak broken Arabic.
  - Require users to delete and recreate profiles: rejected because it is not
    acceptable for an accessibility-critical setup flow.

## Decision: Define an explicit critical prompt surface registry

- **Decision**: Maintain an explicit surface registry that maps each critical
  runtime surface to exactly one approved prompt key, covering startup,
  onboarding guidance, interrupt acknowledgements, offline safe-refusal
  guidance, and protected-command confirmation flows.
- **Rationale**: Release validation must prove more than catalog cleanliness;
  it must also prove that runtime call sites resolve through approved prompt
  keys instead of embedded or duplicated strings.
- **Alternatives considered**:
  - Validate the catalog only: rejected because embedded runtime strings would
    still bypass the approved source.
  - Rely on source-code grep heuristics only: rejected because grep cannot
    reliably prove runtime binding correctness.

## Decision: Return structured runtime prompt resolution with same-language fallback

- **Decision**: Resolve critical prompts through a structured result that
  includes `surface_id`, `prompt_key`, `language`, `integrity_status`,
  `fallback_used`, `failure_reason`, and `text`, and require same-language
  emergency fallback text whenever a critical prompt is missing or corrupt.
- **Rationale**: The runtime needs a machine-readable way to distinguish clean
  catalog use from degraded fallback use, and the spec forbids leaving blind or
  low-vision users without spoken guidance.
- **Alternatives considered**:
  - Silent fallback with logs only: rejected because release and runtime
    observability would be too weak.
  - English fallback for broken Arabic prompts: rejected because it harms
    accessibility and violates the clarified same-language rule.

## Decision: Detect Arabic corruption with deterministic mojibake heuristics

- **Decision**: Fail integrity checks on empty text, replacement characters,
  and an explicit set of mojibake patterns derived from the current corruption
  corpus in `settings/user_profile.json`, `core/assistant_runtime.py`,
  `core/resolver.py`, and `controllers/mock_controllers.py`.
- **Rationale**: Current corruption is not limited to empty strings or the
  replacement character; Phase 7 needs deterministic rules that catch known
  broken encodings and remain regression-testable.
- **Alternatives considered**:
  - Check only for empty strings and `\ufffd`: rejected because most current
    broken Arabic strings would pass.
  - Use subjective manual review only: rejected because release validation must
    be automatic and repeatable.

## Decision: Run release localization validation in two passes

- **Decision**: Extend `core/release_localization.py` to validate both the
  approved catalog entries and the critical surface bindings, producing
  explicit failure reasons such as `missing`, `replacement_character`,
  `mojibake_pattern`, `language_mismatch`, `unapproved_surface`, and
  `embedded_text`.
- **Rationale**: Two-pass validation matches the clarified spec: catalog
  integrity alone is not enough if a critical runtime surface still speaks old
  embedded text.
- **Alternatives considered**:
  - End-to-end spoken-flow tests only: rejected because they are slower and do
    not always pinpoint the broken prompt source.
  - Catalog validation only: rejected because it cannot detect bypassed
    bindings.
