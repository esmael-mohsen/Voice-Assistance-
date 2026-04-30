# PocketSphinx Decommission Contract

## Purpose

Define the evidence proving PocketSphinx is outside the default production STT
path and required production accuracy baseline.

## Evidence Shape

```json
{
  "evidence_id": "sphinx-decommission-001",
  "candidate_run_id": "candidate-2026-04-28",
  "default_candidate_count": 0,
  "default_invocation_count": 0,
  "compatibility_flag_status": "disabled_by_default",
  "accuracy_baseline_includes_sphinx": false,
  "compatibility_tests_present": true,
  "documentation_status": "updated",
  "status": "passed",
  "evidence_refs": [
    "docs/STTInfo.md",
    "artifacts/run-001/stt/pocketsphinx-decommission.json"
  ]
}
```

## Rules

- Default production readiness requires zero PocketSphinx candidates and zero
  PocketSphinx invocations.
- Sphinx-specific tests are excluded from the required production accuracy
  baseline except compatibility-only checks proving non-default behavior.
- Remaining documentation must describe PocketSphinx as non-primary and
  compatibility-only.

## Validation Expectations

- Unit tests prove default STT paths do not invoke PocketSphinx.
- Release validation proves production baselines exclude Sphinx accuracy
  checks while retaining explicit compatibility notes.
