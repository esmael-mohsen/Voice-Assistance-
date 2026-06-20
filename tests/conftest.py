"""Shared pytest fixtures and doubles for runtime extraction tests."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import pytest

from core.command_models import CommandRecognitionResult
from core.critical_prompts import build_default_critical_prompt_catalog, surface_binding_payloads
import settings.settings_manager as settings_module
from settings.settings_manager import settings_manager


@dataclass(frozen=True)
class SettingsManagerSnapshot:
    """Captures mutable settings-manager state so each test can restore it."""

    username: str
    language: str
    voice_gender: str
    default_speech_speed: float
    speech_speed: float
    speech_provider: str
    pending_speech_provider: str | None
    deferred_provider_switch: bool
    min_speech_speed: float
    max_speech_speed: float
    listener: Any
    tts_engine: Any
    profile_loaded: bool
    voice_profiles: dict[tuple[str, str], str]
    default_voice: str
    max_listen_seconds: float
    max_speak_seconds: float
    priority_coalescing_window_s: float
    concise_word_limit: int
    offline_allowlisted_capabilities: set[str]
    network_available: bool
    network_override_mode: str
    connectivity_detected_status: str
    connectivity_last_confirmed_status: str
    connectivity_last_confirmed_at: float | None
    connectivity_grace_window_deadline_at: float | None
    connectivity_probe_generation: int
    connectivity_startup_reset_applied: bool
    connectivity_grace_window_s: float
    wake_primary_mode: str
    wake_fallback_mode: str
    wake_dev_fallback_mode: str
    stt_wake_allowed_in_production: bool
    low_power_standby_enabled: bool
    non_speech_cues_enabled: bool
    command_confidence_high_threshold: float
    command_confidence_medium_threshold: float
    command_protected_threshold: float
    command_allow_missing_confidence_for_unprotected: bool
    command_max_retry_cycles: int
    command_fallback_enabled: bool
    command_rescue_enabled: bool
    command_offline_local_allowed: bool
    standby_capture_profile_id: str
    onboarding_capture_profile_id: str
    command_capture_profile_id: str
    confirmation_capture_profile_id: str
    closed_vocabulary_retry_limit: int
    speech_qualification_profile: str
    enable_audio_noise_suppression: bool
    enable_capture_relisten: bool
    enable_dictionary_bias: bool
    critical_prompt_catalog: dict[str, dict[str, str]]
    repaired_prompt_keys: set[str]
    release_threshold_policy: dict[str, dict[str, float]]
    release_artifact_retention_days: int


def _capture_settings_snapshot() -> SettingsManagerSnapshot:
    return SettingsManagerSnapshot(
        username=settings_manager.username,
        language=settings_manager.language,
        voice_gender=settings_manager.voice_gender,
        default_speech_speed=settings_manager.default_speech_speed,
        speech_speed=settings_manager.speech_speed,
        speech_provider=settings_manager.speech_provider,
        pending_speech_provider=settings_manager.pending_speech_provider,
        deferred_provider_switch=settings_manager.deferred_provider_switch,
        min_speech_speed=settings_manager.min_speech_speed,
        max_speech_speed=settings_manager.max_speech_speed,
        listener=settings_manager._listener,
        tts_engine=settings_manager._tts_engine,
        profile_loaded=settings_manager._profile_loaded,
        voice_profiles=deepcopy(settings_manager._voice_profiles),
        default_voice=settings_manager._default_voice,
        max_listen_seconds=float(getattr(settings_manager, "max_listen_seconds", 8.0)),
        max_speak_seconds=float(getattr(settings_manager, "max_speak_seconds", 8.0)),
        priority_coalescing_window_s=float(getattr(settings_manager, "priority_coalescing_window_s", 2.0)),
        concise_word_limit=int(getattr(settings_manager, "concise_word_limit", 12)),
        offline_allowlisted_capabilities=set(
            getattr(settings_manager, "offline_allowlisted_capabilities", {"system_status"})
        ),
        network_available=bool(getattr(settings_manager, "network_available", True)),
        network_override_mode=str(getattr(settings_manager, "network_override_mode", "auto")),
        connectivity_detected_status=str(getattr(settings_manager, "connectivity_detected_status", "online")),
        connectivity_last_confirmed_status=str(
            getattr(settings_manager, "connectivity_last_confirmed_status", "online")
        ),
        connectivity_last_confirmed_at=getattr(settings_manager, "connectivity_last_confirmed_at", None),
        connectivity_grace_window_deadline_at=getattr(
            settings_manager,
            "connectivity_grace_window_deadline_at",
            None,
        ),
        connectivity_probe_generation=int(getattr(settings_manager, "connectivity_probe_generation", 0)),
        connectivity_startup_reset_applied=bool(
            getattr(settings_manager, "connectivity_startup_reset_applied", False)
        ),
        connectivity_grace_window_s=float(getattr(settings_manager, "connectivity_grace_window_s", 2.0)),
        wake_primary_mode=str(getattr(settings_manager, "wake_primary_mode", "keyword_low_power")),
        wake_fallback_mode=str(getattr(settings_manager, "wake_fallback_mode", "hardware_trigger")),
        wake_dev_fallback_mode=str(getattr(settings_manager, "wake_dev_fallback_mode", "stt_based_wake")),
        stt_wake_allowed_in_production=bool(
            getattr(settings_manager, "stt_wake_allowed_in_production", False)
        ),
        low_power_standby_enabled=bool(getattr(settings_manager, "low_power_standby_enabled", True)),
        non_speech_cues_enabled=bool(getattr(settings_manager, "non_speech_cues_enabled", True)),
        command_confidence_high_threshold=float(
            getattr(settings_manager, "command_confidence_high_threshold", 0.82)
        ),
        command_confidence_medium_threshold=float(
            getattr(settings_manager, "command_confidence_medium_threshold", 0.55)
        ),
        command_protected_threshold=float(getattr(settings_manager, "command_protected_threshold", 0.9)),
        command_allow_missing_confidence_for_unprotected=bool(
            getattr(settings_manager, "command_allow_missing_confidence_for_unprotected", True)
        ),
        command_max_retry_cycles=int(getattr(settings_manager, "command_max_retry_cycles", 1)),
        command_fallback_enabled=bool(getattr(settings_manager, "command_fallback_enabled", True)),
        command_rescue_enabled=bool(
            getattr(
                settings_manager,
                "command_rescue_enabled",
                getattr(settings_manager, "command_fallback_enabled", True),
            )
        ),
        command_offline_local_allowed=bool(getattr(settings_manager, "command_offline_local_allowed", True)),
        standby_capture_profile_id=str(
            getattr(settings_manager, "standby_capture_profile_id", "standby_wake.default")
        ),
        onboarding_capture_profile_id=str(
            getattr(settings_manager, "onboarding_capture_profile_id", "onboarding.default")
        ),
        command_capture_profile_id=str(
            getattr(settings_manager, "command_capture_profile_id", "command.default")
        ),
        confirmation_capture_profile_id=str(
            getattr(settings_manager, "confirmation_capture_profile_id", "confirmation.default")
        ),
        closed_vocabulary_retry_limit=int(getattr(settings_manager, "closed_vocabulary_retry_limit", 1)),
        speech_qualification_profile=str(
            getattr(settings_manager, "speech_qualification_profile", "default")
        ),
        enable_audio_noise_suppression=bool(
            getattr(settings_manager, "enable_audio_noise_suppression", False)
        ),
        enable_capture_relisten=bool(getattr(settings_manager, "enable_capture_relisten", True)),
        enable_dictionary_bias=bool(getattr(settings_manager, "enable_dictionary_bias", True)),
        critical_prompt_catalog=deepcopy(getattr(settings_manager, "_critical_prompt_catalog", {})),
        repaired_prompt_keys=set(getattr(settings_manager, "_repaired_prompt_keys", set())),
        release_threshold_policy=deepcopy(getattr(settings_manager, "release_threshold_policy", {})),
        release_artifact_retention_days=int(getattr(settings_manager, "release_artifact_retention_days", 180)),
    )


def _restore_settings_snapshot(snapshot: SettingsManagerSnapshot) -> None:
    settings_manager.username = snapshot.username
    settings_manager.language = snapshot.language
    settings_manager.voice_gender = snapshot.voice_gender
    settings_manager.default_speech_speed = snapshot.default_speech_speed
    settings_manager.speech_speed = snapshot.speech_speed
    settings_manager.speech_provider = snapshot.speech_provider
    settings_manager.pending_speech_provider = snapshot.pending_speech_provider
    settings_manager.deferred_provider_switch = snapshot.deferred_provider_switch
    settings_manager.min_speech_speed = snapshot.min_speech_speed
    settings_manager.max_speech_speed = snapshot.max_speech_speed
    settings_manager._listener = snapshot.listener
    settings_manager._tts_engine = snapshot.tts_engine
    settings_manager._profile_loaded = snapshot.profile_loaded
    settings_manager._voice_profiles = deepcopy(snapshot.voice_profiles)
    settings_manager._default_voice = snapshot.default_voice
    settings_manager.max_listen_seconds = snapshot.max_listen_seconds
    settings_manager.max_speak_seconds = snapshot.max_speak_seconds
    settings_manager.priority_coalescing_window_s = snapshot.priority_coalescing_window_s
    settings_manager.concise_word_limit = snapshot.concise_word_limit
    settings_manager.offline_allowlisted_capabilities = set(snapshot.offline_allowlisted_capabilities)
    settings_manager.network_available = snapshot.network_available
    settings_manager.network_override_mode = snapshot.network_override_mode
    settings_manager.connectivity_detected_status = snapshot.connectivity_detected_status
    settings_manager.connectivity_last_confirmed_status = snapshot.connectivity_last_confirmed_status
    settings_manager.connectivity_last_confirmed_at = snapshot.connectivity_last_confirmed_at
    settings_manager.connectivity_grace_window_deadline_at = snapshot.connectivity_grace_window_deadline_at
    settings_manager.connectivity_probe_generation = snapshot.connectivity_probe_generation
    settings_manager.connectivity_startup_reset_applied = snapshot.connectivity_startup_reset_applied
    settings_manager.connectivity_grace_window_s = snapshot.connectivity_grace_window_s
    settings_manager.wake_primary_mode = snapshot.wake_primary_mode
    settings_manager.wake_fallback_mode = snapshot.wake_fallback_mode
    settings_manager.wake_dev_fallback_mode = snapshot.wake_dev_fallback_mode
    settings_manager.stt_wake_allowed_in_production = snapshot.stt_wake_allowed_in_production
    settings_manager.low_power_standby_enabled = snapshot.low_power_standby_enabled
    settings_manager.non_speech_cues_enabled = snapshot.non_speech_cues_enabled
    settings_manager.command_confidence_high_threshold = snapshot.command_confidence_high_threshold
    settings_manager.command_confidence_medium_threshold = snapshot.command_confidence_medium_threshold
    settings_manager.command_protected_threshold = snapshot.command_protected_threshold
    settings_manager.command_allow_missing_confidence_for_unprotected = (
        snapshot.command_allow_missing_confidence_for_unprotected
    )
    settings_manager.command_max_retry_cycles = snapshot.command_max_retry_cycles
    settings_manager.command_fallback_enabled = snapshot.command_fallback_enabled
    settings_manager.command_rescue_enabled = snapshot.command_rescue_enabled
    settings_manager.command_offline_local_allowed = snapshot.command_offline_local_allowed
    settings_manager.standby_capture_profile_id = snapshot.standby_capture_profile_id
    settings_manager.onboarding_capture_profile_id = snapshot.onboarding_capture_profile_id
    settings_manager.command_capture_profile_id = snapshot.command_capture_profile_id
    settings_manager.confirmation_capture_profile_id = snapshot.confirmation_capture_profile_id
    settings_manager.closed_vocabulary_retry_limit = snapshot.closed_vocabulary_retry_limit
    settings_manager.speech_qualification_profile = snapshot.speech_qualification_profile
    settings_manager.enable_audio_noise_suppression = snapshot.enable_audio_noise_suppression
    settings_manager.enable_capture_relisten = snapshot.enable_capture_relisten
    settings_manager.enable_dictionary_bias = snapshot.enable_dictionary_bias
    settings_manager._critical_prompt_catalog = deepcopy(snapshot.critical_prompt_catalog)
    settings_manager._repaired_prompt_keys = set(snapshot.repaired_prompt_keys)
    settings_manager.release_threshold_policy = deepcopy(snapshot.release_threshold_policy)
    settings_manager.release_artifact_retention_days = snapshot.release_artifact_retention_days


class EventSink:
    """Queue-like sink that records all emitted events."""

    def __init__(self) -> None:
        self.events: list[Any] = []

    def put(self, event: Any) -> None:
        self.events.append(event)


class FakeClock:
    """Deterministic monotonic clock for wearable runtime tests."""

    def __init__(self, *, start: float = 0.0) -> None:
        self._value = float(start)

    def now(self) -> float:
        return self._value

    def advance(self, seconds: float) -> None:
        self._value += max(0.0, float(seconds))


class FakeNetworkState:
    """Simple mutable network state toggle."""

    def __init__(self, *, available: bool = True) -> None:
        self.available = bool(available)

    def set_available(self, available: bool) -> None:
        self.available = bool(available)


class FakeWakeSignalStream:
    """Queued wearable wake/interrupt signal source."""

    def __init__(self, signals: list[str] | None = None) -> None:
        self._signals = list(signals or [])

    def emit(self, signal: str) -> None:
        self._signals.append(signal)

    def next_signal(self) -> str | None:
        if not self._signals:
            return None
        return self._signals.pop(0)


class FakeVoiceListener:
    """Deterministic stand-in for the speech listener."""

    def __init__(
        self,
        default_language: str = "en-US",
        command_responses: list[str | None] | None = None,
        any_responses: list[str | None] | None = None,
        command_result_responses: list[CommandRecognitionResult | dict[str, Any] | None] | None = None,
    ) -> None:
        self.language = default_language
        self.command_responses = list(command_responses or [])
        self.any_responses = list(any_responses or [])
        self.command_result_responses = list(command_result_responses or [])
        self.listen_command_calls = 0
        self.listen_command_result_calls: list[dict[str, Any]] = []
        self.listen_any_calls: list[dict[str, Any]] = []
        self.set_language_calls: list[str] = []

    def set_language(self, language_code: str) -> None:
        self.language = language_code
        self.set_language_calls.append(language_code)

    def listen_command(self, **_kwargs: Any) -> str | None:
        self.listen_command_calls += 1
        if self.command_responses:
            return self.command_responses.pop(0)
        if self.command_result_responses:
            scripted = self.command_result_responses.pop(0)
            if scripted is None:
                return None
            if isinstance(scripted, CommandRecognitionResult):
                return scripted.primary_transcript if not scripted.error_code else None
            if isinstance(scripted, dict):
                if scripted.get("error_code"):
                    return None
                return str(scripted.get("primary_transcript", "") or "") or None
        return None

    def listen_command_result(self, **kwargs: Any) -> CommandRecognitionResult | None:
        self.listen_command_result_calls.append(dict(kwargs))
        usage_mode = str(kwargs.get("usage_mode", "command") or "command").strip().lower()
        if usage_mode == "standby_wake":
            if self.command_result_responses:
                scripted = self.command_result_responses.pop(0)
                if scripted is None:
                    return None
                if isinstance(scripted, CommandRecognitionResult):
                    return scripted
                if isinstance(scripted, dict):
                    payload = dict(scripted)
                    payload.setdefault("session_id", "fixture-session")
                    payload.setdefault("recognition_path", "local_first")
                    payload.setdefault("provider_id", "legacy")
                    payload.setdefault("primary_transcript", "")
                    payload.setdefault("confidence_available", False)
                    payload.setdefault("confidence_score", None)
                    payload.setdefault("alternative_transcripts", ())
                    payload.setdefault("detected_language", self.language)
                    payload.setdefault("selected_language", self.language)
                    payload.setdefault("latency_ms", 0)
                    payload.setdefault("error_code", None)
                    payload.setdefault("recognition_source", "legacy_local")
                    payload.setdefault("profile_id", str(kwargs.get("capture_profile_id", "standby_wake.default")))
                    payload["alternative_transcripts"] = tuple(payload.get("alternative_transcripts", ()))
                    return CommandRecognitionResult(**payload)
            languages = list(kwargs.get("languages") or [self.language])
            text = self.listen_any(
                languages,
                prompt=str(kwargs.get("prompt", "[STT] Wake listening...")),
                timeout=int(kwargs.get("timeout", kwargs.get("timeout_s", 7)) or 7),
                phrase_time_limit=int(
                    kwargs.get("phrase_time_limit", kwargs.get("phrase_time_limit_s", 6)) or 6
                ),
            )
            if not text:
                return None
            return CommandRecognitionResult(
                session_id=str(kwargs.get("session_id", "fixture-session")),
                recognition_path=str(kwargs.get("recognition_path", "local_first") or "local_first"),
                provider_id="legacy",
                primary_transcript=text,
                confidence_score=None,
                confidence_available=False,
                alternative_transcripts=(text,),
                detected_language=self.language,
                selected_language=self.language,
                latency_ms=0,
                error_code=None,
                recognition_source="legacy_local",
                profile_id=str(kwargs.get("capture_profile_id", "standby_wake.default")),
            )
        if self.command_result_responses:
            scripted = self.command_result_responses.pop(0)
            if scripted is None:
                return None
            if isinstance(scripted, CommandRecognitionResult):
                return scripted
            if isinstance(scripted, dict):
                payload = dict(scripted)
                payload.setdefault("session_id", "fixture-session")
                payload.setdefault("recognition_path", "local_first")
                payload.setdefault("provider_id", "legacy")
                payload.setdefault("primary_transcript", "")
                payload.setdefault("confidence_available", False)
                payload.setdefault("confidence_score", None)
                payload.setdefault("alternative_transcripts", ())
                payload.setdefault("detected_language", self.language)
                payload.setdefault("latency_ms", 0)
                payload.setdefault("error_code", None)
                payload["alternative_transcripts"] = tuple(payload.get("alternative_transcripts", ()))
                return CommandRecognitionResult(**payload)

        text = self.listen_command()
        if text is None:
            return None
        return CommandRecognitionResult(
            session_id="fixture-session",
            recognition_path=str(kwargs.get("recognition_path", "local_first") or "local_first"),
            provider_id="legacy",
            primary_transcript=text,
            confidence_score=None,
            confidence_available=False,
            alternative_transcripts=(text,),
            detected_language=self.language,
            latency_ms=0,
            error_code=None,
        )

    def listen_command_window(self, **kwargs: Any) -> str | None:
        result = self.listen_command_result(**kwargs)
        if result is None or result.error_code:
            return None
        return result.primary_transcript

    def listen_any(
        self,
        languages: list[str],
        prompt: str = "[STT] Listening...",
        timeout: int = 7,
        phrase_time_limit: int = 10,
    ) -> str | None:
        self.listen_any_calls.append(
            {
                "languages": list(languages),
                "prompt": prompt,
                "timeout": timeout,
                "phrase_time_limit": phrase_time_limit,
            }
        )
        if not self.any_responses:
            return None
        return self.any_responses.pop(0)


class FakeTTSEngine:
    """Captures TTS configuration and spoken text for assertions."""

    def __init__(
        self,
        *,
        speech_delay_s: float = 0.0,
        degrade_on_interrupt: bool = False,
    ) -> None:
        self.configure_calls: list[dict[str, Any]] = []
        self.language: str | None = None
        self.gender: str | None = None
        self.speed: float | None = None
        self.voice_id: str | None = None
        self.pitch: str | None = None
        self.volume: str | None = None
        self.spoken_texts: list[str] = []
        self.speech_delay_s = max(0.0, float(speech_delay_s))
        self.degrade_on_interrupt = bool(degrade_on_interrupt)
        self._stop_requested = False

    def configure(
        self,
        *,
        language: str,
        gender: str,
        speed: float,
        voice_id: str,
        pitch: str = "+0Hz",
        volume: str = "+0%",
    ) -> None:
        self.language = language
        self.gender = gender
        self.speed = speed
        self.voice_id = voice_id
        self.pitch = pitch
        self.volume = volume
        self.configure_calls.append(
            {
                "language": language,
                "gender": gender,
                "speed": speed,
                "voice_id": voice_id,
                "pitch": pitch,
                "volume": volume,
            }
        )

    def set_language(self, language: str) -> None:
        self.language = language

    def set_voice_gender(self, gender: str) -> None:
        self.gender = gender

    def set_speech_speed(self, speed: float) -> None:
        self.speed = speed

    def set_voice_profile(self, voice_id: str) -> None:
        self.voice_id = voice_id

    def request_stop(self) -> None:
        self._stop_requested = True

    def clear_stop_request(self) -> None:
        self._stop_requested = False

    def speak(
        self,
        text: str,
        *,
        max_duration_s: float | None = None,
        interrupt_event: Any | None = None,
    ) -> dict[str, Any]:
        import time

        self.clear_stop_request()
        self.spoken_texts.append(text)
        checker = getattr(interrupt_event, "is_set", None) if interrupt_event is not None else None
        if self.speech_delay_s > 0:
            started_at = time.perf_counter()
            while (time.perf_counter() - started_at) < self.speech_delay_s:
                if self._stop_requested or (callable(checker) and checker()):
                    return {
                        "completion_status": "interrupted",
                        "duration_ms": int((time.perf_counter() - started_at) * 1000),
                        "interrupted": True,
                        "degraded_mode": self.degrade_on_interrupt,
                        "degraded_reason": "provider_stall" if self.degrade_on_interrupt else None,
                    }
                time.sleep(0.01)
        duration_ms = int(self.speech_delay_s * 1000)
        if max_duration_s is not None and duration_ms > int(max_duration_s * 1000):
            return {"completion_status": "timeout", "duration_ms": duration_ms, "interrupted": False}
        return {"completion_status": "success", "duration_ms": duration_ms, "interrupted": False}


class FakeProviderListener(FakeVoiceListener):
    def __init__(self, *args, available: bool = True, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.available = available

    def is_available(self) -> bool:
        return self.available


class FakeProviderTTSEngine(FakeTTSEngine):
    def __init__(self, *, available: bool = True) -> None:
        super().__init__()
        self.available = available

    def is_available(self) -> bool:
        return self.available


class FakeWakeDetector:
    """Returns scripted wake detections and records input phrases."""

    def __init__(self, responses: list[Any] | None = None) -> None:
        self.responses = list(responses or [])
        self.detect_calls: list[str] = []

    def detect(self, text: str) -> Any:
        self.detect_calls.append(text)
        if not self.responses:
            return None
        return self.responses.pop(0)


class FakeProviderWakeDetector(FakeWakeDetector):
    def __init__(self, *args, available: bool = True, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.available = available

    def is_available(self) -> bool:
        return self.available


class DispatchSpy:
    """Tracks dispatch invocations and returns scripted results."""

    def __init__(self, responses: list[Any] | None = None) -> None:
        self.responses = list(responses or [])
        self.calls: list[str] = []

    def __call__(self, text: str) -> Any:
        self.calls.append(text)
        if not self.responses:
            return None

        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if callable(response):
            return response(text)
        return response


class FakeObstacleAdapter:
    """Controllable adapter double for obstacle capability tests."""

    def __init__(
        self,
        *,
        available: bool = True,
        start_delay_s: float = 0.0,
        stop_delay_s: float = 0.0,
        read_delay_s: float = 0.0,
        fail_on_read: bool = False,
        fail_on_start: bool = False,
        fail_on_stop: bool = False,
        observation: dict[str, Any] | None = None,
    ) -> None:
        self.available = available
        self.active = False
        self.start_delay_s = start_delay_s
        self.stop_delay_s = stop_delay_s
        self.read_delay_s = read_delay_s
        self.fail_on_read = fail_on_read
        self.fail_on_start = fail_on_start
        self.fail_on_stop = fail_on_stop
        self.observation = dict(
            observation
            or {
                "detected": False,
                "distance_meters": 1.2,
                "angle_degrees": 0.0,
                "severity": "clear",
                "confidence": 0.9,
                "sensor_source": "fake_obstacle_adapter",
            }
        )

    def is_available(self) -> bool:
        return self.available

    def start_monitoring(self) -> None:
        import time

        if self.start_delay_s > 0:
            time.sleep(self.start_delay_s)
        if self.fail_on_start:
            raise RuntimeError("start failed")
        self.active = True

    def stop_monitoring(self) -> None:
        import time

        if self.stop_delay_s > 0:
            time.sleep(self.stop_delay_s)
        if self.fail_on_stop:
            raise RuntimeError("stop failed")
        self.active = False

    def read_observation(self, timeout_s: float) -> dict[str, Any] | None:
        import time

        if self.fail_on_read:
            raise RuntimeError("read failed")
        if self.read_delay_s > 0:
            time.sleep(self.read_delay_s)
        if not self.available:
            return None
        observation = dict(self.observation)
        observation.setdefault("captured_at", "2026-04-18T00:00:00Z")
        return observation

    def describe_health(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "active": self.active,
            "sensor_source": "fake_obstacle_adapter",
            "requires_network": False,
        }


class FakeVisionAdapter:
    """Controllable adapter double for face/emotion capability tests."""

    def __init__(
        self,
        *,
        face_available: bool = True,
        emotion_available: bool = True,
        face_delay_s: float = 0.0,
        emotion_delay_s: float = 0.0,
        face_exception: Exception | None = None,
        emotion_exception: Exception | None = None,
        face_response: dict[str, Any] | None = None,
        emotion_response: dict[str, Any] | None = None,
    ) -> None:
        self.face_available = face_available
        self.emotion_available = emotion_available
        self.face_delay_s = face_delay_s
        self.emotion_delay_s = emotion_delay_s
        self.face_exception = face_exception
        self.emotion_exception = emotion_exception
        self.face_response = dict(
            face_response
            or {
                "status": "success",
                "spoken_text": "Face Face_001 recognized.",
                "payload": {
                    "face_id": "Face_001",
                    "allow_emotion_follow_up": True,
                    "identified": True,
                },
            }
        )
        self.emotion_response = dict(
            emotion_response
            or {
                "status": "success",
                "spoken_text": "Detected a happy emotion for Face_001.",
                "payload": {
                    "face_id": "Face_001",
                    "emotion": "Happy",
                },
            }
        )
        self.face_calls: list[dict[str, Any]] = []
        self.emotion_calls: list[dict[str, Any]] = []

    def is_available(self, capability_id: str) -> bool:
        if capability_id == "face_recognition":
            return self.face_available
        if capability_id == "emotion_recognition":
            return self.emotion_available
        return False

    def recognize_face(self, *, store_new_face: bool = False) -> dict[str, Any]:
        import time

        self.face_calls.append({"store_new_face": store_new_face})
        if self.face_delay_s > 0:
            time.sleep(self.face_delay_s)
        if self.face_exception is not None:
            raise self.face_exception
        return dict(self.face_response)

    def recognize_emotion(self, *, face_id: str | None = None) -> dict[str, Any]:
        import time

        self.emotion_calls.append({"face_id": face_id})
        if self.emotion_delay_s > 0:
            time.sleep(self.emotion_delay_s)
        if self.emotion_exception is not None:
            raise self.emotion_exception
        response = dict(self.emotion_response)
        payload = dict(response.get("payload") or {})
        if face_id is not None:
            payload.setdefault("face_id", face_id)
        response["payload"] = payload
        return response

    def describe_health(self) -> dict[str, Any]:
        return {
            "project_path": "fake://vision",
            "project_path_exists": True,
            "camera_index": 0,
            "dependency_error": None,
            "capabilities": {
                "face_recognition": {
                    "available": self.face_available,
                    "error_code": None if self.face_available else "vision_unavailable",
                },
                "emotion_recognition": {
                    "available": self.emotion_available,
                    "error_code": None if self.emotion_available else "vision_unavailable",
                },
            },
        }


@pytest.fixture()
def isolated_settings_manager(monkeypatch: pytest.MonkeyPatch):
    """Resets global settings and disables disk profile I/O for tests."""

    snapshot = _capture_settings_snapshot()
    monkeypatch.setattr(settings_module, "save_profile_snapshot", lambda _profile: None)
    monkeypatch.setattr(settings_module, "load_profile_snapshot", lambda: None)

    settings_manager.username = ""
    settings_manager.language = "ar-EG"
    settings_manager.voice_gender = "female"
    settings_manager.default_speech_speed = 1.0
    settings_manager.speech_speed = 1.0
    settings_manager.speech_provider = "legacy"
    settings_manager.pending_speech_provider = None
    settings_manager.deferred_provider_switch = False
    settings_manager.min_speech_speed = 0.6
    settings_manager.max_speech_speed = 1.6
    settings_manager.max_listen_seconds = 8.0
    settings_manager.max_speak_seconds = 8.0
    settings_manager.priority_coalescing_window_s = 2.0
    settings_manager.concise_word_limit = 12
    settings_manager.offline_allowlisted_capabilities = {"system_status"}
    settings_manager.network_available = True
    settings_manager.network_override_mode = "auto"
    settings_manager.connectivity_detected_status = "online"
    settings_manager.connectivity_last_confirmed_status = "online"
    settings_manager.connectivity_last_confirmed_at = None
    settings_manager.connectivity_grace_window_deadline_at = None
    settings_manager.connectivity_probe_generation = 0
    settings_manager.connectivity_startup_reset_applied = False
    settings_manager.connectivity_grace_window_s = 2.0
    settings_manager.wake_primary_mode = "keyword_low_power"
    settings_manager.wake_fallback_mode = "hardware_trigger"
    settings_manager.wake_dev_fallback_mode = "stt_based_wake"
    settings_manager.stt_wake_allowed_in_production = False
    settings_manager.low_power_standby_enabled = True
    settings_manager.non_speech_cues_enabled = True
    settings_manager.command_confidence_high_threshold = 0.82
    settings_manager.command_confidence_medium_threshold = 0.55
    settings_manager.command_protected_threshold = 0.9
    settings_manager.command_allow_missing_confidence_for_unprotected = True
    settings_manager.command_max_retry_cycles = 1
    settings_manager.command_fallback_enabled = True
    settings_manager.command_rescue_enabled = True
    settings_manager.command_offline_local_allowed = True
    settings_manager.standby_capture_profile_id = "standby_wake.default"
    settings_manager.onboarding_capture_profile_id = "onboarding.default"
    settings_manager.command_capture_profile_id = "command.default"
    settings_manager.confirmation_capture_profile_id = "confirmation.default"
    settings_manager.closed_vocabulary_retry_limit = 1
    settings_manager.speech_qualification_profile = "default"
    settings_manager.enable_audio_noise_suppression = False
    settings_manager.enable_capture_relisten = True
    settings_manager.enable_dictionary_bias = True
    settings_manager._critical_prompt_catalog = build_default_critical_prompt_catalog()
    settings_manager._repaired_prompt_keys = set()
    settings_manager.release_threshold_policy = {
        "wake_to_listen": {"threshold_ms": 100.0, "threshold_pct": 15.0},
        "listen_to_result": {"threshold_ms": 120.0, "threshold_pct": 15.0},
        "result_to_speech_start": {"threshold_ms": 100.0, "threshold_pct": 15.0},
    }
    settings_manager.release_artifact_retention_days = 180
    settings_manager._listener = None
    settings_manager._tts_engine = None
    settings_manager._profile_loaded = False

    try:
        yield settings_manager
    finally:
        _restore_settings_snapshot(snapshot)


@pytest.fixture()
def runtime_event_sink() -> EventSink:
    return EventSink()


@pytest.fixture()
def wearable_fake_clock() -> FakeClock:
    return FakeClock(start=0.0)


@pytest.fixture()
def wearable_network_state() -> FakeNetworkState:
    return FakeNetworkState(available=True)


@pytest.fixture()
def wearable_wake_signals() -> FakeWakeSignalStream:
    return FakeWakeSignalStream()


@pytest.fixture()
def wearable_runtime_fixtures(
    wearable_fake_clock: FakeClock,
    wearable_network_state: FakeNetworkState,
    wearable_wake_signals: FakeWakeSignalStream,
) -> dict[str, Any]:
    """Convenience bundle for wearable timing/network/wake fixtures."""
    return {
        "clock": wearable_fake_clock,
        "network": wearable_network_state,
        "wake_signals": wearable_wake_signals,
    }


@pytest.fixture()
def listener_factory():
    def _factory(
        *,
        default_language: str = "en-US",
        command_responses: list[str | None] | None = None,
        any_responses: list[str | None] | None = None,
        command_result_responses: list[CommandRecognitionResult | dict[str, Any] | None] | None = None,
    ) -> FakeVoiceListener:
        return FakeVoiceListener(
            default_language=default_language,
            command_responses=command_responses,
            any_responses=any_responses,
            command_result_responses=command_result_responses,
        )

    return _factory


@pytest.fixture()
def fake_listener(listener_factory) -> FakeVoiceListener:
    return listener_factory()


@pytest.fixture()
def tts_engine_factory():
    def _factory(*, speech_delay_s: float = 0.0, degrade_on_interrupt: bool = False) -> FakeTTSEngine:
        return FakeTTSEngine(
            speech_delay_s=speech_delay_s,
            degrade_on_interrupt=degrade_on_interrupt,
        )

    return _factory


@pytest.fixture()
def fake_tts_engine(tts_engine_factory) -> FakeTTSEngine:
    return tts_engine_factory()


@pytest.fixture()
def wake_detector_factory():
    def _factory(*, responses: list[Any] | None = None) -> FakeWakeDetector:
        return FakeWakeDetector(responses=responses)

    return _factory


@pytest.fixture()
def provider_components_factory():
    def _factory(
        *,
        default_language: str = "en-US",
        command_responses: list[str | None] | None = None,
        any_responses: list[str | None] | None = None,
        wake_responses: list[Any] | None = None,
        stt_available: bool = True,
        tts_available: bool = True,
        wake_available: bool = True,
    ) -> tuple[FakeProviderListener, FakeProviderTTSEngine, FakeProviderWakeDetector]:
        listener = FakeProviderListener(
            default_language=default_language,
            command_responses=command_responses,
            any_responses=any_responses,
            available=stt_available,
        )
        tts = FakeProviderTTSEngine(available=tts_available)
        wake = FakeProviderWakeDetector(responses=wake_responses, available=wake_available)
        return listener, tts, wake

    return _factory


@pytest.fixture()
def dispatch_spy_factory():
    def _factory(*, responses: list[Any] | None = None) -> DispatchSpy:
        return DispatchSpy(responses=responses)

    return _factory


@dataclass(frozen=True)
class CommandCase:
    text: str
    expected_intent: str


@pytest.fixture()
def bilingual_everyday_cases() -> list[CommandCase]:
    return [
        CommandCase(text="start obstacle detection", expected_intent="enable_obstacle_detection"),
        CommandCase(text="switch to english", expected_intent="set_language_en"),
        CommandCase(text="male voice", expected_intent="set_voice_gender_male"),
    ]


@pytest.fixture()
def capability_cases() -> list[CommandCase]:
    return [
        CommandCase(text="start obstacle detection", expected_intent="enable_obstacle_detection"),
        CommandCase(text="start ocr", expected_intent="enable_OCR"),
        CommandCase(text="recognize face", expected_intent="recognize_face"),
        CommandCase(text="recognize emotion", expected_intent="recognize_emotion"),
        CommandCase(text="start money detection", expected_intent="enable_money_detection"),
    ]


@pytest.fixture()
def protected_system_cases() -> list[CommandCase]:
    return [
        CommandCase(text="stop system", expected_intent="stop_system"),
        CommandCase(text="reset settings", expected_intent="reset_settings"),
    ]


@pytest.fixture()
def obstacle_adapter_factory():
    def _factory(
        *,
        available: bool = True,
        start_delay_s: float = 0.0,
        stop_delay_s: float = 0.0,
        read_delay_s: float = 0.0,
        fail_on_read: bool = False,
        fail_on_start: bool = False,
        fail_on_stop: bool = False,
        observation: dict[str, Any] | None = None,
    ) -> FakeObstacleAdapter:
        return FakeObstacleAdapter(
            available=available,
            start_delay_s=start_delay_s,
            stop_delay_s=stop_delay_s,
            read_delay_s=read_delay_s,
            fail_on_read=fail_on_read,
            fail_on_start=fail_on_start,
            fail_on_stop=fail_on_stop,
            observation=observation,
        )

    return _factory


@pytest.fixture()
def vision_adapter_factory():
    def _factory(
        *,
        face_available: bool = True,
        emotion_available: bool = True,
        face_delay_s: float = 0.0,
        emotion_delay_s: float = 0.0,
        face_exception: Exception | None = None,
        emotion_exception: Exception | None = None,
        face_response: dict[str, Any] | None = None,
        emotion_response: dict[str, Any] | None = None,
    ) -> FakeVisionAdapter:
        return FakeVisionAdapter(
            face_available=face_available,
            emotion_available=emotion_available,
            face_delay_s=face_delay_s,
            emotion_delay_s=emotion_delay_s,
            face_exception=face_exception,
            emotion_exception=emotion_exception,
            face_response=face_response,
            emotion_response=emotion_response,
        )

    return _factory


@pytest.fixture()
def release_artifact_dir(tmp_path):
    artifact_root = tmp_path / "release-artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    return artifact_root


@pytest.fixture()
def release_validation_context(release_artifact_dir):
    return {
        "artifact_root": release_artifact_dir,
        "candidate_id": "test-candidate",
        "commit_sha": "test-sha",
    }


@pytest.fixture()
def critical_prompt_catalog_factory():
    def _factory(*, overrides: dict[str, dict[str, str]] | None = None) -> dict[str, dict[str, str]]:
        catalog = build_default_critical_prompt_catalog()
        for prompt_key, entry in dict(overrides or {}).items():
            catalog[str(prompt_key)] = {
                "ar": str(entry.get("ar", catalog.get(str(prompt_key), {}).get("ar", "")) or ""),
                "en": str(entry.get("en", catalog.get(str(prompt_key), {}).get("en", "")) or ""),
            }
        return catalog

    return _factory


@pytest.fixture()
def corrupted_critical_prompt_catalog(critical_prompt_catalog_factory):
    return critical_prompt_catalog_factory(
        overrides={
            "offline_guidance": {
                "ar": "ط§ظ„ظ†طµ ط§ظ„طھط§ظ„ظپ",
                "en": "Network unavailable. Try again when connected.",
            }
        }
    )


@pytest.fixture()
def critical_surface_bindings_fixture() -> list[dict[str, Any]]:
    return surface_binding_payloads()


@pytest.fixture()
def reset_dialog_state():
    """Reset resolver dialog state before and after a test."""

    from core import resolver

    resolver.reset_session_context()
    try:
        yield resolver.get_session_context()
    finally:
        resolver.reset_session_context()


@pytest.fixture()
def bilingual_confirmation_utterances() -> dict[str, list[str]]:
    """Approved phrase-family utterances used by Phase 9 regression tests."""

    return {
        "affirmative": ["yes", "yes please", "okay", "ايوه", "تمام"],
        "negative": ["no", "nope", "لا", "لأ"],
        "cancel": ["cancel", "stop", "الغاء", "إلغاء"],
        "mixed": ["yes cancel", "yes but no", "ايوه الغاء"],
        "noise": ["not sure", "hmm maybe", "مش واضح"],
    }


@pytest.fixture()
def phase13_transcript_samples() -> dict[str, str]:
    return {
        "high_local_en": "start obstacle detection",
        "high_local_ar": "شغل العوائق",
        "medium_uncertain": "start obsticle maybe",
        "low_noise": "static noise command",
        "missing_confidence_clear": "switch to english",
        "bilingual_noisy": "reed txt بالعربي",
    }


@pytest.fixture()
def phase13_runtime_observer():
    events: list[Any] = []

    def _observer(event: Any) -> None:
        events.append(event)

    return {"events": events, "observer": _observer}


@pytest.fixture()
def clarification_option_utterances() -> dict[str, list[str]]:
    """Supported clarification options and noisy variants."""

    return {
        "language": ["english", "arabic", "انجليزي", "عربي"],
        "voice": ["male", "female", "ذكر", "أنثى"],
        "invalid": ["whatever", "anything", "مش فاهم"],
    }
@pytest.fixture()
def phase10_interrupt_vocabulary() -> dict[str, list[str]]:
    return {
        "stop": ["stop", "stop now", "\u0642\u0641", "\u062a\u0648\u0642\u0641"],
        "cancel": ["cancel", "\u0625\u0644\u063a\u0627\u0621"],
        "emergency": ["emergency"],
        "noise": ["please continue", "background chatter", "not now"],
    }


@pytest.fixture()
def phase14_audio_fixture_registry() -> dict[str, dict[str, Any]]:
    """Curated metadata-only benchmark fixture registry for Phase 14."""
    return {
        "clip_start_en": {
            "scenario_type": "clipped_start",
            "profile_id": "command.default",
            "qualification_profile_id": "default",
            "source_language": "en-US",
            "expected_canonical_text": "start obstacle detection",
            "field_safe": True,
            "audio_asset_ref": "fixtures/audio/clip_start_en.wav",
            "notes": "Soft leading speech onset.",
        },
        "clip_end_ar": {
            "scenario_type": "clipped_end",
            "profile_id": "command.default",
            "qualification_profile_id": "default",
            "source_language": "ar-EG",
            "expected_canonical_text": "شغل العوائق",
            "field_safe": True,
            "audio_asset_ref": "fixtures/audio/clip_end_ar.wav",
            "notes": "Quiet trailing segment.",
        },
        "closed_choice_yes_no": {
            "scenario_type": "closed_choice",
            "profile_id": "confirmation.default",
            "qualification_profile_id": "simplified",
            "source_language": "en-US",
            "expected_closed_choice_option": "yes",
            "field_safe": True,
            "audio_asset_ref": "fixtures/audio/closed_choice_yes_no.wav",
            "notes": "Closed vocabulary confirmation flow.",
        },
    }


@pytest.fixture()
def phase14_profile_overrides() -> dict[str, str]:
    return {
        "standby_wake": "standby_wake.default",
        "onboarding": "onboarding.default",
        "command": "command.default",
        "confirmation": "confirmation.default",
    }


@pytest.fixture()
def phase15_wake_alias_catalog() -> dict[str, tuple[str, ...]]:
    """Canonical and multilingual wake aliases used by Phase 15 replay tests."""
    return {
        "canonical": ("hi egb", "marhaba"),
        "english_variants": ("hi agency", "hi hgb", "hi e g b"),
        "arabic_variants": ("marhaba", "ahlan e g b", "hala e g b"),
        "non_wake_noise": ("hello assistant", "what time is it", "background chatter"),
    }


@pytest.fixture()
def phase15_replay_scenarios() -> list[dict[str, Any]]:
    """Replay scenario matrix for wake reliability and telemetry qualification."""
    return [
        {
            "scenario_id": "quiet_wake",
            "scenario_type": "quiet_wake",
            "wake_phrase": "hi egb",
            "expected_event_types": ("wake_accepted", "wake_to_listen_latency"),
            "requires_pi_hardware": False,
        },
        {
            "scenario_id": "noisy_wake",
            "scenario_type": "noisy_wake",
            "wake_phrase": "hi hgb",
            "expected_event_types": ("wake_rejected", "false_reject_review"),
            "requires_pi_hardware": False,
        },
        {
            "scenario_id": "bilingual_wake",
            "scenario_type": "bilingual_wake",
            "wake_phrase": "marhaba",
            "expected_event_types": ("wake_accepted", "wake_to_listen_latency"),
            "requires_pi_hardware": False,
        },
        {
            "scenario_id": "degraded_provider",
            "scenario_type": "degraded_provider",
            "wake_phrase": "hi egb",
            "expected_event_types": ("recovery_reset",),
            "requires_pi_hardware": False,
        },
        {
            "scenario_id": "repeated_fault",
            "scenario_type": "repeated_fault",
            "wake_phrase": "hi egb",
            "expected_event_types": ("recovery_reset", "clipped_retry"),
            "requires_pi_hardware": True,
        },
    ]


@pytest.fixture()
def phase15_local_artifact_bundle(tmp_path):
    """Create a local candidate artifact bundle path for telemetry persistence tests."""
    run_id = "phase15-test-run"
    root = tmp_path / "artifacts" / run_id
    speech_dir = root / "speech"
    speech_dir.mkdir(parents=True, exist_ok=True)
    return {
        "run_id": run_id,
        "artifact_root": root,
        "speech_dir": speech_dir,
        "telemetry_summary_path": speech_dir / "telemetry-summary.json",
        "pi_qualification_path": root / "pi-qualification.json",
    }


@pytest.fixture()
def phase19_fake_cloud_wake_responses() -> dict[str, dict[str, Any]]:
    """Deterministic fake cloud wake outcomes for Phase 19 standby tests."""
    return {
        "canonical_en": {
            "primary_transcript": "hi egb open navigation",
            "recognition_source": "cloud_primary",
            "failure_reason_code": None,
            "error_code": None,
        },
        "canonical_ar": {
            "primary_transcript": "\u0645\u0631\u062d\u0628\u0627",
            "recognition_source": "cloud_primary",
            "failure_reason_code": None,
            "error_code": None,
        },
        "timeout_then_fallback_match": {
            "primary_transcript": "hi egb",
            "recognition_source": "wake_strict_vosk_fallback",
            "failure_reason_code": "cloud_network_timeout",
            "error_code": None,
        },
        "timeout_then_fallback_miss": {
            "primary_transcript": "",
            "recognition_source": "wake_strict_vosk_fallback",
            "failure_reason_code": "cloud_network_timeout",
            "error_code": "strict_grammar_no_match",
        },
        "noncanonical_cloud": {
            "primary_transcript": "open navigation",
            "recognition_source": "cloud_primary",
            "failure_reason_code": None,
            "error_code": None,
        },
    }


@pytest.fixture()
def phase19_bilingual_wake_fixtures() -> list[dict[str, Any]]:
    """Bilingual standby wake fixtures with canonical and negative expectations."""
    return [
        {
            "fixture_id": "en_canonical",
            "language": "en-US",
            "utterance": "hi egb",
            "expected_canonical_alias": "hi egb",
            "accepted": True,
        },
        {
            "fixture_id": "ar_canonical",
            "language": "ar-EG",
            "utterance": "\u0645\u0631\u062d\u0628\u0627",
            "expected_canonical_alias": "\u0645\u0631\u062d\u0628\u0627",
            "accepted": True,
        },
        {
            "fixture_id": "mixed_wake_plus_command",
            "language": "en-US",
            "utterance": "hi egb open navigation",
            "expected_canonical_alias": "hi egb",
            "accepted": True,
            "command_suffix_ignored": True,
        },
        {
            "fixture_id": "command_only_negative",
            "language": "en-US",
            "utterance": "open navigation now",
            "expected_canonical_alias": None,
            "accepted": False,
        },
    ]


@pytest.fixture()
def phase19_repeated_wake_miss_sequence() -> list[dict[str, Any]]:
    """50 deterministic wake-miss records for standby stability validation."""
    return [
        {
            "attempt_index": index + 1,
            "recognition_source": "wake_strict_vosk_fallback",
            "failure_reason_code": "strict_grammar_no_match",
            "expected_status": "wake_missed",
            "field_safe": True,
        }
        for index in range(50)
    ]


@pytest.fixture()
def stt_rollout_observability_fixtures() -> dict[str, Any]:
    return {
        "telemetry_events": [
            {
                "event_id": "evt-1",
                "session_id": "session-1",
                "candidate_run_id": "candidate-1",
                "event_type": "cloud_failure",
                "source": "google_cloud",
                "rollout_mode": "commands_low_risk",
                "status": "failed",
                "confidence_bucket": "missing",
                "failure_category": "cloud_timeout",
                "recovery_outcome": "fallback",
                "latency_bucket": "over_baseline",
                "reason_code": "cloud_timeout_strict_fallback",
                "field_safe": True,
                "raw_audio_present": False,
                "raw_utterance_present": False,
            }
        ],
        "failure_scenarios": [
            {
                "scenario_id": "scenario-1",
                "failure_category": "cloud_timeout",
                "source": "google_cloud",
                "rollout_mode": "commands_low_risk",
                "bounded_outcome": "fallback",
                "crash_free": True,
                "spoken_guidance_surface": "runtime.command.fallback",
                "diagnostic_reason_code": "cloud_timeout_strict_fallback",
                "field_safe_metadata": {
                    "raw_audio_present": False,
                    "raw_utterance_present": False,
                },
            }
        ],
        "pi4_snapshot": {
            "environment": "raspberry_pi_4",
            "wake_latency_p95_ms": 950,
            "command_recognition_latency_p95_ms": 1900,
            "fallback_latency_p95_ms": 2200,
            "telemetry_completeness_ratio": 0.99,
        },
    }
