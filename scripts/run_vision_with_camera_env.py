"""Run the external vision app after applying camera index environment overrides."""

from __future__ import annotations

import os
import runpy
import sys


def _camera_index_from_env(default: int) -> int:
    for key in ("EGB_VISION_CAMERA_INDEX", "EGB_CAMERA_INDEX", "CAMERA_INDEX"):
        value = os.environ.get(key)
        if value is None or not value.strip():
            continue
        try:
            return int(value.strip())
        except ValueError:
            print(f"[EGB_VISION_LAUNCHER] Ignoring invalid {key}={value!r}", file=sys.stderr)
    return default


def main() -> None:
    import config

    original_index = int(getattr(config, "CAMERA_INDEX", 0))
    config.CAMERA_INDEX = _camera_index_from_env(original_index)
    print(
        "[EGB_VISION_LAUNCHER] "
        f"CAMERA_INDEX original={original_index} effective={config.CAMERA_INDEX}",
        flush=True,
    )
    runpy.run_path("main.py", run_name="__main__")


if __name__ == "__main__":
    main()
