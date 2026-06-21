from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_vision_env_launcher_overrides_config_camera_index_before_running_main() -> None:
    launcher = ROOT / "scripts" / "run_vision_with_camera_env.py"

    content = launcher.read_text(encoding="utf-8")

    assert "EGB_VISION_CAMERA_INDEX" in content
    assert "EGB_CAMERA_INDEX" in content
    assert "CAMERA_INDEX" in content
    assert "config.CAMERA_INDEX" in content
    assert "runpy.run_path" in content
    assert 'run_name="__main__"' in content
