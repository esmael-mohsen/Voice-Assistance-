"""Diagnose how a spoken command would flow through normalization and parsing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core import parser as command_parser  # noqa: E402
from core.command_post_processing import process_command_transcript  # noqa: E402


def diagnose_command(text: str) -> dict[str, Any]:
    outcome = process_command_transcript(text)
    parser_input = outcome.canonical_command_text or text
    parsed = command_parser.parse_command(parser_input, canonical_command_text=parser_input)
    if outcome.post_processing_status in {"rejected", "constrained_retry"}:
        decision = "retry"
    elif parsed.accepted and parsed.risk_level == "protected":
        decision = "confirm"
    elif parsed.accepted:
        decision = "execute"
    else:
        decision = "retry"

    return {
        "input": text,
        "normalized": outcome.normalized_transcript,
        "canonical": outcome.canonical_command_text,
        "post_processing_status": outcome.post_processing_status,
        "source_rules": list(outcome.substitution_ids),
        "ambiguity_flags": list(outcome.ambiguity_flags),
        "intent_id": parsed.intent_id,
        "matched_keyword": parsed.matched_keyword,
        "score": round(float(parsed.score), 2),
        "threshold": round(float(parsed.threshold), 2),
        "accepted": bool(parsed.accepted),
        "rejection_reason": parsed.rejection_reason,
        "decision": decision,
    }


def _print_human(report: dict[str, Any]) -> None:
    print(f"input: {report['input']}")
    print(f"normalized: {report['normalized']}")
    print(f"canonical: {report['canonical']}")
    print(f"intent: {report['intent_id']}")
    print(f"score: {report['score']} / threshold: {report['threshold']}")
    print(f"accepted: {report['accepted']} decision: {report['decision']}")
    print(f"matched_keyword: {report['matched_keyword']}")
    print(f"post_processing: {report['post_processing_status']}")
    print(f"source_rules: {', '.join(report['source_rules']) or '-'}")
    print(f"ambiguity_flags: {', '.join(report['ambiguity_flags']) or '-'}")
    if report["rejection_reason"]:
        print(f"rejection_reason: {report['rejection_reason']}")


def main(argv: list[str] | None = None) -> int:
    arg_parser = argparse.ArgumentParser(description="Diagnose a voice command transcript.")
    arg_parser.add_argument("text", help="Transcript to diagnose")
    arg_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = arg_parser.parse_args(argv)

    report = diagnose_command(args.text)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
