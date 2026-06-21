"""Unit tests for preemptible TTS playback behavior."""

from __future__ import annotations

from pathlib import Path
import threading
import time

import tts.tts_engine as tts_engine_module
from tts.tts_engine import TTSEngine


def _interruptible_playback_runner(*, path: str, stop_event, interrupt_event) -> dict[str, object]:  # noqa: ARG001
    checker = getattr(interrupt_event, "is_set", None) if interrupt_event is not None else None
    started_at = time.perf_counter()
    while (time.perf_counter() - started_at) < 1.0:
        if stop_event.is_set() or (callable(checker) and checker()):
            return {"completion_status": "interrupted", "interrupted": True}
        time.sleep(0.01)
    return {"completion_status": "success", "interrupted": False}


def test_tts_engine_honors_interrupt_event_mid_playback(monkeypatch) -> None:
    interrupt_event = threading.Event()
    engine = TTSEngine(playback_runner=_interruptible_playback_runner)

    async def _fake_speak_async(text, *, interrupt_event=None):  # noqa: ARG001
        return _interruptible_playback_runner(
            path="fake.mp3",
            stop_event=engine._interrupt_requested,
            interrupt_event=interrupt_event,
        )

    monkeypatch.setattr(
        engine,
        "_speak_async",
        _fake_speak_async,
    )

    def _trip_interrupt() -> None:
        time.sleep(0.02)
        interrupt_event.set()

    worker = threading.Thread(target=_trip_interrupt, daemon=True)
    worker.start()
    result = engine.speak("hello", interrupt_event=interrupt_event)
    worker.join(timeout=0.2)

    assert result["completion_status"] == "interrupted"
    assert result["interrupted"] is True


def test_tts_engine_request_stop_marks_provider_stall_degraded(monkeypatch) -> None:
    engine = TTSEngine(playback_runner=_interruptible_playback_runner)

    async def _fake_speak_async(text, *, interrupt_event=None):  # noqa: ARG001
        return {
            "completion_status": "interrupted",
            "interrupted": True,
            "degraded_mode": True,
            "degraded_reason": "provider_stall",
        }

    monkeypatch.setattr(
        engine,
        "_speak_async",
        _fake_speak_async,
    )

    engine.request_stop()
    result = engine.speak("hello")

    assert result["completion_status"] == "interrupted"
    assert result["degraded_mode"] is True
    assert result["degraded_reason"] == "provider_stall"


def test_tts_engine_request_stop_invokes_active_native_stop_callback() -> None:
    engine = TTSEngine()
    callbacks: list[str] = []
    engine._set_playback_stop_callback(lambda: callbacks.append("stopped"))
    engine.request_stop()
    assert callbacks == ["stopped"]


def test_tts_engine_winmm_path_stops_audio_when_interrupted(monkeypatch) -> None:
    interrupt_event = threading.Event()
    engine = TTSEngine()
    commands: list[str] = []
    playback_state = {"mode": "stopped", "status_checks": 0}

    def _fake_mci_send(command: str) -> tuple[int, str]:
        commands.append(command)
        if command.startswith("open "):
            playback_state["mode"] = "stopped"
            return 0, ""
        if command.startswith("play "):
            playback_state["mode"] = "playing"
            return 0, ""
        if command.startswith("status "):
            playback_state["status_checks"] += 1
            if playback_state["status_checks"] >= 2:
                interrupt_event.set()
            return 0, playback_state["mode"]
        if command.startswith("stop "):
            playback_state["mode"] = "stopped"
            return 0, ""
        if command.startswith("close "):
            return 0, ""
        return 0, ""

    monkeypatch.setattr(tts_engine_module, "_winmm_supported", lambda: True)
    monkeypatch.setattr(tts_engine_module, "_send_mci_command", _fake_mci_send)

    result = engine._play_audio_file_with_winmm(Path("fake.mp3"), interrupt_event=interrupt_event)
    assert result is not None
    assert result["completion_status"] == "interrupted"
    assert result["interrupted"] is True
    assert any(command.startswith("stop ") for command in commands)


def test_tts_engine_mpg123_backend_is_interruptible(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("EGB_TTS_PLAYBACK_BACKEND", "mpg123")
    monkeypatch.setenv("EGB_TTS_MPG123_PATH", "/usr/bin/mpg123")
    monkeypatch.setattr(TTSEngine, "_play_audio_file_with_winmm", lambda *_args, **_kwargs: None)

    class _FakeProcess:
        def __init__(self) -> None:
            self.terminated = False
            self.killed = False
            self.args: list[str] | None = None

        def poll(self):
            return None if not self.terminated and not self.killed else 0

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, timeout=None):  # noqa: ARG002
            self.terminated = True
            return 0

        def kill(self) -> None:
            self.killed = True

    fake_process = _FakeProcess()
    launches: list[list[str]] = []

    def _fake_popen(args, **_kwargs):
        launches.append(list(args))
        fake_process.args = list(args)
        return fake_process

    monkeypatch.setattr(tts_engine_module.subprocess, "Popen", _fake_popen)
    engine = TTSEngine()
    audio_path = tmp_path / "speech.mp3"
    audio_path.write_bytes(b"fake")

    def _interrupt() -> None:
        time.sleep(0.02)
        engine.request_stop()

    worker = threading.Thread(target=_interrupt, daemon=True)
    worker.start()
    result = engine._play_audio_file(audio_path)
    worker.join(timeout=0.2)

    assert launches == [["/usr/bin/mpg123", "-q", str(audio_path)]]
    assert result["completion_status"] == "interrupted"
    assert result["interrupted"] is True
    assert fake_process.terminated is True


def test_tts_engine_enforces_hard_max_duration(monkeypatch) -> None:
    engine = TTSEngine(playback_runner=_interruptible_playback_runner)

    async def _fake_speak_async(text, *, interrupt_event=None):  # noqa: ARG001
        return _interruptible_playback_runner(
            path="fake.mp3",
            stop_event=engine._interrupt_requested,
            interrupt_event=interrupt_event,
        )

    monkeypatch.setattr(engine, "_speak_async", _fake_speak_async)

    result = engine.speak("hello", max_duration_s=0.05)
    assert result["interrupted"] is True
    assert result["completion_status"] == "interrupted"
    assert result["duration_ms"] <= 300


def test_tts_engine_priority_preemption_interrupts_lower_priority_speech() -> None:
    engine = TTSEngine(playback_runner=_interruptible_playback_runner)
    results: dict[str, dict[str, object]] = {}

    def _low_priority() -> None:
        results["low"] = engine.speak("low", priority="info")

    low_worker = threading.Thread(target=_low_priority, daemon=True)
    low_worker.start()
    time.sleep(0.03)
    results["high"] = engine.speak("high", priority="warning", preempt=True)
    low_worker.join(timeout=1.0)

    assert "low" in results and "high" in results
    assert results["low"]["interrupted"] is True
    assert results["high"]["completion_status"] == "success"


def test_tts_engine_prefers_cloud_for_arabic_text(monkeypatch) -> None:
    engine = TTSEngine()
    local_calls = {"count": 0}
    cloud_calls = {"count": 0}

    def _fake_local(text, *, interrupt_event=None):  # noqa: ARG001
        local_calls["count"] += 1
        return {"completion_status": "success", "interrupted": False}

    async def _fake_cloud(text, *, interrupt_event=None):  # noqa: ARG001
        cloud_calls["count"] += 1
        return {"completion_status": "success", "interrupted": False}

    monkeypatch.setattr(engine, "_speak_local_engine", _fake_local)
    monkeypatch.setattr(engine, "_speak_async", _fake_cloud)

    result = engine.speak("المساعد جاهز")
    assert result["completion_status"] == "success"
    assert cloud_calls["count"] == 1
    assert local_calls["count"] == 0


def test_tts_engine_falls_back_local_when_cloud_fails_after_cloud_first(monkeypatch) -> None:
    engine = TTSEngine()
    local_calls = {"count": 0}

    def _fake_local(text, *, interrupt_event=None):  # noqa: ARG001
        local_calls["count"] += 1
        return {"completion_status": "success", "interrupted": False}

    async def _fake_cloud(text, *, interrupt_event=None):  # noqa: ARG001
        return {
            "completion_status": "failed",
            "interrupted": False,
            "degraded_mode": True,
            "degraded_reason": "edge_tts_unavailable",
        }

    monkeypatch.setattr(engine, "_speak_local_engine", _fake_local)
    monkeypatch.setattr(engine, "_speak_async", _fake_cloud)

    result = engine.speak("المساعد جاهز")
    assert result["completion_status"] == "success"
    assert result["degraded_mode"] is True
    assert result["degraded_reason"] == "cloud_tts_failed_fell_back_local"
    assert local_calls["count"] == 1


def test_tts_engine_falls_back_local_when_cloud_raises_after_cloud_first(monkeypatch) -> None:
    engine = TTSEngine()
    local_calls = {"count": 0}

    def _fake_local(text, *, interrupt_event=None):  # noqa: ARG001
        local_calls["count"] += 1
        return {"completion_status": "success", "interrupted": False}

    async def _raise_cloud(text, *, interrupt_event=None):  # noqa: ARG001
        raise RuntimeError("edge handshake rejected")

    monkeypatch.setattr(engine, "_speak_local_engine", _fake_local)
    monkeypatch.setattr(engine, "_speak_with_edge_async", _raise_cloud)

    result = engine.speak("hello cloud failure")

    assert result["completion_status"] == "success"
    assert result["degraded_mode"] is True
    assert result["degraded_reason"] == "cloud_tts_failed_fell_back_local"
    assert local_calls["count"] == 1


def test_tts_engine_uses_espeak_ng_local_backend_on_linux(monkeypatch) -> None:
    monkeypatch.setenv("EGB_TTS_LOCAL_BACKEND", "espeak-ng")
    monkeypatch.setenv("EGB_TTS_ESPEAK_NG_PATH", "/usr/bin/espeak-ng")
    monkeypatch.setattr(tts_engine_module.os, "name", "posix")

    class _FinishedProcess:
        returncode = 0

        def poll(self):
            return 0

        def wait(self, timeout=None):  # noqa: ARG002
            return 0

    launches: list[list[str]] = []

    def _fake_popen(args, **_kwargs):
        launches.append(list(args))
        return _FinishedProcess()

    monkeypatch.setattr(tts_engine_module.subprocess, "Popen", _fake_popen)
    engine = TTSEngine()

    result = engine._speak_local_engine("Assistant ready.")

    assert result == {"completion_status": "success", "interrupted": False}
    assert launches == [["/usr/bin/espeak-ng", "-s", "175", "-v", "en-us", "Assistant ready."]]


def test_tts_engine_can_disable_espeak_local_backend_on_linux(monkeypatch) -> None:
    monkeypatch.setenv("EGB_TTS_LOCAL_BACKEND", "disabled")
    monkeypatch.setattr(tts_engine_module.os, "name", "posix")
    engine = TTSEngine()

    result = engine._speak_local_engine("Assistant ready.")

    assert result is None


def test_tts_engine_prefers_azure_when_enabled(monkeypatch) -> None:
    engine = TTSEngine()
    engine._azure_tts_enabled = True
    calls: list[str] = []

    async def _fake_azure(text, *, interrupt_event=None):  # noqa: ARG001
        calls.append("azure")
        return {"completion_status": "success", "interrupted": False}

    async def _fake_edge(text, *, interrupt_event=None):  # noqa: ARG001
        calls.append("edge")
        return {"completion_status": "success", "interrupted": False}

    monkeypatch.setattr(engine, "_speak_with_azure_async", _fake_azure)
    monkeypatch.setattr(engine, "_speak_with_edge_async", _fake_edge)

    result = engine.speak("hello from azure")
    assert result["completion_status"] == "success"
    assert calls == ["azure"]


def test_tts_engine_falls_back_to_edge_when_azure_fails(monkeypatch) -> None:
    engine = TTSEngine()
    engine._azure_tts_enabled = True
    calls: list[str] = []

    async def _fake_azure(text, *, interrupt_event=None):  # noqa: ARG001
        calls.append("azure")
        return {
            "completion_status": "failed",
            "interrupted": False,
            "degraded_mode": True,
            "degraded_reason": "azure_tts_canceled",
        }

    async def _fake_edge(text, *, interrupt_event=None):  # noqa: ARG001
        calls.append("edge")
        return {"completion_status": "success", "interrupted": False}

    monkeypatch.setattr(engine, "_speak_with_azure_async", _fake_azure)
    monkeypatch.setattr(engine, "_speak_with_edge_async", _fake_edge)

    result = engine.speak("fallback to edge")
    assert result["completion_status"] == "success"
    assert calls == ["azure", "edge"]
