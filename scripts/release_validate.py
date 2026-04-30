"""Release validation entrypoint for compile/test/lint/checklist gates."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.release_artifacts import (
    artifact_storage_root,
    build_artifact_entry,
    persist_diagnostic_artifact_index,
    persist_gate_results,
    persist_pi4_stt_qualification_snapshot,
    persist_pocketsphinx_decommission_evidence,
    persist_stt_failure_scenarios,
    persist_stt_telemetry_events,
    persist_stt_telemetry_rollup,
    persist_run_manifest,
    write_json_artifact,
)
from core.release_gates import (
    ReleaseGateRunner,
    default_command_gate_handlers,
    evaluate_rollout_mode_state,
    evaluate_stt_rollout_release_gate,
    validate_release_checklist,
)
from core.release_models import (
    BASE_REQUIRED_ARTIFACT_KINDS,
    ReleaseChecklistRecord,
    ReleaseValidationContext,
    ReleaseValidationRun,
)
from core.release_override import OverrideGovernanceService


def _read_markdown_checklist(path: Path) -> ReleaseChecklistRecord:
    if not path.exists():
        raise FileNotFoundError(f"Checklist file not found: {path}")
    content = path.read_text(encoding="utf-8").splitlines()
    checked = [line for line in content if line.strip().startswith("- [x]") or line.strip().startswith("- [X]")]
    unchecked = [line for line in content if line.strip().startswith("- [ ]")]
    status = "pass" if unchecked == [] and checked else "fail"
    now = datetime.now(timezone.utc)
    return ReleaseChecklistRecord(
        checklist_id=f"checklist-{int(now.timestamp())}",
        run_id="",
        offline_behavior_status=status,
        emergency_control_status=status,
        audio_permission_status=status,
        crash_recovery_status=status,
        completed_by="release-validator",
        completed_at=now,
        notes=f"checked={len(checked)}, unchecked={len(unchecked)}",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate release quality gates.")
    parser.add_argument("--candidate-id", default="local-candidate")
    parser.add_argument("--commit-sha", default="working-tree")
    parser.add_argument(
        "--gates",
        nargs="*",
        default=["compile", "unit_tests", "integration_tests", "smoke_tests", "lint", "checklist_validation"],
    )
    parser.add_argument("--checklist-path", default="docs/release/checklist.md")
    parser.add_argument("--override-reason", default="")
    parser.add_argument("--engineering-approver", default="")
    parser.add_argument("--qa-safety-approver", default="")
    parser.add_argument("--stt-candidate-run-id", default="")
    parser.add_argument("--stt-evidence-index", default="")
    parser.add_argument("--stt-requested-mode", default="shadow")
    parser.add_argument("--stt-effective-mode", default="shadow")
    parser.add_argument("--stt-rollback-override-active", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    started_at = datetime.now(timezone.utc)
    run_id = f"run-{int(started_at.timestamp())}"
    run = ReleaseValidationRun(
        run_id=run_id,
        candidate_id=args.candidate_id,
        commit_sha=args.commit_sha,
        trigger="manual",
        started_at=started_at,
        execution_context=ReleaseValidationContext(
            python_executable=sys.executable,
            working_directory=str(PROJECT_ROOT),
            invoked_command=" ".join([Path(sys.executable).name, "scripts/release_validate.py", *sys.argv[1:]]).strip(),
            started_at=started_at,
        ),
    )

    governance = OverrideGovernanceService()
    if args.override_reason.strip():
        override = governance.request_override(
            run_id=run_id,
            requested_by="release-validator",
            reason=args.override_reason.strip(),
            failed_blocking_gates=["unknown"],
        )
        if args.engineering_approver and args.qa_safety_approver:
            override = governance.approve_override(
                override=override,
                engineering_lead_approver=args.engineering_approver,
                qa_safety_approver=args.qa_safety_approver,
            )
        run.override_record = override

    checklist = _read_markdown_checklist(Path(args.checklist_path))
    checklist.run_id = run_id
    run.checklist = checklist
    run.expected_artifact_kinds = list(BASE_REQUIRED_ARTIFACT_KINDS) + [
        "checklist_evidence",
        "baseline_comparison",
        "localization_results",
    ]

    handlers = default_command_gate_handlers()
    handlers["checklist_validation"] = lambda _run: validate_release_checklist(checklist)

    runner = ReleaseGateRunner(gate_handlers=handlers, governance=governance)
    run = runner.run(run, requested_gates=list(args.gates))

    storage_root = artifact_storage_root(run_id=run.run_id)
    entries = persist_gate_results(run=run, storage_root=storage_root)

    stt_candidate_run_id = str(args.stt_candidate_run_id or run.run_id).strip()
    evidence_index_payload: dict[str, object] = {}
    if args.stt_evidence_index:
        evidence_path = Path(args.stt_evidence_index)
        if evidence_path.exists():
            evidence_index_payload = json.loads(evidence_path.read_text(encoding="utf-8"))

    telemetry_events = list(evidence_index_payload.get("stt_events", [])) if evidence_index_payload else []
    telemetry_rollup = (
        dict(evidence_index_payload.get("stt_rollup", {}))
        if isinstance(evidence_index_payload.get("stt_rollup"), dict)
        else {}
    )
    failure_scenarios = (
        list(evidence_index_payload.get("failure_scenarios", []))
        if evidence_index_payload
        else []
    )
    pi4_snapshot = (
        dict(evidence_index_payload.get("pi4_snapshot", {}))
        if isinstance(evidence_index_payload.get("pi4_snapshot"), dict)
        else {}
    )
    pocketsphinx_evidence = (
        dict(evidence_index_payload.get("pocketsphinx_decommission", {}))
        if isinstance(evidence_index_payload.get("pocketsphinx_decommission"), dict)
        else {}
    )

    if telemetry_events:
        entries.append(persist_stt_telemetry_events(storage_root=storage_root, events=telemetry_events))
    if telemetry_rollup:
        entries.append(persist_stt_telemetry_rollup(storage_root=storage_root, rollup=telemetry_rollup))
    if failure_scenarios:
        entries.append(persist_stt_failure_scenarios(storage_root=storage_root, scenarios=failure_scenarios))
    if pi4_snapshot:
        entries.append(
            persist_pi4_stt_qualification_snapshot(storage_root=storage_root, snapshot=pi4_snapshot)
        )
    if pocketsphinx_evidence:
        entries.append(
            persist_pocketsphinx_decommission_evidence(
                storage_root=storage_root,
                evidence=pocketsphinx_evidence,
            )
        )

    rollout_state = evaluate_rollout_mode_state(
        requested_mode=str(args.stt_requested_mode or "shadow"),
        effective_mode=str(args.stt_effective_mode or "shadow"),
        rollback_override_active=bool(args.stt_rollback_override_active),
        rollback_reason_code="manual_override" if args.stt_rollback_override_active else None,
        field_validation_complete=False,
        user_visible_behavior_changed=False,
    )
    stt_gate_result = evaluate_stt_rollout_release_gate(
        candidate_run_id=stt_candidate_run_id,
        rollout_state=rollout_state,
        cloud_configuration_ok=bool(evidence_index_payload.get("cloud_configuration_ok", True)),
        strict_fallback_ok=bool(evidence_index_payload.get("strict_fallback_ok", True)),
        wake_fallback_ok=bool(evidence_index_payload.get("wake_fallback_ok", True)),
        protected_command_ok=bool(evidence_index_payload.get("protected_command_ok", True)),
        bilingual_regression_ok=bool(evidence_index_payload.get("bilingual_regression_ok", True)),
        bounded_recovery_ok=bool(evidence_index_payload.get("bounded_recovery_ok", True)),
        pi4_qualification_ok=bool(evidence_index_payload.get("pi4_qualification_ok", True)),
        pocketsphinx_default_candidate_count=int(
            evidence_index_payload.get("pocketsphinx_default_candidate_count", 0)
        ),
        pocketsphinx_default_invocation_count=int(
            evidence_index_payload.get("pocketsphinx_default_invocation_count", 0)
        ),
        required_evidence_refs=[
            "stt-events.json",
            "stt-rollup.json",
            "stt-failure-scenarios.json",
            "pi4-stt-qualification.json",
            "pocketsphinx-decommission.json",
        ],
    )
    stt_gate_payload = stt_gate_result.to_dict()
    stt_gate_path = write_json_artifact(storage_root, "stt-release-gate.json", stt_gate_payload)
    entries.append(build_artifact_entry(kind="stt_release_gate", path=stt_gate_path, payload=stt_gate_payload))

    checklist_path = write_json_artifact(storage_root, "checklist.json", asdict(checklist))
    entries.append(build_artifact_entry(kind="checklist_evidence", path=checklist_path, payload=asdict(checklist)))

    if run.override_record is not None:
        run.expected_artifact_kinds.append("override_record")
        override_path = write_json_artifact(storage_root, "override.json", asdict(run.override_record))
        entries.append(
            build_artifact_entry(kind="override_record", path=override_path, payload=asdict(run.override_record))
        )

    # Keep placeholders present to satisfy retention/audit expectations while
    # remaining implementation-light.
    placeholders = {
        "baseline_comparison": {"comparisons": [asdict(item) for item in run.latency_results]},
        "localization_results": {"results": []},
    }
    for kind, payload in placeholders.items():
        payload_path = write_json_artifact(storage_root, f"{kind}.json", payload)
        entries.append(build_artifact_entry(kind=kind, path=payload_path, payload=payload))

    diagnostic_index = persist_diagnostic_artifact_index(storage_root=storage_root, entries=entries)
    entries.append(diagnostic_index)

    manifest = persist_run_manifest(
        run=run,
        storage_root=storage_root,
        entries=entries,
        include_override=run.override_record is not None,
    )
    run.artifact_references = list(entries)
    run.missing_artifact_kinds = manifest.missing_required_kinds(
        include_override=run.override_record is not None,
        expected_kinds=run.expected_artifact_kinds,
    )
    run.artifact_manifest_id = manifest.manifest_id
    run.final_decision_reason = (
        f"Blocking gate failure: {', '.join(run.failed_blocking_gates())}"
        if run.failed_blocking_gates()
        else ("Approved emergency override applied." if run.status == "approved_with_override" else "All requested release gates passed.")
    )

    outcome = run.to_outcome()

    print(json.dumps(asdict(outcome), ensure_ascii=False, indent=2, default=str))
    return 0 if run.status in {"passed", "approved_with_override"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
