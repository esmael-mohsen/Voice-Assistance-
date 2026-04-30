"""Unit tests for emergency override governance."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.release_override import OverrideGovernanceService


def test_override_approval_requires_dual_roles() -> None:
    service = OverrideGovernanceService()
    override = service.request_override(
        run_id="run-001",
        requested_by="release-manager",
        reason="blocking bug accepted temporarily",
        failed_blocking_gates=["lint"],
        requested_at=datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError):
        service.approve_override(
            override=override,
            engineering_lead_approver="eng-lead",
            qa_safety_approver="",
            approved_at=datetime(2026, 4, 19, 12, 30, tzinfo=timezone.utc),
        )


def test_override_due_date_is_capped_to_48_hours() -> None:
    service = OverrideGovernanceService()
    requested_at = datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc)
    approved_at = datetime(2026, 4, 19, 13, 0, tzinfo=timezone.utc)
    override = service.request_override(
        run_id="run-002",
        requested_by="release-manager",
        reason="pilot hotfix window",
        failed_blocking_gates=["compile"],
        requested_at=requested_at,
    )

    approved = service.approve_override(
        override=override,
        engineering_lead_approver="eng-lead",
        qa_safety_approver="qa-owner",
        approved_at=approved_at,
    )

    assert approved.remediation_due_at == approved_at + timedelta(hours=48)


def test_override_closure_after_due_time_marks_breached() -> None:
    service = OverrideGovernanceService()
    override = service.request_override(
        run_id="run-003",
        requested_by="release-manager",
        reason="temporary quality gate bypass",
        failed_blocking_gates=["baseline_compare"],
        requested_at=datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc),
    )
    override = service.approve_override(
        override=override,
        engineering_lead_approver="eng-lead",
        qa_safety_approver="qa-owner",
        approved_at=datetime(2026, 4, 19, 12, 30, tzinfo=timezone.utc),
    )

    closed = service.close_override(
        override=override,
        closure_evidence_ref="artifacts/remediation.md",
        closed_at=override.remediation_due_at + timedelta(minutes=1),
    )

    assert closed.remediation_status == "breached"
