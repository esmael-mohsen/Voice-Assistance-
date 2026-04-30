"""Helpers for creating and persisting release validation artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core.release_models import (
    ArtifactEntry,
    LatencyComparisonResult,
    PilotVoiceUXSummary,
    ReleaseValidationRun,
    ValidationArtifactManifest,
)


def _sha256_text(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def write_json_artifact(storage_root: str | Path, filename: str, payload: Any) -> str:
    root = Path(storage_root)
    root.mkdir(parents=True, exist_ok=True)
    target = root / filename
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
    target.write_text(serialized, encoding="utf-8")
    return str(target)


def build_artifact_entry(*, kind: str, path: str, payload: Any) -> ArtifactEntry:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return ArtifactEntry(kind=kind, path=path, checksum=_sha256_text(serialized))


def build_missing_artifact_entry(*, kind: str, notes: str) -> ArtifactEntry:
    return ArtifactEntry(
        kind=kind,
        path="",
        checksum="",
        available=False,
        source="missing",
        notes=notes,
    )


def build_validation_manifest(
    *,
    run_id: str,
    storage_root: str,
    entries: list[ArtifactEntry],
    approved_at: datetime,
    include_override: bool,
) -> ValidationArtifactManifest:
    retention_until = approved_at + timedelta(days=180)
    manifest = ValidationArtifactManifest(
        manifest_id=f"manifest-{run_id}",
        run_id=run_id,
        created_at=approved_at,
        storage_root=storage_root,
        artifact_entries=list(entries),
        retention_until=retention_until,
        purge_status="active",
    )
    missing = manifest.missing_required_kinds(include_override=include_override)
    if missing:
        # The manifest can still be created during early implementation;
        # consumers may fail gates based on missing kinds.
        pass
    return manifest


def persist_gate_results(
    *,
    run: ReleaseValidationRun,
    storage_root: str | Path,
) -> list[ArtifactEntry]:
    gate_payload = [asdict(item) for item in run.gate_results]
    gate_path = write_json_artifact(storage_root, "gate-results.json", gate_payload)
    summary_payload = {
        "run_id": run.run_id,
        "candidate_id": run.candidate_id,
        "commit_sha": run.commit_sha,
        "status": run.status,
        "executed_checks": list(run.executed_checks),
        "failed_blocking_gates": run.failed_blocking_gates(),
        "expected_artifact_kinds": list(run.expected_artifact_kinds),
        "final_decision_reason": run.final_decision_reason,
    }
    if run.execution_context is not None:
        summary_payload["execution_context"] = asdict(run.execution_context)
    summary_path = write_json_artifact(storage_root, "summary.json", summary_payload)
    return [
        build_artifact_entry(kind="test_results", path=gate_path, payload=gate_payload),
        build_artifact_entry(kind="gate_summary", path=summary_path, payload=summary_payload),
    ]


def persist_baseline_comparisons(
    *,
    storage_root: str | Path,
    comparisons: list[LatencyComparisonResult],
) -> ArtifactEntry:
    payload = [asdict(item) for item in comparisons]
    path = write_json_artifact(storage_root, "baseline-comparison.json", payload)
    return build_artifact_entry(kind="baseline_comparison", path=path, payload=payload)


def persist_localization_results(
    *,
    storage_root: str | Path,
    results: list[Any],
) -> ArtifactEntry:
    payload: list[Any] = []
    for item in results:
        if hasattr(item, "to_dict") and callable(item.to_dict):
            payload.append(item.to_dict())
        else:
            payload.append(item)
    path = write_json_artifact(storage_root, "localization-results.json", payload)
    return build_artifact_entry(kind="localization_results", path=path, payload=payload)


def persist_diagnostic_artifact_index(
    *,
    storage_root: str | Path,
    entries: list[ArtifactEntry],
) -> ArtifactEntry:
    payload = [
        {
            "kind": entry.kind,
            "path": entry.path,
            "checksum": entry.checksum,
            "available": entry.available,
            "source": entry.source,
            "notes": entry.notes,
        }
        for entry in entries
    ]
    path = write_json_artifact(storage_root, "diagnostic-artifacts.json", payload)
    return build_artifact_entry(kind="diagnostic_artifact_index", path=path, payload=payload)


def persist_run_manifest(
    *,
    run: ReleaseValidationRun,
    storage_root: str | Path,
    entries: list[ArtifactEntry],
    include_override: bool,
) -> ValidationArtifactManifest:
    approved_at = run.completed_at or datetime.now(timezone.utc)
    manifest = build_validation_manifest(
        run_id=run.run_id,
        storage_root=str(storage_root),
        entries=entries,
        approved_at=approved_at,
        include_override=include_override,
    )
    manifest_path = write_json_artifact(storage_root, "manifest.json", asdict(manifest))
    entries.append(build_artifact_entry(kind="manifest", path=manifest_path, payload=asdict(manifest)))
    return manifest


def artifact_storage_root(*, run_id: str) -> Path:
    return Path("artifacts") / run_id


def persist_pilot_voice_ux_summary(
    *,
    storage_root: str | Path,
    summary: PilotVoiceUXSummary,
) -> ArtifactEntry:
    payload = summary.to_dict()
    path = write_json_artifact(storage_root, "voice-ux-summary.json", payload)
    return build_artifact_entry(kind="pilot_voice_ux_summary", path=path, payload=payload)


def persist_stt_telemetry_events(
    *,
    storage_root: str | Path,
    events: list[dict[str, Any]],
) -> ArtifactEntry:
    path = write_json_artifact(storage_root, "stt-events.json", list(events))
    return build_artifact_entry(kind="stt_telemetry_events", path=path, payload=events)


def persist_stt_telemetry_rollup(
    *,
    storage_root: str | Path,
    rollup: dict[str, Any],
) -> ArtifactEntry:
    path = write_json_artifact(storage_root, "stt-rollup.json", dict(rollup))
    return build_artifact_entry(kind="stt_telemetry_rollup", path=path, payload=rollup)


def persist_stt_failure_scenarios(
    *,
    storage_root: str | Path,
    scenarios: list[dict[str, Any]],
) -> ArtifactEntry:
    path = write_json_artifact(storage_root, "stt-failure-scenarios.json", list(scenarios))
    return build_artifact_entry(kind="stt_failure_scenarios", path=path, payload=scenarios)


def persist_pi4_stt_qualification_snapshot(
    *,
    storage_root: str | Path,
    snapshot: dict[str, Any],
) -> ArtifactEntry:
    path = write_json_artifact(storage_root, "pi4-stt-qualification.json", dict(snapshot))
    return build_artifact_entry(kind="pi4_stt_qualification_snapshot", path=path, payload=snapshot)


def persist_pocketsphinx_decommission_evidence(
    *,
    storage_root: str | Path,
    evidence: dict[str, Any],
) -> ArtifactEntry:
    path = write_json_artifact(storage_root, "pocketsphinx-decommission.json", dict(evidence))
    return build_artifact_entry(kind="pocketsphinx_decommission", path=path, payload=evidence)
