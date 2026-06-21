from __future__ import annotations

from pathlib import Path

from controllers.capability_contracts import CapabilityTimeoutPolicy, build_request
from controllers.money_controller import AssistiveMoneyProcessController


def _policy(capability_id: str) -> CapabilityTimeoutPolicy:
    return CapabilityTimeoutPolicy(
        capability_id=capability_id,
        start_timeout_s=0.1,
        stop_timeout_s=0.1,
        status_timeout_s=0.1,
        execute_timeout_s=0.1,
        hard_max_s=10.0,
    )


def test_money_process_controller_starts_and_stops_subprocess(tmp_path: Path) -> None:
    project_dir = tmp_path / "money-project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('money app')\n", encoding="utf-8")
    python_path = project_dir / ".venv" / "Scripts" / "python.exe"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")

    class _FakeProcess:
        def __init__(self) -> None:
            self.pid = 8765
            self._running = True

        def poll(self):
            return None if self._running else 0

        def send_signal(self, _sig) -> None:
            self._running = False

        def terminate(self) -> None:
            self._running = False

        def kill(self) -> None:
            self._running = False

    launches: list[dict[str, object]] = []
    fake_process = _FakeProcess()

    def _fake_popen(args, **kwargs):
        launches.append({"args": args, **kwargs})
        return fake_process

    controller = AssistiveMoneyProcessController(
        project_path=project_dir,
        timeout_policy=_policy("money_detection"),
        popen_factory=_fake_popen,
    )

    start_request = build_request(capability_id="money_detection", action="start", timeout_seconds=0.1)
    start_result = controller.start(start_request)

    assert start_result.status == "success"
    assert start_result.payload["running"] is True
    assert launches
    assert launches[0]["args"][0] == str(python_path)

    stop_request = build_request(capability_id="money_detection", action="stop", timeout_seconds=0.1)
    stop_result = controller.stop(stop_request)

    assert stop_result.status == "success"
    assert stop_result.payload["running"] is False


def test_money_process_controller_reports_already_running(tmp_path: Path) -> None:
    project_dir = tmp_path / "money-project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('money app')\n", encoding="utf-8")
    python_path = project_dir / ".venv" / "Scripts" / "python.exe"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")

    class _FakeProcess:
        pid = 41

        def poll(self):
            return None

    launches = 0

    def _fake_popen(*_args, **_kwargs):
        nonlocal launches
        launches += 1
        return _FakeProcess()

    controller = AssistiveMoneyProcessController(
        project_path=project_dir,
        timeout_policy=_policy("money_detection"),
        popen_factory=_fake_popen,
    )

    request = build_request(capability_id="money_detection", action="start", timeout_seconds=0.1)
    first = controller.start(request)
    second = controller.start(request)

    assert first.status == "success"
    assert second.status == "success"
    assert launches == 1


def test_money_process_controller_prefers_env_python_then_pi_venv(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "money-project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('money app')\n", encoding="utf-8")
    env_python = tmp_path / "custom-python"
    env_python.write_text("", encoding="utf-8")
    monkeypatch.setenv("EGB_MONEY_PYTHON", str(env_python))

    controller = AssistiveMoneyProcessController(
        project_path=project_dir,
        timeout_policy=_policy("money_detection"),
    )

    assert controller._resolved_python() == env_python.resolve()


def test_money_process_controller_uses_pi_venv_before_windows_venv(tmp_path: Path) -> None:
    project_dir = tmp_path / "money-project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('money app')\n", encoding="utf-8")
    pi_python = project_dir / ".venv" / "bin" / "python"
    windows_python = project_dir / ".venv" / "Scripts" / "python.exe"
    pi_python.parent.mkdir(parents=True)
    windows_python.parent.mkdir(parents=True)
    pi_python.write_text("", encoding="utf-8")
    windows_python.write_text("", encoding="utf-8")

    controller = AssistiveMoneyProcessController(
        project_path=project_dir,
        timeout_policy=_policy("money_detection"),
    )

    assert controller._resolved_python() == pi_python.resolve()


def test_money_process_controller_uses_configured_terminal_command(monkeypatch, tmp_path: Path) -> None:
    project_dir = tmp_path / "money-project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('money app')\n", encoding="utf-8")
    monkeypatch.setenv("EGB_MONEY_COMMAND", "bash -lc 'source .venv/bin/activate && exec python -u main.py'")

    class _FakeProcess:
        pid = 99

        def poll(self):
            return None

    launches: list[dict[str, object]] = []

    def _fake_popen(args, **kwargs):
        launches.append({"args": args, **kwargs})
        return _FakeProcess()

    controller = AssistiveMoneyProcessController(
        project_path=project_dir,
        timeout_policy=_policy("money_detection"),
        popen_factory=_fake_popen,
    )

    result = controller.start(build_request(capability_id="money_detection", action="start", timeout_seconds=0.1))

    assert result.status == "success"
    assert launches[0]["args"] == ["bash", "-lc", "source .venv/bin/activate && exec python -u main.py"]
    assert launches[0]["cwd"] == str(project_dir.resolve())


def test_money_process_controller_opens_visible_terminal_when_enabled(monkeypatch, tmp_path: Path) -> None:
    project_dir = tmp_path / "money-project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('money app')\n", encoding="utf-8")
    monkeypatch.setenv("EGB_MONEY_COMMAND", "bash -lc 'source .venv/bin/activate && exec python -u main.py'")
    monkeypatch.setenv("EGB_EXTERNAL_TERMINAL_ENABLED", "1")
    monkeypatch.setenv("EGB_EXTERNAL_TERMINAL_APP", "lxterminal")

    class _FakeProcess:
        pid = 100

        def poll(self):
            return None

    launches: list[dict[str, object]] = []

    def _fake_popen(args, **kwargs):
        launches.append({"args": args, **kwargs})
        return _FakeProcess()

    controller = AssistiveMoneyProcessController(
        project_path=project_dir,
        timeout_policy=_policy("money_detection"),
        popen_factory=_fake_popen,
    )

    result = controller.start(build_request(capability_id="money_detection", action="start", timeout_seconds=0.1))

    assert result.status == "success"
    assert launches[0]["args"][:3] == ["lxterminal", f"--working-directory={project_dir.resolve()}", "--command"]
    assert "source .venv/bin/activate && exec python -u main.py" in launches[0]["args"][3]
    assert launches[0]["cwd"] == str(project_dir.resolve())
