import logging
import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4

from core.audio.endpointing import (
    build_capture_attempt,
    derive_endpoint_quality_hints,
    should_trigger_bounded_relisten,
)
from core.audio.preprocessing import preprocess_audio_for_capture
from core.audio.profiles import normalize_usage_mode, select_capture_profile
from core.closed_vocabulary import closed_vocabulary_choices as registry_closed_vocabulary_choices
from core.command_models import (
    AudioCaptureAttempt,
    CommandRecognitionResult,
    build_stt_configuration_snapshot,
)
from core.speech.google_cloud_stt import CloudRecognitionCandidate, GoogleCloudSTTRecognizer
from core.speech.phrase_hints import build_phrase_hint_set

try:
    import speech_recognition as sr
except ModuleNotFoundError:  # pragma: no cover - exercised only in lean test envs
    class _FallbackUnknownValueError(Exception):
        pass

    class _FallbackRequestError(Exception):
        pass

    class _FallbackWaitTimeoutError(Exception):
        pass

    class _FallbackRecognizer:
        dynamic_energy_threshold = True
        pause_threshold = 0.6
        phrase_threshold = 0.3
        non_speaking_duration = 0.4

        def adjust_for_ambient_noise(self, source, duration: float = 0.5) -> None:  # noqa: ARG002
            return None

        def listen(self, source, timeout: int = 7, phrase_time_limit: int = 10):  # noqa: ARG002
            if timeout <= 0:
                raise _FallbackWaitTimeoutError("timeout")
            return b""

        def recognize_google(self, audio, language: str = "en-US"):  # noqa: ARG002
            return ""

        def recognize_sphinx(self, audio, language: str = "en-US"):  # noqa: ARG002
            return ""

    class _FallbackMicrophone:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ARG002
            return None

    class _FallbackSrModule:
        Recognizer = _FallbackRecognizer
        Microphone = _FallbackMicrophone
        UnknownValueError = _FallbackUnknownValueError
        RequestError = _FallbackRequestError
        WaitTimeoutError = _FallbackWaitTimeoutError

    sr = _FallbackSrModule()

try:
    import webrtcvad
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    webrtcvad = None

try:
    from vosk import KaldiRecognizer, Model, SetLogLevel
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    KaldiRecognizer = None
    Model = None
    SetLogLevel = None


logger = logging.getLogger(__name__)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, "1" if default else "0") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _safe_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(default)
    if parsed <= 0:
        return float(default)
    return parsed


def _safe_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return int(default)
    if parsed < 1:
        return int(default)
    return parsed


def classify_stt_failure_reason(reason_code: str | None) -> str:
    normalized = str(reason_code or "").strip().lower()
    if not normalized:
        return "none"
    if "network" in normalized:
        return "network"
    if "credential" in normalized or "auth" in normalized:
        return "credentials"
    if "quota" in normalized or "rate" in normalized:
        return "quota_or_rate"
    if "timeout" in normalized:
        return "cloud_timeout"
    if "strict_vosk_unavailable" in normalized or "fallback_unavailable" in normalized:
        return "fallback_missing"
    if "microphone" in normalized:
        return "microphone_timeout"
    if "clip" in normalized:
        return "clipping"
    if "language_mismatch" in normalized:
        return "language_mismatch"
    if "confidence" in normalized or "parser_rejected" in normalized:
        return "confidence_policy"
    return "unknown"


def _session_id() -> str:
    return uuid4().hex


def _highlight_heard_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "").strip())
    quoted = f"\"{cleaned}\""
    try:
        if getattr(sys.stdout, "isatty", lambda: False)():
            return f"\x1b[1;96m{quoted}\x1b[0m"
    except Exception:  # noqa: BLE001
        return quoted
    return quoted


class VoiceListener:
    def __init__(
        self,
        default_language: str = "en-US",
        retries: int = 2,
        provider_id: str = "legacy",
        *,
        prefer_offline: bool = True,
        allow_cloud_fallback: bool = True,
    ):
        self.recognizer = sr.Recognizer()
        # Better UX defaults for conversational commands
        self.recognizer.dynamic_energy_threshold = True
        if hasattr(self.recognizer, "dynamic_energy_adjustment_damping"):
            self.recognizer.dynamic_energy_adjustment_damping = 0.12
        if hasattr(self.recognizer, "dynamic_energy_ratio"):
            self.recognizer.dynamic_energy_ratio = 1.65
        # Use slightly longer pause handling to reduce clipped commands.
        self.recognizer.pause_threshold = 0.85
        self.recognizer.phrase_threshold = 0.25
        self.recognizer.non_speaking_duration = 0.55
        if hasattr(self.recognizer, "operation_timeout"):
            self.recognizer.operation_timeout = 10.0
        if hasattr(self.recognizer, "energy_threshold"):
            self.recognizer.energy_threshold = max(float(self.recognizer.energy_threshold), 180.0)
        self.language = default_language
        self.retries = retries
        self.last_error = None
        self.provider_id = provider_id
        self.prefer_offline = bool(prefer_offline)
        self.allow_cloud_fallback = bool(allow_cloud_fallback)
        self._stop_requested = threading.Event()
        self._listen_serial_lock = threading.Lock()
        self._active_source_lock = threading.Lock()
        self._active_source = None
        self._last_ambient_calibration_at = 0.0
        self._ambient_calibration_interval_s = 3.0
        self._ambient_calibration_duration_s = 0.35
        self._microphone_sample_rate = 16_000
        self._microphone_chunk_size = 1024
        self._sphinx_unavailable_languages: set[str] = set()
        self._vosk_unavailable_languages: set[str] = set()
        self._vosk_models: dict[str, Any] = {}
        self._vosk_command_grammar_cache: tuple[str, ...] | None = None
        self._stt_engine_preference = str(os.getenv("EGB_STT_ENGINE", "auto") or "auto").strip().lower()
        if self._stt_engine_preference not in {"auto", "vosk", "google"}:
            self._stt_engine_preference = "auto"
        self._command_grammar_enabled = True
        self._command_grammar_max_phrases = 220
        self._command_vosk_only = bool(int(os.getenv("EGB_STT_VOSK_ONLY", "0")))
        self._command_vosk_min_confidence = 0.34
        self._vad = None
        if webrtcvad is not None:
            try:
                self._vad = webrtcvad.Vad(2)
            except Exception:  # noqa: BLE001
                self._vad = None
        self._vad_sample_rate_hz = 16_000
        self._vad_frame_ms = 30
        self._vad_min_speech_ratio = 0.08
        self._vad_boundary_window_ms = 120
        self._command_followup_relisten_enabled = True
        self._command_followup_relisten_min_remaining_s = 1.6
        self._command_followup_relisten_gap_s = 0.08
        self._command_followup_max_attempts = 2
        self._default_qualification_profile_id = "default"
        self._cloud_primary_enabled = _env_flag("EGB_STT_CLOUD_PRIMARY_ENABLED", default=False)
        self._strict_vosk_fallback_enabled = _env_flag("EGB_STT_STRICT_VOSK_FALLBACK_ENABLED", default=False)
        self._sphinx_compat_enabled = _env_flag("EGB_STT_ENABLE_SPHINX_COMPAT", default=False)
        self._cloud_timeout_s = _safe_float(os.getenv("EGB_STT_CLOUD_TIMEOUT_S", "3.0"), 3.0)
        self._cloud_max_alternatives = _safe_int(os.getenv("EGB_STT_CLOUD_MAX_ALTERNATIVES", "3"), 3)
        self._pocketsphinx_default_candidate_count = 0
        self._pocketsphinx_default_invocation_count = 0
        self._pocketsphinx_compat_candidate_count = 0
        self._pocketsphinx_compat_invocation_count = 0
        self._cloud_recognizer = GoogleCloudSTTRecognizer(
            timeout_s=self._cloud_timeout_s,
            max_alternatives=self._cloud_max_alternatives,
        )
        if callable(SetLogLevel):
            try:
                SetLogLevel(-1)
            except Exception:  # noqa: BLE001
                logger.debug("[STT] Unable to silence vosk logs", exc_info=True)

    def set_language(self, language_code):
        """تغيير لغة الاستماع أثناء التشغيل"""
        if not language_code:
            logger.warning("[STT] Missing language_code, keeping %s", self.language)
            return
        self.language = language_code
        logger.info("[STT] Language set to: %s", self.language)

    def get_language(self):
        return self.language

    def provider_availability_state(self) -> dict[str, Any]:
        if not self._cloud_primary_enabled:
            return {
                "provider_source": "cloud_primary",
                "availability": "disabled",
                "credential_state": "not_required",
                "client_import_state": "not_required",
                "network_required": True,
                "startup_safe": True,
                "reason_code": "cloud_rollout_disabled",
                "checked_at_ms": int(time.time() * 1000),
            }
        return dict(self._cloud_recognizer.availability_state())

    def recognition_configuration_snapshot(self) -> dict[str, Any]:
        return build_stt_configuration_snapshot(
            cloud_primary_enabled=self._cloud_primary_enabled,
            strict_vosk_fallback_enabled=self._strict_vosk_fallback_enabled,
            sphinx_compat_enabled=self._sphinx_compat_enabled,
            cloud_timeout_s=self._cloud_timeout_s,
            cloud_max_alternatives=self._cloud_max_alternatives,
            selected_profile_language=self.language,
            configured_from_environment=True,
        )

    def pocketsphinx_usage_snapshot(self) -> dict[str, Any]:
        return {
            "default_candidate_count": int(self._pocketsphinx_default_candidate_count),
            "default_invocation_count": int(self._pocketsphinx_default_invocation_count),
            "compatibility_candidate_count": int(self._pocketsphinx_compat_candidate_count),
            "compatibility_invocation_count": int(self._pocketsphinx_compat_invocation_count),
            "compatibility_flag_status": "enabled" if self._sphinx_compat_enabled else "disabled_by_default",
            "field_safe": True,
        }

    def clear_stop_request(self) -> None:
        self._stop_requested.clear()

    def _stop_active_source(self) -> None:
        with self._active_source_lock:
            source = self._active_source
        if source is None:
            return
        stream = getattr(source, "stream", None)
        if stream is None:
            return
        try:
            stop_stream = getattr(stream, "stop_stream", None)
            if callable(stop_stream):
                stop_stream()
        except Exception:  # noqa: BLE001
            logger.debug("[STT] stop_stream failed during cancellation", exc_info=True)
        try:
            close_stream = getattr(stream, "close", None)
            if callable(close_stream):
                close_stream()
        except Exception:  # noqa: BLE001
            logger.debug("[STT] stream close failed during cancellation", exc_info=True)

    def request_stop(self) -> None:
        self._stop_requested.set()

    def _normalize_transcript(self, text: str) -> str:
        normalized = str(text or "").strip()
        if not normalized:
            return ""
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    def _transcript_quality_score(self, text: str) -> float:
        normalized = self._normalize_transcript(text)
        if not normalized:
            return 0.0
        token_count = len(normalized.split())
        char_count = len(normalized)
        alpha_count = sum(1 for char in normalized if char.isalpha())
        alpha_ratio = alpha_count / max(1, char_count)
        token_score = min(1.0, token_count / 4.0)
        length_score = min(1.0, char_count / 18.0)
        quality = (0.55 * alpha_ratio) + (0.30 * token_score) + (0.15 * length_score)
        # Penalize ultra-short fragments that are often clipped command edges.
        if token_count == 1 and char_count <= 4:
            quality *= 0.60
        elif token_count == 1 and char_count <= 7:
            quality *= 0.78
        return quality

    def _rank_candidate(self, text: str, *, confidence: float | None, source: str) -> float:
        quality = self._transcript_quality_score(text)
        confidence_value = float(confidence) if confidence is not None else 0.0
        source_bias_by_source = {
            "cloud": 0.08,
            "cloud_primary": 0.08,
            "local_vosk": 0.10,
            "offline": 0.03,
            "sphinx_compat": 0.03,
            "strict_vosk_fallback": 0.09,
            "wake_strict_vosk_fallback": 0.09,
        }
        source_bias = source_bias_by_source.get(source, 0.0)
        return quality + (0.35 * confidence_value) + source_bias

    def _normalize_vosk_language_key(self, language_code: str) -> str:
        normalized = str(language_code or "").strip().lower()
        if normalized.startswith("ar"):
            return "ar"
        if normalized.startswith("en"):
            return "en"
        return "en"

    def _resolve_vosk_model_path(self, language_code: str) -> Path | None:
        language_key = self._normalize_vosk_language_key(language_code)
        env_candidates: list[str] = []
        if language_key == "ar":
            env_candidates.append(str(os.getenv("EGB_VOSK_MODEL_AR", "")).strip())
        else:
            env_candidates.append(str(os.getenv("EGB_VOSK_MODEL_EN", "")).strip())
        env_candidates.append(str(os.getenv("EGB_VOSK_MODEL_DIR", "")).strip())

        default_candidates = [
            Path("models") / "vosk" / f"{language_key}",
            Path("models") / f"vosk-model-small-{language_key}",
            Path("models") / f"vosk-model-{language_key}",
        ]
        if language_key == "en":
            default_candidates.append(Path("models") / "vosk-model-small-en-us-0.15")
            default_candidates.append(Path("models") / "vosk-model-en-us-0.22")
        if language_key == "ar":
            default_candidates.append(Path("models") / "vosk-model-ar-0.22-linto-1.1.0")
            default_candidates.append(Path("models") / "vosk-model-ar-mgb2-0.4")

        for raw_path in env_candidates:
            if not raw_path:
                continue
            candidate = Path(raw_path)
            if candidate.exists():
                return candidate
        for candidate in default_candidates:
            if candidate.exists():
                return candidate
        return None

    def _load_vosk_model(self, language_code: str) -> Any | None:
        if Model is None:
            return None
        language_key = self._normalize_vosk_language_key(language_code)
        if "*" in self._vosk_unavailable_languages or language_key in self._vosk_unavailable_languages:
            return None
        if language_key in self._vosk_models:
            return self._vosk_models[language_key]
        model_path = self._resolve_vosk_model_path(language_key)
        if model_path is None:
            self._vosk_unavailable_languages.add(language_key)
            logger.info("[STT] Vosk model not found for language=%s", language_key)
            return None
        try:
            model = Model(str(model_path))
        except Exception as err:  # noqa: BLE001
            self._vosk_unavailable_languages.add(language_key)
            logger.warning("[STT] Failed loading Vosk model (%s): %s", model_path, err)
            return None
        self._vosk_models[language_key] = model
        logger.info("[STT] Loaded Vosk model language=%s path=%s", language_key, model_path)
        return model

    def _command_grammar_phrases(
        self,
        *,
        closed_vocabulary_choices: Sequence[str] | None = None,
    ) -> tuple[str, ...]:
        if closed_vocabulary_choices:
            normalized = [
                self._normalize_transcript(str(item or "")).lower()
                for item in closed_vocabulary_choices
            ]
            filtered = [item for item in normalized if item]
            if filtered:
                return tuple(dict.fromkeys(filtered))
        if self._vosk_command_grammar_cache is not None:
            return self._vosk_command_grammar_cache
        phrases: list[str] = []
        seen: set[str] = set()
        try:
            from core import parser as command_parser

            for entry in command_parser.COMMAND_CATALOG.values():
                for keyword in entry.keywords:
                    candidate = self._normalize_transcript(str(keyword or "")).lower()
                    if not candidate:
                        continue
                    if len(candidate) > 48:
                        continue
                    key = candidate.casefold()
                    if key in seen:
                        continue
                    seen.add(key)
                    phrases.append(candidate)
                    if len(phrases) >= self._command_grammar_max_phrases:
                        break
                if len(phrases) >= self._command_grammar_max_phrases:
                    break
        except Exception:  # noqa: BLE001
            logger.debug("[STT] Failed building command grammar from parser catalog", exc_info=True)

        essential_phrases = (
            "male",
            "female",
            "english",
            "arabic",
            "yes",
            "no",
            "ذكر",
            "أنثى",
            "عربي",
            "انجليزي",
            "نعم",
            "لا",
        )
        for phrase in essential_phrases:
            candidate = self._normalize_transcript(phrase).lower()
            if candidate and candidate.casefold() not in seen:
                seen.add(candidate.casefold())
                phrases.append(candidate)
        self._vosk_command_grammar_cache = tuple(phrases[: self._command_grammar_max_phrases])
        return self._vosk_command_grammar_cache

    def _wake_phrase_hints(self) -> tuple[str, ...]:
        hint_set = build_phrase_hint_set(mode="wake")
        return tuple(hint_set.phrases[: int(hint_set.max_cloud_phrases)])

    def _strict_grammar_phrases(
        self,
        *,
        mode: str,
        usage_mode: str,
        closed_vocabulary_choices: Sequence[str] | None = None,
        closed_vocabulary_id: str | None = None,
    ) -> tuple[str, ...]:
        normalized_mode = str(mode or "").strip().lower()
        normalized_usage = str(usage_mode or "").strip().lower()
        if normalized_mode == "closed_choice":
            if closed_vocabulary_choices:
                return tuple(
                    dict.fromkeys(
                        self._normalize_transcript(str(item or "")).lower()
                        for item in closed_vocabulary_choices
                        if self._normalize_transcript(str(item or "")).strip()
                    )
                )
            if closed_vocabulary_id:
                from_registry = registry_closed_vocabulary_choices(closed_vocabulary_id)
                return tuple(
                    dict.fromkeys(
                        self._normalize_transcript(str(item or "")).lower()
                        for item in from_registry
                        if self._normalize_transcript(str(item or "")).strip()
                    )
                )
            return ()
        if normalized_mode == "wake_grammar" or normalized_usage == "standby_wake":
            hint_set = build_phrase_hint_set(mode="wake")
            return tuple(hint_set.phrases[: int(hint_set.max_strict_grammar_phrases)])
        return self._command_grammar_phrases(closed_vocabulary_choices=closed_vocabulary_choices)

    def _recognize_cloud_candidate(
        self,
        *,
        audio: Any,
        selected_language: str,
        phrase_hints: Sequence[str],
        recognition_path: str,
    ) -> CloudRecognitionCandidate:
        return self._cloud_recognizer.recognize_short_utterance(
            audio=audio,
            selected_language=selected_language,
            phrase_hints=phrase_hints,
            recognition_path=recognition_path,
        )

    def _analyze_vad_profile(self, audio: Any) -> dict[str, Any] | None:
        if self._vad is None:
            return None
        get_raw_data = getattr(audio, "get_raw_data", None)
        if not callable(get_raw_data):
            return None
        try:
            pcm = get_raw_data(convert_rate=self._vad_sample_rate_hz, convert_width=2)
        except Exception:  # noqa: BLE001
            return None
        if not pcm:
            return None
        frame_size = int(self._vad_sample_rate_hz * (self._vad_frame_ms / 1000.0) * 2)
        if frame_size <= 0 or len(pcm) < frame_size:
            return None
        total_frames = len(pcm) // frame_size
        speech_flags: list[bool] = []
        for index in range(total_frames):
            frame = pcm[index * frame_size : (index + 1) * frame_size]
            try:
                is_speech = bool(self._vad.is_speech(frame, self._vad_sample_rate_hz))
            except Exception:  # noqa: BLE001
                return None
            speech_flags.append(is_speech)
        if not speech_flags:
            return None
        voiced_frames = sum(1 for value in speech_flags if value)
        speech_ratio = voiced_frames / max(1, len(speech_flags))
        first_voice_index = next((idx for idx, value in enumerate(speech_flags) if value), len(speech_flags))
        last_voice_index = next(
            (idx for idx in range(len(speech_flags) - 1, -1, -1) if speech_flags[idx]),
            -1,
        )
        leading_silence_ms = first_voice_index * self._vad_frame_ms
        trailing_silence_ms = (
            (len(speech_flags) - 1 - last_voice_index) * self._vad_frame_ms
            if last_voice_index >= 0
            else len(speech_flags) * self._vad_frame_ms
        )
        boundary_clipped = bool(
            speech_ratio >= self._vad_min_speech_ratio
            and (
                leading_silence_ms <= self._vad_boundary_window_ms
                or trailing_silence_ms <= self._vad_boundary_window_ms
            )
        )
        return {
            "speech_ratio": round(speech_ratio, 3),
            "leading_silence_ms": int(leading_silence_ms),
            "trailing_silence_ms": int(trailing_silence_ms),
            "boundary_clipped": boundary_clipped,
        }

    def _is_likely_clipped_transcript(self, text: str, *, vad_profile: dict[str, Any] | None = None) -> bool:
        normalized = self._normalize_transcript(text).lower()
        if not normalized:
            return True
        tokens = [token for token in normalized.split() if token]
        if not tokens:
            return True
        if len(normalized) <= 2:
            return True
        last_token = tokens[-1]
        if len(last_token) <= 1:
            return True
        trailing_connectors = {
            "to",
            "the",
            "a",
            "an",
            "and",
            "or",
            "for",
            "of",
            "in",
            "on",
            "with",
            "from",
            "at",
            "is",
            "are",
            "be",
            "this",
            "that",
            "و",
            "او",
            "أو",
            "في",
            "من",
            "على",
            "الى",
            "إلى",
            "عن",
            "مع",
        }
        if last_token in trailing_connectors:
            return True
        if len(tokens) >= 2 and len(last_token) <= 2 and len(normalized) >= 9:
            return True
        if vad_profile and bool(vad_profile.get("boundary_clipped", False)):
            return True
        return False

    def _recognition_completeness_score(
        self,
        *,
        primary_text: str,
        alternatives: Sequence[str],
        raw_confidence: float | None,
        vad_profile: dict[str, Any] | None = None,
    ) -> float:
        confidence_term = max(0.0, min(1.0, float(raw_confidence))) if raw_confidence is not None else 0.0
        ambiguity_penalty = 0.06 * max(0, len(tuple(alternatives)) - 1)
        clipped_penalty = (
            0.28
            if self._is_likely_clipped_transcript(primary_text, vad_profile=vad_profile)
            else 0.0
        )
        return (
            self._transcript_quality_score(primary_text)
            + (0.32 * confidence_term)
            - ambiguity_penalty
            - clipped_penalty
        )

    def _should_relisten_for_command_completion(
        self,
        *,
        primary_text: str,
        alternatives: Sequence[str],
        raw_confidence: float | None,
        remaining_s: float,
        attempt_index: int,
        vad_profile: dict[str, Any] | None = None,
    ) -> bool:
        if not self._command_followup_relisten_enabled:
            return False
        if attempt_index >= self._command_followup_max_attempts:
            return False
        if remaining_s < self._command_followup_relisten_min_remaining_s:
            return False
        clipped = self._is_likely_clipped_transcript(primary_text, vad_profile=vad_profile)
        low_confidence = raw_confidence is None or float(raw_confidence) < 0.55
        low_quality = self._transcript_quality_score(primary_text) < 0.48
        high_ambiguity = len(tuple(alternatives)) >= 3
        return clipped or low_quality or (low_confidence and high_ambiguity)

    def _recognize_sphinx_candidate(self, audio: Any, *, language_code: str) -> str | None:
        recognize_sphinx = getattr(self.recognizer, "recognize_sphinx", None)
        if not callable(recognize_sphinx):
            return None
        language_key = str(language_code or "").strip().lower()
        if "*" in self._sphinx_unavailable_languages or language_key in self._sphinx_unavailable_languages:
            return None
        try:
            text = recognize_sphinx(audio, language=language_code)
            normalized = self._normalize_transcript(str(text or ""))
            return normalized or None
        except sr.UnknownValueError:
            self.last_error = "unknown_value"
            return None
        except sr.RequestError as err:
            self.last_error = f"offline_request_error:{err}"
            message = str(err)
            lowered_message = message.lower()
            if "missing pocketsphinx language data directory" in lowered_message:
                if language_key and language_key not in self._sphinx_unavailable_languages:
                    logger.warning("[STT] Offline recognition unavailable: %s", err)
                self._sphinx_unavailable_languages.add(language_key)
                return None
            if "missing pocketsphinx module" in lowered_message:
                if "*" not in self._sphinx_unavailable_languages:
                    logger.warning("[STT] Offline recognition unavailable: %s", err)
                self._sphinx_unavailable_languages.add("*")
                return None
            logger.warning("[STT] Offline recognition unavailable: %s", err)
            return None
        except Exception as err:  # noqa: BLE001
            self.last_error = f"offline_failure:{type(err).__name__}"
            logger.warning("[STT] Offline recognition failed: %s", err)
            return None

    def _recognize_google_candidates(
        self,
        audio: Any,
        *,
        language_code: str,
    ) -> list[tuple[str, float | None]]:
        recognize_google = getattr(self.recognizer, "recognize_google", None)
        if not callable(recognize_google):
            return []

        payload: Any = None
        try:
            payload = recognize_google(audio, language=language_code, show_all=True)
        except TypeError:
            try:
                text = recognize_google(audio, language=language_code)
                normalized = self._normalize_transcript(str(text or ""))
                return [(normalized, None)] if normalized else []
            except sr.UnknownValueError:
                self.last_error = "unknown_value"
                return []
            except sr.RequestError as err:
                self.last_error = f"request_error:{err}"
                logger.error("[STT] Request failed; %s", err)
                return []
        except sr.UnknownValueError:
            self.last_error = "unknown_value"
            return []
        except sr.RequestError as err:
            self.last_error = f"request_error:{err}"
            logger.error("[STT] Request failed; %s", err)
            return []
        except Exception as err:  # noqa: BLE001
            self.last_error = f"request_error:{type(err).__name__}"
            logger.debug("[STT] Cloud recognizer payload build failed: %s", err)
            return []

        candidates: list[tuple[str, float | None]] = []
        if isinstance(payload, dict):
            for item in list(payload.get("alternative", ())):
                if not isinstance(item, dict):
                    continue
                normalized = self._normalize_transcript(str(item.get("transcript", "") or ""))
                if not normalized:
                    continue
                confidence_raw = item.get("confidence")
                confidence = float(confidence_raw) if isinstance(confidence_raw, (int, float)) else None
                if normalized not in {existing for existing, _ in candidates}:
                    candidates.append((normalized, confidence))
        elif isinstance(payload, str):
            normalized = self._normalize_transcript(payload)
            if normalized:
                candidates.append((normalized, None))

        return candidates

    def _recognize_vosk_candidates(
        self,
        audio: Any,
        *,
        language_code: str,
        for_command: bool = False,
        closed_vocabulary_choices: Sequence[str] | None = None,
        strict_mode: bool = False,
        grammar_phrases: Sequence[str] | None = None,
    ) -> list[tuple[str, float | None]]:
        if KaldiRecognizer is None:
            return []
        model = self._load_vosk_model(language_code)
        if model is None:
            return []
        get_raw_data = getattr(audio, "get_raw_data", None)
        if not callable(get_raw_data):
            return []
        try:
            pcm = get_raw_data(convert_rate=16_000, convert_width=2)
        except Exception:  # noqa: BLE001
            return []
        if not pcm:
            return []

        recognizer = None
        try:
            if strict_mode:
                grammar_payload = list(
                    grammar_phrases
                    or self._strict_grammar_phrases(
                        mode="wake_grammar",
                        usage_mode="standby_wake",
                        closed_vocabulary_choices=closed_vocabulary_choices,
                    )
                )
                if grammar_payload:
                    grammar_payload.append("[unk]")
                    recognizer = KaldiRecognizer(model, 16_000, json.dumps(grammar_payload, ensure_ascii=False))
            elif for_command and self._command_grammar_enabled:
                grammar_payload = list(self._command_grammar_phrases(closed_vocabulary_choices=closed_vocabulary_choices))
                if grammar_payload:
                    grammar_payload.append("[unk]")
                    recognizer = KaldiRecognizer(model, 16_000, json.dumps(grammar_payload, ensure_ascii=False))
            if recognizer is None:
                recognizer = KaldiRecognizer(model, 16_000)
            set_max_alternatives = getattr(recognizer, "SetMaxAlternatives", None)
            if callable(set_max_alternatives):
                set_max_alternatives(3)
            set_words = getattr(recognizer, "SetWords", None)
            if callable(set_words):
                set_words(True)
            recognizer.AcceptWaveform(pcm)
            payload = json.loads(recognizer.FinalResult())
        except Exception as err:  # noqa: BLE001
            logger.debug("[STT] Vosk recognition failed (%s): %s", language_code, err)
            return []

        candidates: list[tuple[str, float | None]] = []
        for item in list(payload.get("alternatives", [])):
            if not isinstance(item, dict):
                continue
            text = self._normalize_transcript(str(item.get("text", "") or ""))
            if not text:
                continue
            confidence_raw = item.get("confidence")
            confidence = float(confidence_raw) if isinstance(confidence_raw, (int, float)) else None
            if for_command and (not strict_mode) and confidence is not None and confidence < self._command_vosk_min_confidence:
                continue
            if text not in {existing for existing, _ in candidates}:
                candidates.append((text, confidence))

        if not candidates:
            text = self._normalize_transcript(str(payload.get("text", "") or ""))
            if text:
                word_confidences = [
                    float(item.get("conf"))
                    for item in list(payload.get("result", []))
                    if isinstance(item, dict) and isinstance(item.get("conf"), (int, float))
                ]
                avg_confidence = (
                    sum(word_confidences) / len(word_confidences)
                    if word_confidences
                    else None
                )
                if (
                    (not for_command)
                    or strict_mode
                    or avg_confidence is None
                    or avg_confidence >= self._command_vosk_min_confidence
                ):
                    candidates.append((text, avg_confidence))

        if strict_mode:
            allowed = {
                self._normalize_transcript(str(item or "")).lower()
                for item in (grammar_phrases or ())
                if self._normalize_transcript(str(item or "")).strip()
            }
            if allowed:
                candidates = [
                    (text, confidence)
                    for text, confidence in candidates
                    if self._normalize_transcript(text).lower() in allowed
                ]

        return candidates

    def _recognize_audio_candidates(
        self,
        audio: Any,
        *,
        language_code: str,
        for_command: bool = False,
        usage_mode: str = "wake",
        recognition_path: str = "local_first",
        closed_vocabulary_id: str | None = None,
        closed_vocabulary_choices: Sequence[str] | None = None,
    ) -> list[tuple[str, float | None, str, dict[str, Any]]]:
        normalized_usage = str(usage_mode or "wake").strip().lower()
        candidates: list[tuple[str, float | None, str, dict[str, Any]]] = []

        def _append_candidate(
            text: str,
            confidence: float | None,
            source: str,
            *,
            metadata: dict[str, Any] | None = None,
        ) -> None:
            normalized = self._normalize_transcript(text)
            if not normalized:
                return
            payload = {
                "recognition_source": source,
                "selected_language": language_code,
                "detected_language": language_code,
                "failure_reason_code": None,
            }
            if metadata:
                payload.update(dict(metadata))
                payload.setdefault("recognition_source", source)
                payload.setdefault("selected_language", language_code)
                payload.setdefault("detected_language", language_code)
                payload.setdefault("failure_reason_code", None)
            candidates.append((normalized, confidence, source, payload))

        cloud_candidate: CloudRecognitionCandidate | None = None
        if self._cloud_primary_enabled and (for_command or normalized_usage == "standby_wake"):
            phrase_hints: tuple[str, ...]
            if normalized_usage == "standby_wake":
                phrase_hints = self._wake_phrase_hints()
            else:
                phrase_hints = tuple(build_phrase_hint_set(mode="command").phrases[: self._cloud_max_alternatives * 24])
            cloud_candidate = self._recognize_cloud_candidate(
                audio=audio,
                selected_language=language_code,
                phrase_hints=phrase_hints,
                recognition_path=recognition_path,
            )
            if cloud_candidate.is_usable:
                cloud_meta = {
                    "recognition_source": "cloud_primary",
                    "selected_language": cloud_candidate.selected_language,
                    "detected_language": cloud_candidate.detected_language or language_code,
                    "failure_reason_code": cloud_candidate.failure_reason_code,
                }
                alternatives = cloud_candidate.alternative_transcripts or (
                    cloud_candidate.primary_transcript or "",
                )
                for index, transcript in enumerate(alternatives):
                    confidence = cloud_candidate.confidence_score if index == 0 else None
                    _append_candidate(transcript, confidence, "cloud_primary", metadata=cloud_meta)
                if candidates:
                    self.last_error = None
                    return candidates
            else:
                failure = cloud_candidate.failure_reason_code
                if failure:
                    self.last_error = failure

        strict_mode_enabled = (
            self._strict_vosk_fallback_enabled
            and cloud_candidate is not None
            and (for_command or normalized_usage == "standby_wake")
        )
        if strict_mode_enabled and not candidates:
            strict_mode = "wake_grammar" if normalized_usage == "standby_wake" else (
                "closed_choice" if normalized_usage == "confirmation" else "command_inventory"
            )
            strict_phrases = self._strict_grammar_phrases(
                mode=strict_mode,
                usage_mode=normalized_usage,
                closed_vocabulary_choices=closed_vocabulary_choices,
                closed_vocabulary_id=closed_vocabulary_id,
            )
            strict_candidates = self._recognize_vosk_candidates(
                audio,
                language_code=language_code,
                for_command=for_command,
                closed_vocabulary_choices=closed_vocabulary_choices,
                strict_mode=True,
                grammar_phrases=strict_phrases,
            )
            strict_source = "wake_strict_vosk_fallback" if normalized_usage == "standby_wake" else "strict_vosk_fallback"
            fallback_meta = {
                "recognition_source": strict_source,
                "selected_language": language_code,
                "detected_language": language_code,
                "failure_reason_code": None,
                "cloud_failure_reason_code": (
                    cloud_candidate.failure_reason_code if cloud_candidate is not None else None
                ),
            }
            for text, confidence in strict_candidates:
                _append_candidate(text, confidence, strict_source, metadata=fallback_meta)
            if candidates:
                self.last_error = None
                return candidates
            self.last_error = "strict_grammar_no_match"
            return []

        if cloud_candidate is not None and not candidates:
            # Cloud path was enabled but produced no usable result and strict
            # fallback is disabled.
            return []

        use_vosk_first = for_command and self._stt_engine_preference in {"auto", "vosk"}
        if use_vosk_first:
            if normalized_usage == "standby_wake":
                wake_grammar = self._strict_grammar_phrases(
                    mode="wake_grammar",
                    usage_mode=normalized_usage,
                    closed_vocabulary_choices=closed_vocabulary_choices,
                    closed_vocabulary_id=closed_vocabulary_id,
                )
                for text, confidence in self._recognize_vosk_candidates(
                    audio,
                    language_code=language_code,
                    for_command=True,
                    closed_vocabulary_choices=closed_vocabulary_choices,
                    strict_mode=True,
                    grammar_phrases=wake_grammar,
                ):
                    _append_candidate(text, confidence, "wake_strict_vosk_fallback")
            else:
                for text, confidence in self._recognize_vosk_candidates(
                    audio,
                    language_code=language_code,
                    for_command=for_command,
                    closed_vocabulary_choices=closed_vocabulary_choices,
                ):
                    _append_candidate(text, confidence, "local_vosk")
            if for_command and candidates:
                return candidates
            if self._command_vosk_only and candidates:
                return candidates

        if self.prefer_offline:
            if self._sphinx_compat_enabled and not for_command:
                self._pocketsphinx_compat_invocation_count += 1
                offline_text = self._recognize_sphinx_candidate(audio, language_code=language_code)
                if offline_text:
                    self._pocketsphinx_compat_candidate_count += 1
                    _append_candidate(offline_text, None, "sphinx_compat")
            if self.allow_cloud_fallback and not (for_command and self._command_vosk_only):
                for text, confidence in self._recognize_google_candidates(audio, language_code=language_code):
                    _append_candidate(text, confidence, "cloud_primary" if for_command else "cloud")
        else:
            if self.allow_cloud_fallback and not (for_command and self._command_vosk_only):
                for text, confidence in self._recognize_google_candidates(audio, language_code=language_code):
                    _append_candidate(text, confidence, "cloud_primary" if for_command else "cloud")
            if not candidates and self._sphinx_compat_enabled and not for_command:
                self._pocketsphinx_compat_invocation_count += 1
                offline_text = self._recognize_sphinx_candidate(audio, language_code=language_code)
                if offline_text:
                    self._pocketsphinx_compat_candidate_count += 1
                    _append_candidate(offline_text, None, "sphinx_compat")

        if for_command and not candidates and self._stt_engine_preference == "vosk":
            for text, confidence in self._recognize_vosk_candidates(
                audio,
                language_code=language_code,
                for_command=True,
                closed_vocabulary_choices=closed_vocabulary_choices,
            ):
                _append_candidate(text, confidence, "local_vosk")
        return candidates

    def listen(self, prompt="[STT] Listening..."):
        """Listen for speech input with retries and logging."""
        for attempt in range(1, self.retries + 2):
            try:
                audio = self.listen_audio(prompt=f"{prompt} (attempt {attempt})")
                if audio is None:
                    time.sleep(0.5)
                    continue

                text = self.recognize_audio(audio, language_code=self.language)
                if not text:
                    time.sleep(0.5)
                    continue
                logger.info("[STT] Recognized: %s", text)
                self.last_error = None
                return text

            except sr.UnknownValueError:
                self.last_error = "unknown_value"
                logger.warning("[STT] Could not understand audio (Attempt %s)", attempt)
            except sr.RequestError as err:
                self.last_error = f"request_error:{err}"
                logger.error("[STT] Request failed; %s (Attempt %s)", err, attempt)
            except sr.WaitTimeoutError:
                self.last_error = "timeout"
                logger.warning("[STT] No speech detected (Attempt %s)", attempt)

            time.sleep(0.5)  # Small delay before retry

        logger.error("[STT] Failed to recognize speech after retries")
        return None

    def listen_audio(
        self,
        prompt="[STT] Listening...",
        timeout=7,
        phrase_time_limit=10,
        *,
        interrupt_event: Any | None = None,
        hard_timeout_s: float | None = None,
    ):
        """Capture audio once from the microphone with hard cancellation boundaries."""
        with self._listen_serial_lock:
            self.clear_stop_request()
            checker = getattr(interrupt_event, "is_set", None) if interrupt_event is not None else None
            if self._stop_requested.is_set() or (callable(checker) and checker()):
                self.last_error = "cancelled"
                return None

            outcome: dict[str, Any] = {"audio": None, "error": None}
            done = threading.Event()

            def _listen_once() -> None:
                try:
                    with sr.Microphone(
                        sample_rate=self._microphone_sample_rate,
                        chunk_size=self._microphone_chunk_size,
                    ) as source:
                        with self._active_source_lock:
                            self._active_source = source
                        logger.info("%s", prompt)
                        should_calibrate = (
                            (time.monotonic() - self._last_ambient_calibration_at) >= self._ambient_calibration_interval_s
                        )
                        if should_calibrate:
                            self.recognizer.adjust_for_ambient_noise(
                                source,
                                duration=self._ambient_calibration_duration_s,
                            )
                            self._last_ambient_calibration_at = time.monotonic()
                        if self._stop_requested.is_set() or (callable(checker) and checker()):
                            return
                        outcome["audio"] = self.recognizer.listen(
                            source,
                            timeout=timeout,
                            phrase_time_limit=phrase_time_limit,
                        )
                except Exception as exc:  # noqa: BLE001
                    outcome["error"] = exc
                finally:
                    with self._active_source_lock:
                        self._active_source = None
                    done.set()

            worker = threading.Thread(target=_listen_once, name="VoiceListenerListen", daemon=True)
            worker.start()
            deadline = None
            if hard_timeout_s is not None:
                deadline = time.perf_counter() + max(0.1, float(hard_timeout_s))
            cancelled = False
            while not done.wait(timeout=0.01):
                if cancelled:
                    continue
                if self._stop_requested.is_set() or (callable(checker) and checker()):
                    # Avoid forcibly closing the PyAudio stream from another thread.
                    # We mark cancellation and wait for the listen thread to unwind safely.
                    self._stop_requested.set()
                    self.last_error = "cancelled"
                    cancelled = True
                    continue
                if deadline is not None and time.perf_counter() >= deadline:
                    self._stop_requested.set()
                    self.last_error = "timeout"
                    cancelled = True
                    continue

            if cancelled:
                return None

            error = outcome["error"]
            if isinstance(error, sr.WaitTimeoutError):
                self.last_error = "timeout"
                logger.warning("[STT] No speech detected")
                return None
            if isinstance(error, Exception):
                self.last_error = f"listen_error:{type(error).__name__}"
                logger.warning("[STT] Listen failed: %s", error)
                return None
            return outcome["audio"]

    def recognize_audio(self, audio, language_code: str):
        """Recognize previously captured audio using local-first, cloud-fallback strategy."""
        if audio is None:
            self.last_error = "unknown_value"
            return None
        if self.prefer_offline and not self._sphinx_compat_enabled:
            offline_text = self._recognize_sphinx_candidate(audio, language_code=language_code)
            if offline_text:
                self.last_error = None
                return offline_text
        candidates = self._recognize_audio_candidates(audio, language_code=language_code)
        if not candidates:
            return None

        best_text = None
        best_rank = -1.0
        for item in candidates:
            if len(item) == 4:
                text, confidence, source, _metadata = item
            else:
                text, confidence, source = item[:3]
            rank = self._rank_candidate(text, confidence=confidence, source=source)
            if rank > best_rank:
                best_text = text
                best_rank = rank
        if best_text:
            self.last_error = None
            return best_text
        return None

    def _language_candidates(self, languages: Sequence[str] | None = None) -> list[str]:
        language_candidates: list[str] = []
        primary_language = str(self.language or "").strip()
        if primary_language:
            language_candidates.append(primary_language)
        for language_code in list(languages or ()):
            normalized = str(language_code or "").strip()
            if normalized and normalized not in language_candidates:
                language_candidates.append(normalized)
        for fallback_language in ("en-US", "ar-EG"):
            if fallback_language not in language_candidates:
                language_candidates.append(fallback_language)
        return language_candidates

    def listen_any(
        self,
        languages,
        prompt="[STT] Listening...",
        timeout=7,
        phrase_time_limit=10,
        interrupt_event: Any | None = None,
    ):
        """Listen using bounded retries and language-aware candidate ranking."""
        language_candidates = self._language_candidates(list(languages))
        max_attempts = max(1, min(3, self.retries + 1))
        deadline = time.perf_counter() + max(0.8, float(timeout))
        for attempt in range(max_attempts):
            remaining = max(0.0, deadline - time.perf_counter())
            if remaining <= 0:
                break
            attempt_timeout = max(1, int(round(min(float(timeout), remaining))))
            attempt_phrase_limit = max(1, int(round(min(float(phrase_time_limit), remaining + 0.8))))
            attempt_prompt = prompt if max_attempts == 1 else f"{prompt} ({attempt + 1}/{max_attempts})"
            audio = self.listen_audio(
                prompt=attempt_prompt,
                timeout=attempt_timeout,
                phrase_time_limit=attempt_phrase_limit,
                interrupt_event=interrupt_event,
                hard_timeout_s=remaining,
            )
            if audio is None:
                continue
            recognition_payload = self._recognize_candidates(
                audio,
                languages=language_candidates,
                for_command=False,
                usage_mode="wake",
                recognition_path="local_first",
            )
            if len(recognition_payload) == 5:
                primary_text, detected_language, _, _, _ = recognition_payload
            else:
                primary_text, detected_language, _, _ = recognition_payload
            if primary_text:
                logger.info(
                    "[STT][HEARD] %s (lang=%s source=listen_any)",
                    _highlight_heard_text(primary_text),
                    detected_language or "auto",
                )
                return primary_text
            if attempt < max_attempts - 1:
                time.sleep(0.1)
        logger.warning("[STT] Could not recognize audio in any provided language")
        return None

    def listen_command(
        self,
        timeout: float | None = None,
        phrase_time_limit: float | None = None,
        interrupt_event: Any | None = None,
        languages: list[str] | tuple[str, ...] | None = None,
        recognition_path: str = "local_first",
        usage_mode: str = "command",
        capture_profile_id: str | None = None,
        closed_vocabulary_id: str | None = None,
        closed_vocabulary_choices: Sequence[str] | None = None,
        dictionary_bias_mode: str | None = None,
        qualification_profile_id: str | None = None,
    ) -> str | None:
        """Capture and normalize a single command phrase."""
        result = self.listen_command_result(
            timeout_s=timeout,
            phrase_time_limit_s=phrase_time_limit,
            interrupt_event=interrupt_event,
            languages=languages,
            recognition_path=recognition_path,
            usage_mode=usage_mode,
            capture_profile_id=capture_profile_id,
            closed_vocabulary_id=closed_vocabulary_id,
            closed_vocabulary_choices=closed_vocabulary_choices,
            dictionary_bias_mode=dictionary_bias_mode,
            qualification_profile_id=qualification_profile_id,
        )
        if result is None or result.error_code:
            return None
        return result.primary_transcript.strip()

    def _recognize_candidates(
        self,
        audio: Any,
        *,
        languages: Sequence[str],
        for_command: bool = False,
        usage_mode: str = "wake",
        recognition_path: str = "local_first",
        closed_vocabulary_id: str | None = None,
        closed_vocabulary_choices: Sequence[str] | None = None,
    ) -> tuple[str | None, str | None, tuple[str, ...], float | None, dict[str, Any]]:
        entries: list[tuple[float, str, str, float | None, dict[str, Any]]] = []
        for language_code in languages:
            candidates = self._recognize_audio_candidates(
                audio,
                language_code=language_code,
                for_command=for_command,
                usage_mode=usage_mode,
                recognition_path=recognition_path,
                closed_vocabulary_id=closed_vocabulary_id,
                closed_vocabulary_choices=closed_vocabulary_choices,
            )
            for item in candidates:
                if len(item) == 4:
                    text, confidence, source, metadata = item
                else:
                    # Backward compatibility if tests monkeypatch old tuple shape.
                    text, confidence, source = item[:3]
                    metadata = {}
                normalized = self._normalize_transcript(text)
                if not normalized:
                    continue
                rank = self._rank_candidate(normalized, confidence=confidence, source=source)
                entry_metadata = dict(metadata)
                entry_metadata.setdefault("recognition_source", source)
                entry_metadata.setdefault("selected_language", language_code)
                entry_metadata.setdefault("detected_language", language_code)
                entry_metadata.setdefault("failure_reason_code", None)
                entries.append((rank, normalized, language_code, confidence, entry_metadata))

        if not entries:
            logger.info(
                "[STT][CANDIDATES] mode=%s path=%s languages=%s status=no_transcript",
                usage_mode,
                recognition_path,
                list(languages),
            )
            return None, None, (), None, {}

        entries.sort(key=lambda item: item[0], reverse=True)
        top_rank, top_text, top_language, top_confidence, top_metadata = entries[0]
        alternatives: list[str] = []
        for _, text, _, _, _ in entries:
            if text not in alternatives:
                alternatives.append(text)
            if len(alternatives) >= 4:
                break
        logger.info(
            "[STT][CANDIDATES] mode=%s path=%s top=%s lang=%s source=%s conf=%s rank=%.3f alternatives=%s",
            usage_mode,
            recognition_path,
            _highlight_heard_text(top_text),
            top_language,
            top_metadata.get("recognition_source", "unknown"),
            f"{top_confidence:.2f}" if isinstance(top_confidence, (int, float)) else "n/a",
            top_rank,
            alternatives,
        )
        return top_text, top_language, tuple(alternatives), top_confidence, dict(top_metadata)

    def _estimate_confidence(
        self,
        alternatives: Sequence[str],
        *,
        confidence_available: bool,
        raw_confidence: float | None = None,
    ) -> float | None:
        if not confidence_available:
            return None
        if raw_confidence is not None:
            return max(0.0, min(1.0, float(raw_confidence)))
        if not alternatives:
            return 0.0
        # Conservative estimate that degrades with competing alternatives.
        estimate = 0.92 - (0.08 * max(0, len(alternatives) - 1))
        return max(0.0, min(1.0, estimate))

    def listen_command_result(
        self,
        *,
        timeout_s: float | None = None,
        phrase_time_limit_s: float | None = None,
        interrupt_event: Any | None = None,
        languages: list[str] | tuple[str, ...] | None = None,
        recognition_path: str = "local_first",
        session_id: str | None = None,
        force_missing_confidence: bool = False,
        usage_mode: str = "command",
        capture_profile_id: str | None = None,
        closed_vocabulary_id: str | None = None,
        closed_vocabulary_choices: Sequence[str] | None = None,
        dictionary_bias_mode: str | None = None,
        qualification_profile_id: str | None = None,
        recovery_prompt_surface: str | None = None,
        attempt_index: int = 0,
    ) -> CommandRecognitionResult | None:
        """Capture one command with structured recognition metadata."""
        checker = getattr(interrupt_event, "is_set", None) if interrupt_event is not None else None
        if callable(checker) and checker():
            return None

        if not closed_vocabulary_choices and closed_vocabulary_id:
            closed_vocabulary_choices = registry_closed_vocabulary_choices(closed_vocabulary_id)

        usage_mode_value = normalize_usage_mode(usage_mode)
        qualification_profile = str(
            qualification_profile_id or self._default_qualification_profile_id
        ).strip().lower()
        profile_overrides = (
            {usage_mode_value: str(capture_profile_id)}
            if capture_profile_id is not None and str(capture_profile_id).strip()
            else None
        )
        capture_profile = select_capture_profile(
            usage_mode=usage_mode_value,
            profile_overrides=profile_overrides,
            dictionary_bias_mode=dictionary_bias_mode,
            closed_vocabulary_id=closed_vocabulary_id,
            qualification_profile=qualification_profile,
        )

        timeout = int(timeout_s) if timeout_s is not None else max(1, int(capture_profile.max_utterance_ms / 1000) + 1)
        phrase_time_limit = int(phrase_time_limit_s) if phrase_time_limit_s is not None else max(
            1,
            int(capture_profile.max_utterance_ms / 1000),
        )
        started_at = time.perf_counter()
        result_session_id = session_id or _session_id()
        language_candidates = self._language_candidates(languages)
        # Phase 14 keeps bounded relisten to at most one additional attempt.
        max_attempts = 2 if usage_mode_value in {"command", "confirmation"} else 1
        max_attempts = max(1, min(max_attempts, self.retries + 1))
        deadline = time.perf_counter() + max(0.8, float(timeout_s) if timeout_s is not None else float(timeout))

        primary_text: str | None = None
        detected_language: str | None = None
        alternatives: tuple[str, ...] = ()
        top_confidence: float | None = None
        selected_language: str | None = None
        recognition_source: str | None = None
        failure_reason_code: str | None = None
        best_capture_score = float("-inf")
        best_capture: tuple[str, str | None, tuple[str, ...], float | None, dict[str, Any]] | None = None
        best_capture_attempt: AudioCaptureAttempt | None = None
        last_capture_attempt: AudioCaptureAttempt | None = None

        for attempt in range(max_attempts):
            remaining = max(0.0, deadline - time.perf_counter())
            if remaining <= 0:
                break
            attempt_started_ms = int(time.perf_counter() * 1000)
            attempt_timeout = max(1, int(round(min(float(timeout), remaining))))
            attempt_phrase_limit = max(1, int(round(min(float(phrase_time_limit), remaining + 1.0))))
            attempt_prompt = "[STT] Listening..." if max_attempts == 1 else f"[STT] Listening... ({attempt + 1}/{max_attempts})"
            audio = self.listen_audio(
                prompt=attempt_prompt,
                timeout=attempt_timeout,
                phrase_time_limit=attempt_phrase_limit,
                interrupt_event=interrupt_event,
                hard_timeout_s=remaining,
            )
            if audio is None:
                continue
            preprocessing_outcome = preprocess_audio_for_capture(audio, profile=capture_profile)
            vad_profile = self._analyze_vad_profile(audio)
            recognition_payload = self._recognize_candidates(
                audio,
                languages=language_candidates,
                for_command=True,
                usage_mode=usage_mode_value,
                recognition_path=recognition_path,
                closed_vocabulary_id=closed_vocabulary_id,
                closed_vocabulary_choices=closed_vocabulary_choices,
            )
            if len(recognition_payload) == 5:
                primary_text, detected_language, alternatives, top_confidence, recognition_metadata = recognition_payload
            else:
                primary_text, detected_language, alternatives, top_confidence = recognition_payload
                recognition_metadata = {}
            clipping_start_suspected = bool(
                vad_profile and int(vad_profile.get("leading_silence_ms", 0) or 0) <= min(capture_profile.pre_roll_ms, 120)
            )
            clipping_end_suspected = self._is_likely_clipped_transcript(
                primary_text or "",
                vad_profile=vad_profile,
            )
            endpoint_quality_hints = derive_endpoint_quality_hints(
                vad_profile=vad_profile,
                profile=capture_profile,
                clipping_start_suspected=clipping_start_suspected,
                clipping_end_suspected=clipping_end_suspected,
            )
            attempt_capture = build_capture_attempt(
                session_id=result_session_id,
                profile=capture_profile,
                attempt_index=min(1, max(0, attempt_index + attempt)),
                started_at_ms=attempt_started_ms,
                ended_at_ms=int(time.perf_counter() * 1000),
                raw_duration_ms=preprocessing_outcome.raw_duration_ms,
                processed_duration_ms=preprocessing_outcome.processed_duration_ms,
                utterance_duration_ms=max(
                    0,
                    preprocessing_outcome.processed_duration_ms - capture_profile.pre_roll_ms - capture_profile.post_roll_ms,
                ),
                clipping_start_suspected=clipping_start_suspected,
                clipping_end_suspected=clipping_end_suspected,
                endpoint_quality_hints=endpoint_quality_hints,
                relisten_triggered=False,
                recovery_prompt_surface=recovery_prompt_surface,
            )
            last_capture_attempt = attempt_capture
            if primary_text:
                completeness = self._recognition_completeness_score(
                    primary_text=primary_text,
                    alternatives=alternatives,
                    raw_confidence=top_confidence,
                    vad_profile=vad_profile,
                )
                if completeness > best_capture_score:
                    best_capture_score = completeness
                    best_capture = (
                        primary_text,
                        detected_language,
                        alternatives,
                        top_confidence,
                        dict(recognition_metadata),
                    )
                    best_capture_attempt = attempt_capture
                remaining_after_recognition = max(0.0, deadline - time.perf_counter())
                should_retry = should_trigger_bounded_relisten(
                    attempt_index=attempt,
                    max_relisten_attempts=1,
                    clipping_start_suspected=clipping_start_suspected,
                    clipping_end_suspected=clipping_end_suspected,
                    endpoint_quality_hints=endpoint_quality_hints,
                    relisten_enabled=(
                        self._command_followup_relisten_enabled
                        and usage_mode_value in {"command", "confirmation"}
                        and remaining_after_recognition >= self._command_followup_relisten_min_remaining_s
                    ),
                )
                if not should_retry:
                    break
                attempt_capture = build_capture_attempt(
                    session_id=attempt_capture.session_id,
                    profile=capture_profile,
                    attempt_index=attempt_capture.attempt_index,
                    started_at_ms=attempt_capture.started_at_ms,
                    ended_at_ms=attempt_capture.ended_at_ms,
                    raw_duration_ms=attempt_capture.raw_duration_ms,
                    processed_duration_ms=attempt_capture.processed_duration_ms,
                    utterance_duration_ms=attempt_capture.utterance_duration_ms,
                    clipping_start_suspected=attempt_capture.clipping_start_suspected,
                    clipping_end_suspected=attempt_capture.clipping_end_suspected,
                    endpoint_quality_hints=attempt_capture.endpoint_quality_hints,
                    relisten_triggered=True,
                    recovery_prompt_surface=recovery_prompt_surface or "runtime.capture.retry_short",
                    speech_started_at_ms=attempt_capture.speech_started_at_ms,
                    speech_ended_at_ms=attempt_capture.speech_ended_at_ms,
                    capture_attempt_id=attempt_capture.capture_attempt_id,
                )
                best_capture_attempt = attempt_capture
                last_capture_attempt = attempt_capture
                if attempt < (max_attempts - 1):
                    time.sleep(self._command_followup_relisten_gap_s)
                continue
            if attempt < max_attempts - 1:
                time.sleep(0.12)

        if best_capture is not None:
            primary_text, detected_language, alternatives, top_confidence, recognition_metadata = best_capture
            selected_language = str(recognition_metadata.get("selected_language") or "") or None
            recognition_source = str(recognition_metadata.get("recognition_source") or "") or None
            failure_reason_code = str(recognition_metadata.get("failure_reason_code") or "") or None

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        if not primary_text:
            if failure_reason_code:
                self.last_error = failure_reason_code
            return CommandRecognitionResult(
                session_id=result_session_id,
                recognition_path=recognition_path,
                provider_id=self.provider_id,
                primary_transcript="",
                confidence_score=None,
                confidence_available=False,
                alternative_transcripts=(),
                detected_language=None,
                language_candidates=tuple(language_candidates),
                capture_attempt_id=(
                    last_capture_attempt.capture_attempt_id if last_capture_attempt is not None else None
                ),
                profile_id=capture_profile.profile_id,
                dictionary_bias_applied=(capture_profile.dictionary_bias_mode != "none"),
                dictionary_bias_mode=capture_profile.dictionary_bias_mode,
                closed_vocabulary_id=capture_profile.closed_vocabulary_id,
                endpoint_quality_hints=(
                    last_capture_attempt.endpoint_quality_hints if last_capture_attempt is not None else ()
                ),
                capture_attempt=last_capture_attempt,
                qualification_profile_id=qualification_profile,
                latency_ms=latency_ms,
                error_code=self.last_error or "unknown_value",
                recognition_source=recognition_source,
                failure_reason_code=failure_reason_code,
                selected_language=selected_language,
            )

        logger.info(
            "[STT][HEARD] %s (lang=%s source=command mode=%s)",
            _highlight_heard_text(primary_text),
            detected_language or "auto",
            usage_mode_value,
        )
        confidence_available = not force_missing_confidence
        confidence_score = self._estimate_confidence(
            alternatives,
            confidence_available=confidence_available,
            raw_confidence=top_confidence,
        )
        return CommandRecognitionResult(
            session_id=result_session_id,
            recognition_path=recognition_path,
            provider_id=self.provider_id,
            primary_transcript=primary_text,
            confidence_score=confidence_score,
            confidence_available=confidence_available,
            alternative_transcripts=alternatives,
            detected_language=detected_language,
            language_candidates=tuple(language_candidates),
            capture_attempt_id=(
                best_capture_attempt.capture_attempt_id if best_capture_attempt is not None else None
            ),
            profile_id=capture_profile.profile_id,
            dictionary_bias_applied=(capture_profile.dictionary_bias_mode != "none"),
            dictionary_bias_mode=capture_profile.dictionary_bias_mode,
            closed_vocabulary_id=capture_profile.closed_vocabulary_id,
            endpoint_quality_hints=(
                best_capture_attempt.endpoint_quality_hints if best_capture_attempt is not None else ()
            ),
            capture_attempt=best_capture_attempt,
            qualification_profile_id=qualification_profile,
            latency_ms=latency_ms,
            error_code=None,
            recognition_source=recognition_source,
            failure_reason_code=failure_reason_code,
            selected_language=selected_language,
        )

    def listen_command_window(
        self,
        *,
        timeout_s: float | None = None,
        phrase_time_limit_s: float | None = None,
        interrupt_event: Any | None = None,
        languages: list[str] | tuple[str, ...] | None = None,
        usage_mode: str = "command",
        closed_vocabulary_id: str | None = None,
        closed_vocabulary_choices: Sequence[str] | None = None,
    ) -> str | None:
        """Capture one command inside a bounded session window."""
        result = self.listen_command_result(
            timeout_s=timeout_s,
            phrase_time_limit_s=phrase_time_limit_s,
            interrupt_event=interrupt_event,
            languages=languages,
            recognition_path="local_first",
            usage_mode=usage_mode,
            closed_vocabulary_id=closed_vocabulary_id,
            closed_vocabulary_choices=closed_vocabulary_choices,
        )
        if result is None or result.error_code:
            return None
        return result.primary_transcript.strip()

    def is_available(self) -> bool:
        return True


if __name__ == "__main__":
    listener = VoiceListener(default_language="ar-EG")  # افتراضي عربي
    while True:
        command_text = listener.listen_command()
        if command_text:
            logger.info("[MAIN] Command to Dispatcher: %s", command_text)
