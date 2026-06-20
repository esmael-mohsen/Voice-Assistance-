"""Small .env loader for local runtime configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _env_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _strip_inline_comment(value: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(value):
        if char == "'" and not in_double:
            in_single = not in_single
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            continue
        if char == "#" and not in_single and not in_double:
            if index == 0 or value[index - 1].isspace():
                return value[:index].rstrip()
    return value.strip()


def _unquote(value: str) -> str:
    cleaned = _strip_inline_comment(value)
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        return cleaned[1:-1]
    return cleaned


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].lstrip()
    if "=" not in stripped:
        raise ValueError(line)
    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key or any(char.isspace() for char in key):
        raise ValueError(line)
    return key, _unquote(value)


def load_env_file(path: str | Path | None = None) -> dict[str, Any]:
    """Load key/value pairs from .env without overriding existing env by default."""
    env_path_value = str(os.getenv("EGB_ENV_FILE", "") or "").strip()
    env_path = Path(path or env_path_value or ".env").resolve()
    override = _env_truthy(os.getenv("EGB_ENV_OVERRIDE"))
    report: dict[str, Any] = {
        "path": str(env_path),
        "loaded": False,
        "missing": False,
        "override": override,
        "applied": (),
        "skipped_existing": (),
        "invalid_lines": (),
    }
    if not env_path.exists():
        report["missing"] = True
        return report

    applied: list[str] = []
    skipped_existing: list[str] = []
    invalid_lines: list[int] = []
    for line_number, raw_line in enumerate(env_path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        try:
            parsed = _parse_env_line(raw_line)
        except ValueError:
            invalid_lines.append(line_number)
            continue
        if parsed is None:
            continue
        key, value = parsed
        if key in os.environ and not override:
            skipped_existing.append(key)
            continue
        os.environ[key] = value
        applied.append(key)

    report.update(
        {
            "loaded": True,
            "applied": tuple(sorted(applied)),
            "skipped_existing": tuple(sorted(skipped_existing)),
            "invalid_lines": tuple(invalid_lines),
        }
    )
    return report
