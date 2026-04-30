"""Optional Google Cloud STT boundary with field-safe failure classification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import time
from typing import Any, Callable, Sequence

from core.command_models import CLOUD_FAILURE_REASON_CODES

try:  # pragma: no cover - optional dependency path
    from google.api_core import exceptions as gcloud_exceptions  # type: ignore
except Exception:  # noqa: BLE001
    gcloud_exceptions = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency path
    from google.cloud import speech_v2 as google_speech_v2  # type: ignore
except Exception:  # noqa: BLE001
    google_speech_v2 = None  # type: ignore[assignment]


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


@dataclass(frozen=True)
class CloudRecognitionCandidate:
    provider_source: str
    status: str
    recognition_path: str
    primary_transcript: str | None
    confidence_available: bool
    confidence_score: float | None
    alternative_transcripts: tuple[str, ...]
    selected_language: str
    detected_language: str | None
    latency_ms: int
    failure_reason_code: str | None
    field_safe: bool = True
    raw_user_content_persisted: bool = False

    @property
    def is_usable(self) -> bool:
        return self.status == "recognized" and bool(str(self.primary_transcript or "").strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_source": self.provider_source,
            "status": self.status,
            "recognition_path": self.recognition_path,
            "primary_transcript": self.primary_transcript,
            "confidence_available": self.confidence_available,
            "confidence_score": self.confidence_score,
            "alternative_transcripts": tuple(self.alternative_transcripts),
            "selected_language": self.selected_language,
            "detected_language": self.detected_language,
            "latency_ms": max(0, int(self.latency_ms)),
            "failure_reason_code": self.failure_reason_code,
            "field_safe": bool(self.field_safe),
            "raw_user_content_persisted": bool(self.raw_user_content_persisted),
        }


class GoogleCloudSTTRecognizer:
    """Optional cloud recognizer used by the legacy listener when enabled."""

    def __init__(
        self,
        *,
        timeout_s: float = 3.0,
        max_alternatives: int = 3,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.timeout_s = _safe_float(timeout_s, 3.0)
        self.max_alternatives = _safe_int(max_alternatives, 3)
        self._client_factory = client_factory

    def _credentials_available(self) -> bool:
        raw = str(os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "") or "").strip()
        if not raw:
            return False
        return Path(raw).exists()

    def _client_import_available(self) -> bool:
        return google_speech_v2 is not None or self._client_factory is not None

    def availability_state(self) -> dict[str, Any]:
        checked_at_ms = int(time.time() * 1000)
        if not self._client_import_available():
            return {
                "provider_source": "cloud_primary",
                "availability": "unavailable",
                "credential_state": "not_required",
                "client_import_state": "missing",
                "network_required": True,
                "startup_safe": True,
                "reason_code": "cloud_client_import_missing",
                "checked_at_ms": checked_at_ms,
            }
        if not self._credentials_available():
            return {
                "provider_source": "cloud_primary",
                "availability": "unavailable",
                "credential_state": "missing",
                "client_import_state": "available",
                "network_required": True,
                "startup_safe": True,
                "reason_code": "cloud_credentials_missing",
                "checked_at_ms": checked_at_ms,
            }
        return {
            "provider_source": "cloud_primary",
            "availability": "ready",
            "credential_state": "available",
            "client_import_state": "available",
            "network_required": True,
            "startup_safe": True,
            "reason_code": None,
            "checked_at_ms": checked_at_ms,
        }

    def _build_client(self) -> Any:
        if self._client_factory is not None:
            return self._client_factory()
        if google_speech_v2 is None:  # pragma: no cover - guarded by availability check
            return None
        try:
            return google_speech_v2.SpeechClient()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            return None

    def _audio_bytes(self, audio: Any) -> bytes:
        getter = getattr(audio, "get_raw_data", None)
        if not callable(getter):
            return b""
        try:
            return bytes(getter(convert_rate=16_000, convert_width=2))
        except Exception:  # noqa: BLE001
            return b""

    def _classify_error(self, error: Exception) -> str:
        name = type(error).__name__.lower()
        message = str(error).lower()
        if "timeout" in name or "deadline" in name or "timeout" in message:
            return "cloud_network_timeout"
        if (
            "unauthenticated" in name
            or "permission" in name
            or "auth" in name
            or "unauthenticated" in message
            or "permission" in message
            or "auth" in message
        ):
            return "cloud_auth_error"
        if "quota" in name or "resourceexhausted" in name or "quota" in message:
            return "cloud_quota_error"
        if "serviceunavailable" in name or "unavailable" in name or "service unavailable" in message:
            return "cloud_service_unavailable"
        if gcloud_exceptions is not None:
            if isinstance(error, getattr(gcloud_exceptions, "DeadlineExceeded", ())):
                return "cloud_network_timeout"
            if isinstance(
                error,
                (
                    getattr(gcloud_exceptions, "Unauthenticated", ()),
                    getattr(gcloud_exceptions, "PermissionDenied", ()),
                ),
            ):
                return "cloud_auth_error"
            if isinstance(error, getattr(gcloud_exceptions, "ResourceExhausted", ())):
                return "cloud_quota_error"
            if isinstance(error, getattr(gcloud_exceptions, "ServiceUnavailable", ())):
                return "cloud_service_unavailable"
        return "cloud_unknown_failure"

    def _normalize_transcript(self, value: str | None) -> str:
        return " ".join(str(value or "").strip().split())

    def _normalize_alternatives(self, values: Sequence[str]) -> tuple[str, ...]:
        unique: list[str] = []
        for item in values:
            normalized = self._normalize_transcript(item)
            if not normalized:
                continue
            if normalized in unique:
                continue
            unique.append(normalized)
            if len(unique) >= self.max_alternatives:
                break
        return tuple(unique)

    def _build_request_payload(
        self,
        *,
        audio_bytes: bytes,
        selected_language: str,
        phrase_hints: Sequence[str],
    ) -> dict[str, Any]:
        return {
            "content": audio_bytes,
            "selected_language": selected_language,
            "max_alternatives": self.max_alternatives,
            "phrase_hints": list(phrase_hints),
        }

    def _extract_candidates(self, payload: Any, *, selected_language: str) -> CloudRecognitionCandidate:
        alternatives: list[str] = []
        confidence_score: float | None = None
        detected_language: str | None = None

        if isinstance(payload, dict):
            raw_alts = payload.get("alternatives") or payload.get("alternative") or ()
            for item in list(raw_alts):
                if isinstance(item, dict):
                    transcript = self._normalize_transcript(str(item.get("transcript", "") or ""))
                    if transcript:
                        alternatives.append(transcript)
                    confidence = item.get("confidence")
                    if confidence_score is None and isinstance(confidence, (float, int)):
                        confidence_score = float(confidence)
            detected_language = str(payload.get("detected_language") or payload.get("language_code") or "") or None
        else:
            response_results = list(getattr(payload, "results", ()) or ())
            for result in response_results:
                detected_language = (
                    str(getattr(result, "language_code", "") or "")
                    or detected_language
                )
                for alt in list(getattr(result, "alternatives", ()) or ()):
                    transcript = self._normalize_transcript(str(getattr(alt, "transcript", "") or ""))
                    if transcript:
                        alternatives.append(transcript)
                    confidence = getattr(alt, "confidence", None)
                    if confidence_score is None and isinstance(confidence, (float, int)):
                        confidence_score = float(confidence)

        normalized = self._normalize_alternatives(alternatives)
        if not normalized:
            return CloudRecognitionCandidate(
                provider_source="cloud_primary",
                status="empty_result",
                recognition_path="local_first",
                primary_transcript=None,
                confidence_available=False,
                confidence_score=None,
                alternative_transcripts=(),
                selected_language=selected_language,
                detected_language=detected_language,
                latency_ms=0,
                failure_reason_code="cloud_empty_result",
            )

        return CloudRecognitionCandidate(
            provider_source="cloud_primary",
            status="recognized",
            recognition_path="local_first",
            primary_transcript=normalized[0],
            confidence_available=confidence_score is not None,
            confidence_score=confidence_score,
            alternative_transcripts=normalized,
            selected_language=selected_language,
            detected_language=detected_language,
            latency_ms=0,
            failure_reason_code=None,
        )

    def recognize_short_utterance(
        self,
        *,
        audio: Any,
        selected_language: str,
        phrase_hints: Sequence[str],
        recognition_path: str = "local_first",
    ) -> CloudRecognitionCandidate:
        started_at = time.perf_counter()
        availability = self.availability_state()
        if availability["availability"] != "ready":
            reason_code = "cloud_credentials_missing"
            if availability.get("reason_code") == "cloud_client_import_missing":
                reason_code = "cloud_unknown_failure"
            return CloudRecognitionCandidate(
                provider_source="cloud_primary",
                status="unavailable",
                recognition_path=recognition_path,
                primary_transcript=None,
                confidence_available=False,
                confidence_score=None,
                alternative_transcripts=(),
                selected_language=selected_language,
                detected_language=None,
                latency_ms=int((time.perf_counter() - started_at) * 1000),
                failure_reason_code=reason_code,
            )

        audio_bytes = self._audio_bytes(audio)
        if not audio_bytes:
            return CloudRecognitionCandidate(
                provider_source="cloud_primary",
                status="empty_result",
                recognition_path=recognition_path,
                primary_transcript=None,
                confidence_available=False,
                confidence_score=None,
                alternative_transcripts=(),
                selected_language=selected_language,
                detected_language=None,
                latency_ms=int((time.perf_counter() - started_at) * 1000),
                failure_reason_code="cloud_empty_result",
            )

        client = self._build_client()
        if client is None:
            return CloudRecognitionCandidate(
                provider_source="cloud_primary",
                status="failed",
                recognition_path=recognition_path,
                primary_transcript=None,
                confidence_available=False,
                confidence_score=None,
                alternative_transcripts=(),
                selected_language=selected_language,
                detected_language=None,
                latency_ms=int((time.perf_counter() - started_at) * 1000),
                failure_reason_code="cloud_unknown_failure",
            )

        request_payload = self._build_request_payload(
            audio_bytes=audio_bytes,
            selected_language=selected_language,
            phrase_hints=phrase_hints,
        )
        retries_used = 0
        last_error: Exception | None = None

        while retries_used <= 1:
            try:
                recognize = getattr(client, "recognize", None)
                if not callable(recognize):
                    raise RuntimeError("cloud_client_missing_recognize")
                response = recognize(request=request_payload, timeout=self.timeout_s)
                candidate = self._extract_candidates(response, selected_language=selected_language)
                return CloudRecognitionCandidate(
                    provider_source=candidate.provider_source,
                    status=candidate.status,
                    recognition_path=recognition_path,
                    primary_transcript=candidate.primary_transcript,
                    confidence_available=candidate.confidence_available,
                    confidence_score=candidate.confidence_score,
                    alternative_transcripts=candidate.alternative_transcripts,
                    selected_language=candidate.selected_language,
                    detected_language=candidate.detected_language,
                    latency_ms=int((time.perf_counter() - started_at) * 1000),
                    failure_reason_code=candidate.failure_reason_code,
                )
            except Exception as err:  # noqa: BLE001
                last_error = err
                reason = self._classify_error(err)
                if reason in {"cloud_network_timeout", "cloud_service_unavailable"} and retries_used < 1:
                    retries_used += 1
                    continue
                break

        reason_code = self._classify_error(last_error) if last_error is not None else "cloud_unknown_failure"
        if reason_code not in CLOUD_FAILURE_REASON_CODES:
            reason_code = "cloud_unknown_failure"
        return CloudRecognitionCandidate(
            provider_source="cloud_primary",
            status="failed",
            recognition_path=recognition_path,
            primary_transcript=None,
            confidence_available=False,
            confidence_score=None,
            alternative_transcripts=(),
            selected_language=selected_language,
            detected_language=None,
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            failure_reason_code=reason_code,
        )
