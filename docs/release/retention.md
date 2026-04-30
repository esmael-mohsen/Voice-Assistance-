# Release Artifact Retention

## Policy

Release validation artifacts must be retained for 180 days from approval date.

## Required Artifact Kinds

- Base required (every run):
  `gate_summary`, `test_results`, `diagnostic_artifact_index`
- Conditional (run-specific):
  `checklist_evidence`, `baseline_comparison`, `localization_results`,
  `override_record`

## Lifecycle

1. Create manifest at release completion.
2. Record missing expected artifact kinds explicitly in run outcome metadata.
3. Track `retention_until` per manifest.
4. Archive or purge only after retention period ends.
