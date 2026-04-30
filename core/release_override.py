"""Emergency override governance for release quality gates."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from core.release_models import EmergencyOverrideRecord


class OverrideGovernanceService:
    """Encapsulates override request, approval, and remediation closure rules."""

    def request_override(
        self,
        *,
        run_id: str,
        requested_by: str,
        reason: str,
        failed_blocking_gates: list[str],
        requested_at: datetime | None = None,
    ) -> EmergencyOverrideRecord:
        when = requested_at or datetime.now(timezone.utc)
        override_id = f"ovr-{run_id}-{int(when.timestamp())}"
        return EmergencyOverrideRecord(
            override_id=override_id,
            run_id=run_id,
            requested_by=requested_by,
            requested_at=when,
            reason=reason.strip(),
            failed_blocking_gates=list(failed_blocking_gates),
            remediation_status="open",
        )

    def approve_override(
        self,
        *,
        override: EmergencyOverrideRecord,
        engineering_lead_approver: str,
        qa_safety_approver: str,
        approved_at: datetime | None = None,
    ) -> EmergencyOverrideRecord:
        if not engineering_lead_approver:
            raise ValueError("engineering_lead_approver is required")
        if not qa_safety_approver:
            raise ValueError("qa_safety_approver is required")
        when = approved_at or datetime.now(timezone.utc)
        remediation_due_at = when + timedelta(hours=48)
        return replace(
            override,
            engineering_lead_approver=engineering_lead_approver,
            qa_safety_approver=qa_safety_approver,
            approved_at=when,
            remediation_due_at=remediation_due_at,
            remediation_status="open",
        )

    def close_override(
        self,
        *,
        override: EmergencyOverrideRecord,
        closure_evidence_ref: str,
        closed_at: datetime | None = None,
    ) -> EmergencyOverrideRecord:
        if not closure_evidence_ref:
            raise ValueError("closure_evidence_ref is required")
        if override.remediation_due_at is None:
            raise ValueError("override must be approved before closure")
        when = closed_at or datetime.now(timezone.utc)
        status = "closed" if when <= override.remediation_due_at else "breached"
        return replace(
            override,
            remediation_status=status,
            remediation_closed_at=when,
            closure_evidence_ref=closure_evidence_ref,
        )

    @staticmethod
    def is_override_active(override: EmergencyOverrideRecord | None) -> bool:
        if override is None:
            return False
        return override.is_approved and override.remediation_status in {"open", "closed", "breached"}
