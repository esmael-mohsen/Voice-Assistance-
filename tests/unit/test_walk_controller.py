from __future__ import annotations

from pathlib import Path

from controllers.capability_contracts import CapabilityTimeoutPolicy, build_request
from controllers.walk_controller import WalkAssistantProcessController


def _policy() -> CapabilityTimeoutPolicy:
    return CapabilityTimeoutPolicy(
        capability_id="obstacle_detection",
        start_timeout_s=0.1,
        stop_timeout_s=0.1,
        status_timeout_s=0.1,
        execute_timeout_s=0.1,
        hard_max_s=10.0,
    )


def test_walk_controller_launches_ros2_blind_assist_entrypoint(tmp_path: Path) -> None:
    project_dir = tmp_path / "Walk_Assistant"
    launch_dir = project_dir / "ros2_ws" / "src" / "blind_assist" / "launch"
    launch_dir.mkdir(parents=True)
    launch_file = launch_dir / "blind_assist.launch.py"
    launch_file.write_text("from launch import LaunchDescription\n", encoding="utf-8")
    python_path = project_dir / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")

    class _FakeProcess:
        def __init__(self) -> None:
            self.pid = 2468
            self._running = True

        def poll(self):
            return None if self._running else 0

        def terminate(self) -> None:
            self._running = False

        def kill(self) -> None:
            self._running = False

    launches: list[dict[str, object]] = []
    fake_process = _FakeProcess()

    def _fake_popen(args, **kwargs):
        launches.append({"args": args, **kwargs})
        return fake_process

    controller = WalkAssistantProcessController(
        project_path=project_dir,
        timeout_policy=_policy(),
        popen_factory=_fake_popen,
    )

    start = controller.start(
        build_request(capability_id="obstacle_detection", action="start", timeout_seconds=0.1)
    )

    assert start.status == "success"
    assert start.backend_name == "walk_assistant_process"
    assert start.payload["running"] is True
    assert start.payload["suspend_assistant_listening"] is True
    assert launches[0]["args"] == [
        str(python_path),
        "-m",
        "launch",
        str(launch_file),
    ]

    stop = controller.stop(
        build_request(capability_id="obstacle_detection", action="stop", timeout_seconds=0.1)
    )

    assert stop.status == "success"
    assert stop.payload["running"] is False
