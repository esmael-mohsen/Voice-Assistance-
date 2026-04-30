"""Persistence helpers for release latency baseline records."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.release_models import REQUIRED_LATENCY_METRICS


@dataclass
class BaselineRecord:
    baseline_id: str
    metric_name: str
    profile: str
    sample_count: int
    p50_ms: float
    p95_ms: float
    captured_at: str
    approved_at: str | None
    approved_by: str | None
    source_run_id: str

    def __post_init__(self) -> None:
        if self.metric_name not in REQUIRED_LATENCY_METRICS:
            raise ValueError(f"unsupported metric: {self.metric_name}")
        if self.sample_count <= 0:
            raise ValueError("sample_count must be positive")
        if self.p95_ms < self.p50_ms:
            raise ValueError("p95_ms must be >= p50_ms")

    @property
    def is_approved(self) -> bool:
        return bool(self.approved_at and self.approved_by)


def _default_baseline_path() -> Path:
    return Path("artifacts") / "latency-baselines.json"


def load_baseline_records(path: str | Path | None = None) -> list[BaselineRecord]:
    target = Path(path) if path else _default_baseline_path()
    if not target.exists():
        return []
    payload = json.loads(target.read_text(encoding="utf-8"))
    records = payload if isinstance(payload, list) else payload.get("records", [])
    return [BaselineRecord(**item) for item in records]


def save_baseline_records(records: list[BaselineRecord], path: str | Path | None = None) -> None:
    target = Path(path) if path else _default_baseline_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    serializable = [asdict(item) for item in records]
    target.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


def append_baseline_record(
    *,
    metric_name: str,
    profile: str,
    p50_ms: float,
    p95_ms: float,
    sample_count: int,
    source_run_id: str,
    approved_by: str | None = None,
    path: str | Path | None = None,
) -> BaselineRecord:
    now = datetime.now(timezone.utc).isoformat()
    record = BaselineRecord(
        baseline_id=f"baseline-{metric_name}-{source_run_id}",
        metric_name=metric_name,
        profile=profile,
        sample_count=sample_count,
        p50_ms=float(p50_ms),
        p95_ms=float(p95_ms),
        captured_at=now,
        approved_at=now if approved_by else None,
        approved_by=approved_by,
        source_run_id=source_run_id,
    )
    records = load_baseline_records(path)
    records.append(record)
    save_baseline_records(records, path)
    return record


def latest_approved_baselines(*, profile: str, path: str | Path | None = None) -> dict[str, float]:
    records = load_baseline_records(path)
    latest: dict[str, BaselineRecord] = {}
    for record in records:
        if record.profile != profile or not record.is_approved:
            continue
        existing = latest.get(record.metric_name)
        if existing is None:
            latest[record.metric_name] = record
            continue
        if record.approved_at and existing.approved_at and record.approved_at > existing.approved_at:
            latest[record.metric_name] = record
    return {metric: entry.p95_ms for metric, entry in latest.items()}
