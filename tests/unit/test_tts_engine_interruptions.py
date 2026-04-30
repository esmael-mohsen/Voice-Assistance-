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
