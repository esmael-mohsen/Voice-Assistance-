"""High-quality neural TTS powered by Microsoft Edge voices."""

import asyncio
import os
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
import subprocess
import threading
import time
from typing import Callable
import uuid

try:
    import ctypes
except ModuleNotFoundError:  # pragma: no cover - ctypes should exist on CPython
    ctypes = None

try:
    import edge_tts
except ModuleNotFoundError:  # pragma: no cover - exercised only in lean test envs
    edge_tts = None

try:
    from playsound import playsound as _playsound
except ModuleNotFoundError:  # pragma: no cover - exercised only in lean test envs
    def _playsound(path: str, block: bool = True) -> None:  # noqa: ARG001
        return None

logger = logging.getLogger(__name__)

_SPEECH_PRIORITY_RANK: dict[str, int] = {
    "warning": 0,
    "action_confirmation": 1,
    "error": 2,
    "info": 3,
}


def _contains_arabic_characters(text: str) -> bool:
    for ch in text:
        codepoint = ord(ch)
        if (
            0x0600 <= codepoint <= 0x06FF
            or 0x0750 <= codepoint <= 0x077F
            or 0x08A0 <= codepoint <= 0x08FF
            or 0xFB50 <= codepoint <= 0xFDFF
            or 0xFE70 <= codepoint <= 0xFEFF
        ):
            return True
    return False


def _winmm_supported() -> bool:
    if os.name != "nt" or ctypes is None:
        return False
    try:
        winmm = ctypes.windll.winmm
    except Exception:  # noqa: BLE001
        return False
    return hasattr(winmm, "mciSendStringW")


def _send_mci_command(command: str) -> tuple[int, str]:
    if not _winmm_supported():
        return 1, ""
    buffer = ctypes.create_unicode_buffer(256)
    error = int(ctypes.windll.winmm.mciSendStringW(command, buffer, len(buffer), 0))
    return error, str(buffer.value or "").strip()


class TTSEngine:
    def __init__(
        self,
        *,
        playback_runner=None,
        poll_interval_s: float = 0.01,
        prefer_local_engine: bool = True,
        allow_cloud_fallback: bool = True,
        allow_non_interruptible_fallback: bool = False,
    ):
        self.language = "en-US"
        self.gender = "female"
        self.speed = 1.0
        self.voice_id = "en-US-JennyNeural"
        self._rate = "+0%"
        self._pitch = "+2Hz"
        self._volume = "+0%"
        self._interrupt_requested = threading.Event()
        self._playback_runner = playback_runner
        self._poll_interval_s = max(0.001, float(poll_interval_s))
        self._playback_stop_lock = threading.Lock()
        self._playback_stop_callback: Callable[[], None] | None = None
        self._prefer_local_engine = bool(prefer_local_engine) and playback_runner is None
        self._allow_cloud_fallback = bool(allow_cloud_fallback)
        self._allow_non_interruptible_fallback = bool(allow_non_interruptible_fallback)
        self._active_local_process_lock = threading.Lock()
        self._active_local_process: subprocess.Popen[str] | None = None
        self._speak_state = threading.Condition()
        self._speech_active = False
        self._active_priority_rank = max(_SPEECH_PRIORITY_RANK.values()) + 1

    def configure(self, language=None, gender=None, speed=None, voice_id=None, pitch=None, volume=None):
        if language:
            self.language = language
        if gender:
            self.gender = gender
        if voice_id:
            self.voice_id = voice_id
        if speed is not None:
            self.set_speech_speed(speed)
        if pitch is not None:
            self.set_pitch(pitch)
        if volume is not None:
            self.set_volume(volume)
        logger.info(
            "[TTS] Configured (voice=%s, speed=%.2f)",
            self.voice_id,
            self.speed,
        )

    def set_language(self, language):
        self.language = language
        logger.info("[TTS] Language context set to %s", language)

    def set_voice_gender(self, gender):
        self.gender = gender
        logger.info("[TTS] Voice gender context set to %s", gender)

    def set_voice_profile(self, voice_id):
        if voice_id:
            self.voice_id = voice_id
            logger.info("[TTS] Voice profile switched to %s", voice_id)

    def set_speech_speed(self, speed):
        self.speed = speed
        rate_percent = int((speed - 1.0) * 100)
        self._rate = f"{rate_percent:+d}%"
        logger.info("[TTS] Speech speed set to %.2f (%s)", speed, self._rate)

    def set_pitch(self, pitch: str):
        # Edge TTS format: '+0Hz', '-2Hz', '+4Hz'
        if pitch:
            self._pitch = pitch

    def set_volume(self, volume: str):
        # Edge TTS format: '+0%', '+10%', '-5%'
        if volume:
            self._volume = volume

    def _priority_rank(self, priority: str | None) -> int:
        key = str(priority or "info").strip().lower()
        return _SPEECH_PRIORITY_RANK.get(key, _SPEECH_PRIORITY_RANK["info"])

    def _set_active_local_process(self, process: subprocess.Popen[str] | None) -> None:
        with self._active_local_process_lock:
            self._active_local_process = process

    def _terminate_active_local_process(self) -> None:
        with self._active_local_process_lock:
            process = self._active_local_process
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=0.2)
        except Exception:  # noqa: BLE001
            try:
                process.kill()
            except Exception:  # noqa: BLE001
                logger.exception("[TTS] Failed to terminate local TTS process")
        finally:
            self._set_active_local_process(None)

    def request_stop(self) -> None:
        self._interrupt_requested.set()
        self._terminate_active_local_process()
        callback: Callable[[], None] | None
        with self._playback_stop_lock:
            callback = self._playback_stop_callback
        if callback is not None:
            try:
                callback()
            except Exception:  # noqa: BLE001
                logger.exception("[TTS] Native playback stop callback failed")

    def clear_stop_request(self) -> None:
        self._interrupt_requested.clear()

    def _set_playback_stop_callback(self, callback: Callable[[], None] | None) -> None:
        with self._playback_stop_lock:
            self._playback_stop_callback = callback

    def _clear_playback_stop_callback(self) -> None:
        self._set_playback_stop_callback(None)

    def speak(
        self,
        text,
        *,
        max_duration_s: float | None = None,
        interrupt_event: threading.Event | None = None,
        priority: str = "info",
        preempt: bool = False,
    ):
        if not text:
            return {"completion_status": "skipped", "duration_ms": 0, "interrupted": False}

        requested_rank = self._priority_rank(priority)
        with self._speak_state:
            if self._speech_active and (preempt or requested_rank < self._active_priority_rank):
                self.request_stop()
            while self._speech_active:
                self._speak_state.wait(timeout=self._poll_interval_s)
            self._speech_active = True
            self._active_priority_rank = requested_rank

        self.clear_stop_request()
        timeout_timer: threading.Timer | None = None
        if max_duration_s is not None and float(max_duration_s) > 0:
            timeout_timer = threading.Timer(float(max_duration_s), self.request_stop)
            timeout_timer.daemon = True
            timeout_timer.start()

        started_at = time.perf_counter()
        interrupted = False
        checker = getattr(interrupt_event, "is_set", None) if interrupt_event is not None else None
        try:
            if callable(checker) and checker():
                interrupted = True
                return {"completion_status": "interrupted", "duration_ms": 0, "interrupted": True}
            playback_result = self._speak_preferred(text, interrupt_event=interrupt_event)
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            if self._interrupt_requested.is_set() or playback_result.get("interrupted"):
                interrupted = True
            if callable(checker) and checker():
                interrupted = True
            if interrupted:
                completion = playback_result.get("completion_status", "interrupted")
                if completion == "success":
                    completion = "interrupted"
                return {
                    "completion_status": completion,
                    "duration_ms": duration_ms,
                    "interrupted": True,
                    "degraded_mode": bool(playback_result.get("degraded_mode", False)),
                    "degraded_reason": playback_result.get("degraded_reason"),
                }
            if timeout_timer is not None and duration_ms >= int(float(max_duration_s) * 1000):
                return {
                    "completion_status": "timeout",
                    "duration_ms": duration_ms,
                    "interrupted": False,
                }
            return {
                "completion_status": playback_result.get("completion_status", "success"),
                "duration_ms": duration_ms,
                "interrupted": False,
                "degraded_mode": bool(playback_result.get("degraded_mode", False)),
                "degraded_reason": playback_result.get("degraded_reason"),
            }
        finally:
            if timeout_timer is not None:
                timeout_timer.cancel()
            self._set_active_local_process(None)
            with self._speak_state:
                self._speech_active = False
                self._active_priority_rank = max(_SPEECH_PRIORITY_RANK.values()) + 1
                self._speak_state.notify_all()

    def _speak_preferred(
        self,
        text: str,
        *,
        interrupt_event: threading.Event | None,
    ) -> dict[str, object]:
        cloud_preferred_reason = self._cloud_preferred_reason(text)
        use_local_first = self._prefer_local_engine
        if use_local_first and cloud_preferred_reason is not None and self._allow_cloud_fallback:
            use_local_first = False
            logger.info(
                "[TTS] Backend selection=cloud_first reason=%s (language=%s voice=%s)",
                cloud_preferred_reason,
                self.language,
                self.voice_id,
            )

        if use_local_first:
            local_result = self._speak_local_engine(text, interrupt_event=interrupt_event)
            if local_result is not None:
                logger.info("[TTS] Backend completed=local_sapi status=%s", local_result.get("completion_status"))
                return local_result
            logger.info("[TTS] Local backend unavailable; attempting cloud fallback")
        if self._allow_cloud_fallback:
            try:
                cloud_result = asyncio.run(self._speak_async(text, interrupt_event=interrupt_event))
            except RuntimeError:
                loop = asyncio.new_event_loop()
                cloud_result = loop.run_until_complete(self._speak_async(text, interrupt_event=interrupt_event))
                loop.close()
            if not use_local_first and cloud_result.get("completion_status") == "failed" and self._prefer_local_engine:
                logger.warning(
                    "[TTS] Cloud backend failed after cloud-first selection; attempting best-effort local fallback"
                )
                local_fallback = self._speak_local_engine(text, interrupt_event=interrupt_event)
                if local_fallback is not None:
                    return {
                        **local_fallback,
                        "degraded_mode": True,
                        "degraded_reason": "cloud_tts_failed_fell_back_local",
                    }
            return cloud_result
        return {
            "completion_status": "failed",
            "interrupted": False,
            "degraded_mode": True,
            "degraded_reason": "local_tts_unavailable",
        }

    def _cloud_preferred_reason(self, text: str) -> str | None:
        language = str(self.language or "").strip().lower()
        voice_id = str(self.voice_id or "").strip().lower()
        if _contains_arabic_characters(str(text or "")):
            return "arabic_text"
        if language.startswith("ar"):
            return "arabic_language"
        if "neural" in voice_id:
            return "neural_voice_profile"
        return None

    def _speak_local_engine(
        self,
        text: str,
        *,
        interrupt_event: threading.Event | None = None,
    ) -> dict[str, object] | None:
        if os.name != "nt":
            return None
        checker = getattr(interrupt_event, "is_set", None) if interrupt_event is not None else None
        if self._interrupt_requested.is_set() or (callable(checker) and checker()):
            return {"completion_status": "interrupted", "interrupted": True}

        voice_id = str(self.voice_id or "").replace("'", "''")
        escaped_text = str(text).replace("'", "''")
        rate_value = max(-10, min(10, int(round((float(self.speed) - 1.0) * 8))))
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$tts = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            f"$tts.Rate = {rate_value};"
            f"if ('{voice_id}' -ne '') {{ try {{ $tts.SelectVoice('{voice_id}') }} catch {{ }} }};"
            f"$tts.Speak('{escaped_text}');"
            "$tts.Dispose();"
        )
        try:
            process = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except Exception:  # noqa: BLE001
            logger.exception("[TTS] Failed to start local SAPI speech process")
            return None

        self._set_active_local_process(process)
        while process.poll() is None:
            if self._interrupt_requested.is_set() or (callable(checker) and checker()):
                self._terminate_active_local_process()
                return {
                    "completion_status": "interrupted",
                    "interrupted": True,
                    "degraded_mode": False,
                    "degraded_reason": None,
                }
            time.sleep(self._poll_interval_s)
        self._set_active_local_process(None)
        if process.returncode == 0:
            return {"completion_status": "success", "interrupted": False}
        logger.warning("[TTS] Local SAPI process exited with return code %s", process.returncode)
        return None

    async def _speak_async(self, text, *, interrupt_event: threading.Event | None = None):
        logger.info("[TTS] Backend selected=edge_tts voice=%s language=%s", self.voice_id, self.language)
        if edge_tts is None:
            logger.warning("[TTS] edge_tts is unavailable; skipping cloud synthesis")
            if self._playback_runner is not None:
                result = self._playback_runner(
                    path="edge_tts_unavailable.mp3",
                    stop_event=self._interrupt_requested,
                    interrupt_event=interrupt_event,
                )
                if isinstance(result, dict):
                    return result
                return {"completion_status": "success", "interrupted": False}
            return {
                "completion_status": "failed",
                "interrupted": False,
                "degraded_mode": True,
                "degraded_reason": "edge_tts_unavailable",
            }
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice_id,
            rate=self._rate,
            pitch=self._pitch,
            volume=self._volume,
        )
        with NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            temp_path = Path(tmp_file.name)
        try:
            await communicate.save(str(temp_path))
            return self._play_audio_file(temp_path, interrupt_event=interrupt_event)
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("[TTS] Unable to delete temp file %s", temp_path)

    def _play_audio_file(self, temp_path: Path, *, interrupt_event: threading.Event | None = None) -> dict[str, object]:
        if self._playback_runner is not None:
            result = self._playback_runner(
                path=str(temp_path),
                stop_event=self._interrupt_requested,
                interrupt_event=interrupt_event,
            )
            if isinstance(result, dict):
                return result
            return {"completion_status": "success", "interrupted": False}

        winmm_result = self._play_audio_file_with_winmm(temp_path, interrupt_event=interrupt_event)
        if winmm_result is not None:
            return winmm_result

        if not self._allow_non_interruptible_fallback:
            logger.warning(
                "[TTS] Skipping non-interruptible playback fallback because interruptible backend is unavailable"
            )
            return {
                "completion_status": "failed",
                "interrupted": False,
                "degraded_mode": True,
                "degraded_reason": "interruptible_playback_unavailable",
            }

        completed = threading.Event()

        def _playback() -> None:
            try:
                _playsound(str(temp_path), block=True)
            finally:
                completed.set()

        thread = threading.Thread(target=_playback, name="TTSEnginePlayback", daemon=True)
        thread.start()
        checker = getattr(interrupt_event, "is_set", None) if interrupt_event is not None else None
        while not completed.is_set():
            if self._interrupt_requested.is_set() or (callable(checker) and checker()):
                return {
                    "completion_status": "interrupted",
                    "interrupted": True,
                    "degraded_mode": True,
                    "degraded_reason": "non_interruptible_playback",
                }
            time.sleep(self._poll_interval_s)
        thread.join(timeout=self._poll_interval_s)
        return {"completion_status": "success", "interrupted": False}

    def _play_audio_file_with_winmm(
        self,
        temp_path: Path,
        *,
        interrupt_event: threading.Event | None = None,
    ) -> dict[str, object] | None:
        if not _winmm_supported():
            return None

        alias = f"tts_{uuid.uuid4().hex}"
        media_path = str(temp_path).replace('"', "")
        open_error, _ = _send_mci_command(f'open "{media_path}" type mpegvideo alias {alias}')
        if open_error != 0:
            return None

        def _native_stop() -> None:
            _send_mci_command(f"stop {alias}")

        try:
            play_error, _ = _send_mci_command(f"play {alias} from 0")
            if play_error != 0:
                return None

            self._set_playback_stop_callback(_native_stop)
            checker = getattr(interrupt_event, "is_set", None) if interrupt_event is not None else None

            while True:
                if self._interrupt_requested.is_set() or (callable(checker) and checker()):
                    _native_stop()
                    return {"completion_status": "interrupted", "interrupted": True}

                status_error, status_mode = _send_mci_command(f"status {alias} mode")
                if status_error != 0:
                    return {"completion_status": "success", "interrupted": False}

                normalized_mode = str(status_mode or "").strip().lower()
                if normalized_mode in {"stopped", "not ready", ""}:
                    return {"completion_status": "success", "interrupted": False}

                time.sleep(self._poll_interval_s)
        finally:
            self._clear_playback_stop_callback()
            _send_mci_command(f"close {alias}")
