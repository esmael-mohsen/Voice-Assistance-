"""Smoke checks for quickstart-aligned release quality gate behavior."""

from __future__ import annotations

from datetime import datetime, timezone

from core.release_artifacts import build_validation_manifest
from core.release_gates import RELEASE_GATE_ORDER
from core.release_models import ArtifactEntry


def test_release_gate_order_contains_required_blocking_gates() -> None:
    assert RELEASE_GATE_ORDER[:3] == ("compile", "unit_tests", "integration_tests")
    assert "lint" in RELEASE_GATE_ORDER
    assert "baseline_compare" in RELEASE_GATE_ORDER
    assert "checklist_validation" in RELEASE_GATE_ORDER


def test_release_manifest_builder_produces_active_manifest() -> None:
    manifest = build_validation_manifest(
        run_id="run-quickstart",
        storage_root="artifacts/run-quickstart",
        entries=[ArtifactEntry(kind="gate_summary", path="summary.json", checksum="sha256:abc")],
        approved_at=datetime.now(timezone.utc),
        include_override=False,
    )

    assert manifest.purge_status == "active"
    assert manifest.artifact_entries


def test_release_manifest_quickstart_requires_diagnostic_artifact_index() -> None:
    manifest = build_validation_manifest(
        run_id="run-quickstart-missing",
        storage_root="artifacts/run-quickstart-missing",
        entries=[ArtifactEntry(kind="gate_summary", path="summary.json", checksum="sha256:abc")],
        approved_at=datetime.now(timezone.utc),
        include_override=False,
    )

    assert "diagnostic_artifact_index" in manifest.missing_required_kinds(include_override=False)
