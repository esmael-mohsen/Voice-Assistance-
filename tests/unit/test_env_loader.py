from __future__ import annotations

import os
from pathlib import Path

from core.env_loader import load_env_file


def test_load_env_file_sets_missing_values_without_overriding(monkeypatch, tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "EGB_RUNTIME_TARGET=raspberry_pi",
                "EGB_EXISTING_VALUE=from_file",
                "EGB_QUOTED_VALUE=\"/home/pi/projects/EGY money det\"",
                "EGB_INLINE_COMMENT=value # keep this clean",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("EGB_EXISTING_VALUE", "from_system")

    report = load_env_file(env_path)

    assert os.environ["EGB_RUNTIME_TARGET"] == "raspberry_pi"
    assert os.environ["EGB_EXISTING_VALUE"] == "from_system"
    assert os.environ["EGB_QUOTED_VALUE"] == "/home/pi/projects/EGY money det"
    assert os.environ["EGB_INLINE_COMMENT"] == "value"
    assert report == {
        "path": str(env_path),
        "loaded": True,
        "missing": False,
        "override": False,
        "applied": ("EGB_INLINE_COMMENT", "EGB_QUOTED_VALUE", "EGB_RUNTIME_TARGET"),
        "skipped_existing": ("EGB_EXISTING_VALUE",),
        "invalid_lines": (),
    }


def test_load_env_file_overrides_when_enabled(monkeypatch, tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("export EGB_EXISTING_VALUE=from_file\n", encoding="utf-8")
    monkeypatch.setenv("EGB_EXISTING_VALUE", "from_system")
    monkeypatch.setenv("EGB_ENV_OVERRIDE", "1")

    report = load_env_file(env_path)

    assert os.environ["EGB_EXISTING_VALUE"] == "from_file"
    assert report["applied"] == ("EGB_EXISTING_VALUE",)
    assert report["skipped_existing"] == ()
    assert report["override"] is True


def test_load_env_file_missing_path_is_safe(tmp_path: Path) -> None:
    report = load_env_file(tmp_path / ".env")

    assert report["loaded"] is False
    assert report["missing"] is True
    assert report["applied"] == ()
