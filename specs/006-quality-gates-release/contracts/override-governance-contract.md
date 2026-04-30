# Override Governance Contract

## Purpose

Define emergency override approval, remediation tracking, and artifact
retention requirements for release runs with failed blocking gates.

## Emergency Override Request Contract

```json
{
  "override_id": "ovr-2026-04-19-01",
  "run_id": "run-2026-04-19-001",
  "requested_by": "release_manager",
  "requested_at": "2026-04-19T14:12:00Z",
  "reason": "Pilot demo deadline requires temporary release despite lint failure",
  "failed_blocking_gates": ["lint"]
}
```

### Rules

- `reason` must be non-empty and specific to the failed gate(s).
- Override request is invalid without at least one failed blocking gate.

## Dual Approval Contract

```json
{
  "override_id": "ovr-2026-04-19-01",
  "engineering_lead_approver": "eng_lead_1",
  "qa_safety_approver": "qa_safety_1",
  "approved_at": "2026-04-19T14:20:00Z",
  "remediation_due_at": "2026-04-21T14:20:00Z"
}
```

### Rules

- Both approver roles are mandatory:
  - Engineering Lead
  - QA/Safety owner
- Override becomes active only after both approvals are present.
- `remediation_due_at` must be no later than 48 hours after approval.
- Active remediation statuses are `open`, `closed`, and `breached`.

## Remediation Closure Contract

```json
{
  "override_id": "ovr-2026-04-19-01",
  "remediation_status": "closed",
  "remediation_closed_at": "2026-04-20T09:00:00Z",
  "closure_evidence_ref": "artifacts/ovr-2026-04-19-01/remediation.md",
  "breach_flag": false
}
```

### Rules

- `closure_evidence_ref` is mandatory when status is `closed`.
- If closure time exceeds due time, `remediation_status` must be `breached`.
- Breached overrides should trigger explicit follow-up escalation.

## Artifact Retention Manifest Contract

```json
{
  "manifest_id": "manifest-2026-04-19-001",
  "run_id": "run-2026-04-19-001",
  "retention_until": "2026-10-16T00:00:00Z",
  "entries": [
    {
      "kind": "gate_summary",
      "path": "artifacts/run-2026-04-19-001/summary.json",
      "checksum": "sha256:..."
    },
    {
      "kind": "override_record",
      "path": "artifacts/run-2026-04-19-001/override.json",
      "checksum": "sha256:..."
    }
  ]
}
```

### Rules

- `retention_until` must be approval date + 180 days.
- Required artifact kinds:
  - `gate_summary`
  - `test_results`
  - `localization_results`
  - `baseline_comparison`
  - `checklist_evidence`
  - `override_record` (if override exists)

## Audit Query Contract

Expected minimum queryable fields for compliance review:

- `run_id`
- `status`
- `failed_blocking_gates`
- `override_id`
- `engineering_lead_approver`
- `qa_safety_approver`
- `approved_at`
- `remediation_due_at`
- `remediation_status`
- `retention_until`

## Validation Expectations

- Unit tests for role enforcement and 48-hour remediation window logic.
- Integration tests for override activation and breach flagging.
- Retention checks to ensure all required artifacts remain available for 180
  days.
