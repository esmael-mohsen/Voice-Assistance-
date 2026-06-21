"""Vision capability controller backed by the Assistive-Vision-System project."""

from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import importlib
import io
import logging
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Protocol
from uuid import uuid4

from controllers.capability_contracts import (
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatusSnapshot,
    CapabilityTimeoutPolicy,
    build_result,
    invoke_with_timeout,
)
from controllers.external_process_runtime import build_external_process_env, write_launch_diagnostics
from settings.settings_manager import settings_manager

logger = logging.getLogger(__name__)

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

VISION_CAPABILITIES = frozenset({"face_recognition", "emotion_recognition"})
DEFAULT_VISION_PROJECT_PATH = Path(__file__).resolve().parents[2] / "Assistive-Vision-System"
VISION_PROJECT_ENV = "EGB_VISION_PROJECT_PATH"
VISION_PYTHON_ENV = "EGB_VISION_PYTHON"
VISION_CAMERA_ENV = "EGB_VISION_CAMERA_INDEX"
VISION_FRAME_WARMUP_ENV = "EGB_VISION_FRAME_WARMUP"
VISION_CAPTURE_ATTEMPTS_ENV = "EGB_VISION_CAPTURE_ATTEMPTS"
VISION_CAPTURE_RETRY_MS_ENV = "EGB_VISION_CAPTURE_RETRY_MS"
VISION_BACKEND_NAME = "assistive_vision_system"
VISION_PROCESS_BACKEND_NAME = "assistive_vision_process"
VISION_STOP_FILE_ENV = "AVS_STOP_FILE"
VISION_LOG_DIR_ENV = "EGB_VISION_LOG_DIR"

_EMOTION_TRANSLATIONS = {
    "angry": "غاضب",
    "disgust": "منزعج",
    "fear": "خائف",
    "happy": "سعيد",
    "neutral": "محايد",
    "sad": "حزين",
    "surprise": "متفاجئ",
}


class VisionAdapter(Protocol):
    def is_available(self, capability_id: str) -> bool: ...
    def recognize_face(self, *, store_new_face: bool = False) -> dict[str, Any]: ...
    def recognize_emotion(self, *, face_id: str | None = None) -> dict[str, Any]: ...
    def describe_health(self) -> dict[str, Any]: ...


def _safe_int(value: str | None, default: int) -> int:
    try:
        return int(str(value).strip()) if value is not None else default
    except (TypeError, ValueError):
        return default


class AssistiveVisionAdapter:
    """Adapter that reuses the face/emotion logic from Assistive-Vision-System."""

    def __init__(
        self,
        *,
        project_path: str | Path | None = None,
        camera_index: int | None = None,
        frame_warmup_reads: int | None = None,
    ) -> None:
        resolved_project = Path(
            os.environ.get(VISION_PROJECT_ENV) or project_path or DEFAULT_VISION_PROJECT_PATH
        ).resolve()
        self._project_path = resolved_project
        self._camera_index_override = camera_index
        self._frame_warmup_reads = max(
            1,
            frame_warmup_reads
            if frame_warmup_reads is not None
            else _safe_int(os.environ.get(VISION_FRAME_WARMUP_ENV), 3),
        )
        self._capture_attempts = max(1, _safe_int(os.environ.get(VISION_CAPTURE_ATTEMPTS_ENV), 2))
        self._capture_retry_delay_s = max(
            0.0,
            _safe_int(os.environ.get(VISION_CAPTURE_RETRY_MS_ENV), 120) / 1000.0,
        )
        self._bootstrap_lock = threading.Lock()
        self._runtime_lock = threading.Lock()
        self._bootstrapped = False

        self._cv2: Any | None = None
        self._np: Any | None = None
        self._vision_config: Any | None = None
        self._face_processor: Any | None = None
        self._face_db: Any | None = None
        self._emotion_detector: Any | None = None
        self._face_health_error: str | None = None
        self._emotion_health_error: str | None = None
        self._dependency_error: str | None = None

    def _refresh_dependency_error(self) -> None:
        self._dependency_error = self._face_health_error or self._emotion_health_error

    def _emotion_model_candidate_paths(self) -> tuple[Path, ...]:
        if self._vision_config is None:
            return ()
        configured_path = Path(str(getattr(self._vision_config, "MODEL_PATH", "")))
        candidates: list[Path] = []
        if str(configured_path):
            candidates.append(configured_path)
        fallback_path = self._project_path / "model" / "emotion_model.keras"
        if fallback_path not in candidates:
            candidates.append(fallback_path)
        return tuple(candidates)

    def _bootstrap_emotion_runtime(self) -> None:
        self._emotion_health_error = None
        try:
            with ExitStack() as stack:
                buffer = io.StringIO()
                stack.enter_context(redirect_stdout(buffer))
                stack.enter_context(redirect_stderr(buffer))

                # Match the upstream project bootstrap order: emotion model first,
                # then DeepFace later, to avoid tf-keras compatibility regressions.
                os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
                model_loader = importlib.import_module("tensorflow.keras.models").load_model
                face_detector_module = importlib.import_module("emotion.face_detector")

                last_error: Exception | None = None
                for model_path in self._emotion_model_candidate_paths():
                    if not model_path.exists():
                        continue
                    try:
                        emotion_model = model_loader(str(model_path), compile=False)
                        self._emotion_detector = face_detector_module.FaceEmotionDetector(emotion_model)
                        self._emotion_health_error = None
                        return
                    except Exception as exc:  # noqa: BLE001
                        last_error = exc

            if last_error is not None:
                raise last_error
            self._emotion_health_error = "emotion_model_missing"
        except Exception as exc:  # noqa: BLE001
            logger.warning("[VISION] Failed to bootstrap emotion runtime: %s", exc)
            self._emotion_health_error = "vision_emotion_dependency_missing"

    def _bootstrap_face_runtime(self) -> None:
        self._face_health_error = None
        try:
            with ExitStack() as stack:
                buffer = io.StringIO()
                stack.enter_context(redirect_stdout(buffer))
                stack.enter_context(redirect_stderr(buffer))

                face_processor_module = importlib.import_module("face.face_processor")
                face_db_module = importlib.import_module("face.face_db")
                self._face_processor = face_processor_module.FaceProcessor()
                self._face_db = face_db_module.FaceDB(path=str(self._vision_config.FACE_DB_PATH))

            self._face_health_error = self._validate_face_runtime()
            if self._face_health_error is None:
                return
        except Exception as exc:  # noqa: BLE001
            logger.warning("[VISION] Failed to bootstrap face runtime: %s", exc)
            self._face_health_error = "vision_face_dependency_missing"

    def _face_embedding_vector_size(self) -> int | None:
        if self._face_db is None:
            return None
        try:
            database = self._face_db.all()
        except Exception:  # noqa: BLE001
            return None
        for record in database.values():
            embeddings = getattr(record, "embeddings", None)
            if not embeddings:
                continue
            sample = embeddings[0]
            shape = getattr(sample, "shape", None)
            if shape and len(shape) == 1:
                try:
                    return int(shape[0])
                except (TypeError, ValueError):
                    return None
            try:
                return len(sample)
            except TypeError:
                return None
        return None

    def _validate_face_runtime(self) -> str | None:
        if self._face_processor is None or self._face_db is None:
            return None
        embedding_vector_size = self._face_embedding_vector_size()
        deepface_ready = bool(getattr(self._face_processor, "_df_ok", False))
        if embedding_vector_size == 512 and not deepface_ready:
            return "vision_face_embedding_backend_missing"
        return None

    def _localized(self, ar_text: str, en_text: str) -> str:
        return settings_manager.speak_localized(ar_text, en_text)

    def _bootstrap(self) -> None:
        if self._bootstrapped:
            return

        with self._bootstrap_lock:
            if self._bootstrapped:
                return

            self._bootstrapped = True

            if not self._project_path.exists():
                self._dependency_error = "vision_project_missing"
                self._face_health_error = "vision_project_missing"
                self._emotion_health_error = "vision_project_missing"
                return

            project_path_str = str(self._project_path)
            if project_path_str not in sys.path:
                sys.path.insert(0, project_path_str)

            try:
                self._cv2 = importlib.import_module("cv2")
                self._np = importlib.import_module("numpy")
                self._vision_config = importlib.import_module("config")
            except Exception as exc:  # noqa: BLE001
                logger.warning("[VISION] Failed to bootstrap vision runtime: %s", exc)
                self._face_health_error = "vision_face_dependency_missing"
                self._emotion_health_error = "vision_emotion_dependency_missing"
                self._refresh_dependency_error()
                return

            self._bootstrap_emotion_runtime()
            self._bootstrap_face_runtime()
            self._refresh_dependency_error()

    def _camera_index(self) -> int:
        if self._camera_index_override is not None:
            return int(self._camera_index_override)
        if self._vision_config is not None:
            return _safe_int(os.environ.get(VISION_CAMERA_ENV), int(getattr(self._vision_config, "CAMERA_INDEX", 0)))
        return _safe_int(os.environ.get(VISION_CAMERA_ENV), 0)

    def _camera_index_candidates(self) -> tuple[int, ...]:
        preferred = self._camera_index()
        candidates = [preferred]
        for fallback_index in (0, 1, 2):
            if fallback_index not in candidates:
                candidates.append(fallback_index)
        return tuple(candidates)

    def _capture_frame(self) -> tuple[Any | None, str | None]:
        if self._cv2 is None:
            return None, "opencv_unavailable"

        camera_candidates = self._camera_index_candidates()
        runtime_target = str(os.environ.get("EGB_RUNTIME_TARGET", "") or "").strip().lower()
        if runtime_target == "raspberry_pi":
            api_preferences = [None]
        else:
            api_preferences = [getattr(self._cv2, "CAP_DSHOW", None), None]
        for attempt_index in range(self._capture_attempts):
            for camera_index in camera_candidates:
                for api_preference in api_preferences:
                    capture = None
                    try:
                        capture = (
                            self._cv2.VideoCapture(camera_index, api_preference)
                            if api_preference is not None
                            else self._cv2.VideoCapture(camera_index)
                        )
                        if not capture or not capture.isOpened():
                            continue

                        if self._vision_config is not None:
                            capture.set(
                                self._cv2.CAP_PROP_FRAME_WIDTH,
                                int(getattr(self._vision_config, "FRAME_WIDTH", 640)),
                            )
                            capture.set(
                                self._cv2.CAP_PROP_FRAME_HEIGHT,
                                int(getattr(self._vision_config, "FRAME_HEIGHT", 480)),
                            )

                        frame = None
                        for _ in range(self._frame_warmup_reads):
                            ok, candidate = capture.read()
                            if ok and candidate is not None:
                                frame = candidate

                        if frame is not None:
                            if attempt_index > 0 or camera_index != camera_candidates[0]:
                                logger.info(
                                    "[VISION] Camera capture recovered attempt=%s camera_index=%s preferred_index=%s",
                                    attempt_index + 1,
                                    camera_index,
                                    camera_candidates[0],
                                )
                            return frame, None
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("[VISION] Camera capture failed: %s", exc)
                    finally:
                        if capture is not None:
                            capture.release()
            if attempt_index + 1 < self._capture_attempts and self._capture_retry_delay_s > 0:
                time.sleep(self._capture_retry_delay_s)

        return None, "camera_unavailable"

    def _largest_box(self, boxes: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int] | None:
        if not boxes:
            return None
        return max(boxes, key=lambda item: int(item[2]) * int(item[3]))

    def _face_analysis(
        self,
        frame: Any,
        *,
        preferred_box: tuple[int, int, int, int] | None = None,
    ) -> dict[str, Any]:
        if self._face_processor is None or self._face_db is None:
            return {"error_code": "vision_face_dependency_missing"}

        boxes: list[tuple[int, int, int, int]]
        if preferred_box is not None:
            boxes = [preferred_box]
        else:
            boxes = list(self._face_processor.detect(frame))

        target_box = self._largest_box(boxes)
        if target_box is None:
            return {"error_code": "no_face_detected"}

        is_live, liveness_score = self._face_processor.is_live(frame, target_box)
        if not is_live:
            return {
                "error_code": "liveness_check_failed",
                "detected": True,
                "liveness_score": float(liveness_score),
                "box": target_box,
            }

        embedding = self._face_processor.embed(frame, target_box)
        if embedding is None:
            return {
                "error_code": "face_embedding_failed",
                "detected": True,
                "liveness_score": float(liveness_score),
                "box": target_box,
            }

        database = self._face_db.all()
        if self._face_processor.identify_blocked(embedding, database):
            return {
                "detected": True,
                "identified": True,
                "blocked": True,
                "face_id": "Blocked",
                "match_score": 1.0,
                "liveness_score": float(liveness_score),
                "box": target_box,
            }

        face_id, match_score = self._face_processor.identify(embedding, database, target_box)
        identified = face_id != "Unknown"
        return {
            "detected": True,
            "identified": identified,
            "blocked": False,
            "face_id": face_id if identified else None,
            "match_score": float(match_score),
            "liveness_score": float(liveness_score),
            "box": target_box,
        }

    def _emotion_label_ar(self, emotion: str) -> str:
        return _EMOTION_TRANSLATIONS.get(emotion.strip().lower(), "غير واضح")

    def is_available(self, capability_id: str) -> bool:
        self._bootstrap()
        if capability_id == "face_recognition":
            return self._face_health_error is None
        if capability_id == "emotion_recognition":
            return self._emotion_health_error is None
        return False

    def describe_health(self) -> dict[str, Any]:
        self._bootstrap()
        return {
            "project_path": str(self._project_path),
            "project_path_exists": self._project_path.exists(),
            "camera_index": self._camera_index(),
            "camera_index_candidates": list(self._camera_index_candidates()),
            "capture_attempts": self._capture_attempts,
            "capture_retry_delay_ms": int(self._capture_retry_delay_s * 1000),
            "face_embedding_vector_size": self._face_embedding_vector_size(),
            "face_embedding_backend_ready": bool(
                self._face_processor is not None and getattr(self._face_processor, "_df_ok", False)
            ),
            "face_database_path": str(getattr(self._vision_config, "FACE_DB_PATH", "")) if self._vision_config else None,
            "emotion_model_path": str(getattr(self._vision_config, "MODEL_PATH", "")) if self._vision_config else None,
            "dependency_error": self._dependency_error,
            "capabilities": {
                "face_recognition": {
                    "available": self._face_health_error is None,
                    "error_code": self._face_health_error,
                },
                "emotion_recognition": {
                    "available": self._emotion_health_error is None,
                    "error_code": self._emotion_health_error,
                },
            },
        }

    def recognize_face(self, *, store_new_face: bool = False) -> dict[str, Any]:
        self._bootstrap()
        if store_new_face:
            return {
                "status": "rejected",
                "error_code": "face_enrollment_not_supported",
                "spoken_text": self._localized(
                    "تسجيل الوجوه غير مدمج داخل المساعد الصوتي بعد.",
                    "Face enrollment is not integrated into the voice assistant yet.",
                ),
                "payload": {
                    "allow_emotion_follow_up": False,
                    "store_new_face_requested": True,
                },
            }
        if self._face_health_error is not None:
            return {
                "status": "unavailable",
                "error_code": self._face_health_error,
                "spoken_text": self._localized(
                    "ميزة التعرف على الوجه غير متاحة حالياً.",
                    "Face recognition is currently unavailable.",
                ),
                "payload": {
                    "allow_emotion_follow_up": False,
                },
            }

        frame, capture_error = self._capture_frame()
        if frame is None:
            return {
                "status": "unavailable",
                "error_code": capture_error or "camera_unavailable",
                "spoken_text": self._localized(
                    "تعذر الوصول إلى الكاميرا الخاصة بالرؤية الآن.",
                    "I could not access the vision camera right now.",
                ),
                "payload": {
                    "allow_emotion_follow_up": False,
                },
            }

        with self._runtime_lock:
            analysis = self._face_analysis(frame)

        captured_at = datetime.now(timezone.utc).isoformat()
        error_code = str(analysis.get("error_code") or "")
        common_payload = {
            "captured_at": captured_at,
            "camera_index": self._camera_index(),
            "allow_emotion_follow_up": False,
            "source_project": str(self._project_path),
        }
        if analysis.get("box") is not None:
            common_payload["face_box"] = list(analysis["box"])
        if analysis.get("liveness_score") is not None:
            common_payload["liveness_score"] = float(analysis["liveness_score"])

        if error_code == "no_face_detected":
            return {
                "status": "failed",
                "error_code": "no_face_detected",
                "spoken_text": self._localized(
                    "لم أتمكن من العثور على وجه واضح أمام الكاميرا.",
                    "I could not find a clear face in front of the camera.",
                ),
                "payload": common_payload,
            }
        if error_code == "liveness_check_failed":
            return {
                "status": "failed",
                "error_code": "liveness_check_failed",
                "spoken_text": self._localized(
                    "رأيت وجهاً لكن فحص الحيوية لم ينجح.",
                    "I saw a face, but the liveness check did not pass.",
                ),
                "payload": common_payload,
            }
        if error_code:
            return {
                "status": "failed",
                "error_code": error_code,
                "spoken_text": self._localized(
                    "حدثت مشكلة أثناء تحليل الوجه.",
                    "There was a problem while analyzing the face.",
                ),
                "payload": common_payload,
            }

        if analysis.get("blocked"):
            return {
                "status": "success",
                "error_code": None,
                "spoken_text": self._localized(
                    "تم رصد شخص محظور أمام الكاميرا.",
                    "A blocked face was detected.",
                ),
                "payload": {
                    **common_payload,
                    "detected": True,
                    "identified": True,
                    "blocked": True,
                    "face_id": "Blocked",
                    "match_score": float(analysis.get("match_score", 1.0)),
                },
            }

        if not analysis.get("identified"):
            return {
                "status": "success",
                "error_code": None,
                "spoken_text": self._localized(
                    "رأيت وجهاً لكنني لم أتمكن من التعرف عليه.",
                    "I can see a face, but I could not identify it.",
                ),
                "payload": {
                    **common_payload,
                    "detected": True,
                    "identified": False,
                    "face_id": None,
                    "match_score": float(analysis.get("match_score", 0.0)),
                },
            }

        face_id = str(analysis["face_id"])
        return {
            "status": "success",
            "error_code": None,
            "spoken_text": self._localized(
                f"تم التعرف على الوجه {face_id}.",
                f"Face {face_id} recognized.",
            ),
            "payload": {
                **common_payload,
                "detected": True,
                "identified": True,
                "blocked": False,
                "face_id": face_id,
                "match_score": float(analysis.get("match_score", 0.0)),
                "allow_emotion_follow_up": True,
            },
        }

    def recognize_emotion(self, *, face_id: str | None = None) -> dict[str, Any]:
        self._bootstrap()
        if self._emotion_health_error is not None:
            return {
                "status": "unavailable",
                "error_code": self._emotion_health_error,
                "spoken_text": self._localized(
                    "ميزة التعرف على المشاعر غير متاحة حالياً.",
                    "Emotion recognition is currently unavailable.",
                ),
                "payload": {"face_id": face_id},
            }

        frame, capture_error = self._capture_frame()
        if frame is None:
            return {
                "status": "unavailable",
                "error_code": capture_error or "camera_unavailable",
                "spoken_text": self._localized(
                    "تعذر الوصول إلى الكاميرا الخاصة بالرؤية الآن.",
                    "I could not access the vision camera right now.",
                ),
                "payload": {"face_id": face_id},
            }

        with self._runtime_lock:
            frame_gray = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2GRAY)
            detection = self._emotion_detector.detect(frame_gray, frame)

        if detection is None:
            return {
                "status": "failed",
                "error_code": "no_face_detected",
                "spoken_text": self._localized(
                    "لم أتمكن من العثور على وجه واضح لتحليل المشاعر.",
                    "I could not find a clear face to analyze the emotion.",
                ),
                "payload": {"face_id": face_id},
            }

        emotion, confidence, face_box = detection
        resolved_face_id = face_id
        identified_face = False

        if resolved_face_id is None and self._face_health_error is None:
            with self._runtime_lock:
                face_analysis = self._face_analysis(frame, preferred_box=tuple(face_box))
            if face_analysis.get("identified") and not face_analysis.get("blocked"):
                resolved_face_id = str(face_analysis["face_id"])
                identified_face = True

        emotion_label = str(emotion)
        emotion_label_lower = emotion_label.lower()
        emotion_label_ar = self._emotion_label_ar(emotion_label)
        if resolved_face_id:
            spoken_text = self._localized(
                f"تبدو الحالة المزاجية للوجه {resolved_face_id} {emotion_label_ar}.",
                f"Detected a {emotion_label_lower} emotion for {resolved_face_id}.",
            )
        else:
            spoken_text = self._localized(
                f"تبدو الحالة المزاجية للوجه أمامي {emotion_label_ar}.",
                f"Detected a {emotion_label_lower} emotion.",
            )

        return {
            "status": "success",
            "error_code": None,
            "spoken_text": spoken_text,
            "payload": {
                "face_id": resolved_face_id,
                "emotion": emotion_label,
                "confidence": float(confidence),
                "identified_face": identified_face,
                "camera_index": self._camera_index(),
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "face_box": list(face_box),
                "source_project": str(self._project_path),
            },
        }


class VisionCapabilityController:
    """Capability controller that exposes face/emotion recognition through one adapter."""

    def __init__(
        self,
        *,
        capability_id: str,
        adapter: VisionAdapter | None = None,
        timeout_policy: CapabilityTimeoutPolicy | None = None,
    ) -> None:
        if capability_id not in VISION_CAPABILITIES:
            raise ValueError(f"Unsupported vision capability '{capability_id}'")

        self._capability_id = capability_id
        self._adapter = adapter or AssistiveVisionAdapter()
        self._timeout_policy = timeout_policy or CapabilityTimeoutPolicy(
            capability_id=capability_id,
            status_timeout_s=1.5,
            execute_timeout_s=6.0,
            hard_max_s=10.0,
        )
        self._last_status = "success"
        self._last_error_code: str | None = None

    def set_adapter(self, adapter: VisionAdapter) -> None:
        self._adapter = adapter
        self._last_status = "success"
        self._last_error_code = None

    def _localized(self, ar_text: str, en_text: str) -> str:
        return settings_manager.speak_localized(ar_text, en_text)

    def _unsupported_action(self, request: CapabilityRequest) -> CapabilityResult:
        self._last_status = "rejected"
        self._last_error_code = "invalid_action"
        return build_result(
            request=request,
            status="rejected",
            spoken_text=self._localized(
                "هذا الإجراء غير مدعوم لميزة الرؤية.",
                "This action is not supported for the vision capability.",
            ),
            payload={"capability_id": self._capability_id},
            error_code="invalid_action",
            used_fallback=False,
            backend_name=VISION_BACKEND_NAME,
        )

    def _availability_failure(self, *, request: CapabilityRequest, duration_ms: int = 0) -> CapabilityResult:
        health = self._adapter.describe_health()
        capability_health = dict(health.get("capabilities", {}).get(self._capability_id, {}))
        error_code = str(capability_health.get("error_code") or "capability_unavailable")
        self._last_status = "unavailable"
        self._last_error_code = error_code
        spoken_text = self._localized(
            "ميزة الرؤية المطلوبة غير متاحة حالياً.",
            "The requested vision capability is currently unavailable.",
        )
        return build_result(
            request=request,
            status="unavailable",
            spoken_text=spoken_text,
            payload={"capability_id": self._capability_id, "availability": "unavailable"},
            error_code=error_code,
            duration_ms=duration_ms,
            used_fallback=False,
            backend_name=VISION_BACKEND_NAME,
            metadata={"health": health},
        )

    def _timeout_failure(self, *, request: CapabilityRequest, duration_ms: int) -> CapabilityResult:
        self._last_status = "timeout"
        self._last_error_code = "capability_timeout"
        spoken_text = self._localized(
            "انتهت مهلة تنفيذ ميزة الرؤية. حاول مرة أخرى.",
            "The vision capability timed out. Please try again.",
        )
        return build_result(
            request=request,
            status="timeout",
            spoken_text=spoken_text,
            payload={"capability_id": self._capability_id},
            error_code="capability_timeout",
            duration_ms=duration_ms,
            used_fallback=False,
            backend_name=VISION_BACKEND_NAME,
        )

    def _exception_failure(self, *, request: CapabilityRequest, error: Exception, duration_ms: int) -> CapabilityResult:
        logger.error(
            "[VISION] Capability failed capability=%s error=%s",
            self._capability_id,
            error,
            exc_info=(type(error), error, error.__traceback__),
        )
        self._last_status = "failed"
        self._last_error_code = "capability_failure"
        spoken_text = self._localized(
            "حدث خطأ أثناء تشغيل ميزة الرؤية.",
            "An error occurred while running the vision capability.",
        )
        return build_result(
            request=request,
            status="failed",
            spoken_text=spoken_text,
            payload={"capability_id": self._capability_id},
            error_code="capability_failure",
            duration_ms=duration_ms,
            used_fallback=False,
            backend_name=VISION_BACKEND_NAME,
            metadata={"exception": str(error)},
        )

    def _response_to_result(
        self,
        *,
        request: CapabilityRequest,
        response: dict[str, Any],
        duration_ms: int,
    ) -> CapabilityResult:
        status = str(response.get("status", "failed"))
        payload = dict(response.get("payload") or {})
        payload.setdefault("capability_id", self._capability_id)
        spoken_text = str(
            response.get("spoken_text")
            or self._localized("تم تنفيذ الطلب.", "Request completed.")
        )
        error_code = response.get("error_code")
        self._last_status = status
        self._last_error_code = str(error_code) if error_code is not None else None
        return build_result(
            request=request,
            status=status,
            spoken_text=spoken_text,
            payload=payload,
            error_code=None if status == "success" else str(error_code or "capability_failure"),
            duration_ms=duration_ms,
            used_fallback=False,
            backend_name=VISION_BACKEND_NAME,
            metadata={"health": self._adapter.describe_health()},
        )

    def start(self, request: CapabilityRequest) -> CapabilityResult:
        return self._unsupported_action(request)

    def stop(self, request: CapabilityRequest) -> CapabilityResult:
        return self._unsupported_action(request)

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        if not self._adapter.is_available(self._capability_id):
            return self._availability_failure(request=request)

        if self._capability_id == "face_recognition":
            operation = lambda: self._adapter.recognize_face(  # noqa: E731
                store_new_face=bool(request.params.get("store_new_face", False))
            )
        else:
            operation = lambda: self._adapter.recognize_emotion(face_id=request.params.get("face_id"))

        invocation = invoke_with_timeout(operation, timeout_seconds=request.timeout_seconds)
        if invocation.timed_out:
            return self._timeout_failure(request=request, duration_ms=invocation.duration_ms)
        if invocation.exception is not None:
            return self._exception_failure(
                request=request,
                error=invocation.exception,
                duration_ms=invocation.duration_ms,
            )
        if not isinstance(invocation.result, dict):
            return self._exception_failure(
                request=request,
                error=RuntimeError("Vision adapter returned non-dict response"),
                duration_ms=invocation.duration_ms,
            )
        return self._response_to_result(
            request=request,
            response=invocation.result,
            duration_ms=invocation.duration_ms,
        )

    def get_status(self, request: CapabilityRequest) -> CapabilityStatusSnapshot:
        health = self._adapter.describe_health()
        capability_health = dict(health.get("capabilities", {}).get(self._capability_id, {}))
        available = bool(capability_health.get("available", False))
        availability = "ready" if available else "unavailable"
        spoken_summary = self._localized(
            "ميزة الرؤية المطلوبة جاهزة." if available else "ميزة الرؤية المطلوبة غير متاحة حالياً.",
            "The requested vision capability is ready."
            if available
            else "The requested vision capability is currently unavailable.",
        )
        return CapabilityStatusSnapshot(
            capability_id=self._capability_id,
            lifecycle_state="active" if available else "inactive",
            availability=availability,
            using_fallback=False,
            backend_name=VISION_BACKEND_NAME,
            last_result_status=self._last_status,
            last_error_code=self._last_error_code,
            spoken_summary=spoken_summary,
            details={"health": health},
        )


class AssistiveVisionProcessController:
    """Lifecycle controller that launches the full Assistive-Vision-System app."""

    def __init__(
        self,
        *,
        project_path: str | Path | None = None,
        timeout_policy: CapabilityTimeoutPolicy | None = None,
        popen_factory: Any | None = None,
    ) -> None:
        self._project_path = Path(
            os.environ.get(VISION_PROJECT_ENV) or project_path or DEFAULT_VISION_PROJECT_PATH
        ).resolve()
        self._main_script_path = self._project_path / "main.py"
        self._timeout_policy = timeout_policy or CapabilityTimeoutPolicy(
            capability_id="vision_system",
            start_timeout_s=4.0,
            stop_timeout_s=6.0,
            status_timeout_s=1.0,
            execute_timeout_s=4.0,
            hard_max_s=10.0,
        )
        self._popen_factory = popen_factory or subprocess.Popen
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | Any | None = None
        self._log_handle: Any | None = None
        self._log_path: Path | None = None
        self._stop_file_path: Path | None = None
        self._last_status = "success"
        self._last_error_code: str | None = None

    def _localized(self, ar_text: str, en_text: str) -> str:
        return settings_manager.speak_localized(ar_text, en_text)

    def _python_candidates(self) -> tuple[Path, ...]:
        candidates: list[Path] = []
        env_python = os.environ.get(VISION_PYTHON_ENV)
        if env_python:
            candidates.append(Path(env_python).resolve())
        candidates.append((self._project_path / ".venv" / "bin" / "python").resolve())
        candidates.append((self._project_path / ".venv" / "Scripts" / "python.exe").resolve())
        candidates.append(Path(sys.executable).resolve())

        unique: list[Path] = []
        for candidate in candidates:
            if candidate not in unique:
                unique.append(candidate)
        return tuple(unique)

    def _resolved_python(self) -> Path | None:
        for candidate in self._python_candidates():
            if candidate.exists():
                return candidate
        return None

    def _project_ready(self) -> tuple[bool, str | None]:
        if not self._project_path.exists():
            return False, "vision_project_missing"
        if not self._main_script_path.exists():
            return False, "vision_main_missing"
        if self._resolved_python() is None:
            return False, "vision_python_missing"
        return True, None

    def _vision_log_dir(self) -> Path:
        configured = os.environ.get(VISION_LOG_DIR_ENV)
        if configured:
            return Path(configured).resolve()
        return Path(__file__).resolve().parents[1] / "artifacts" / "vision_runtime"

    def _new_stop_file(self) -> Path:
        return Path(tempfile.gettempdir()) / f"assistive_vision_stop_{uuid4().hex}.flag"

    def _cleanup_finished_process(self) -> None:
        process = self._process
        if process is None or process.poll() is None:
            return
        if self._log_handle is not None:
            try:
                self._log_handle.close()
            except Exception:  # noqa: BLE001
                pass
        self._process = None
        self._log_handle = None
        self._log_path = None
        if self._stop_file_path is not None:
            try:
                self._stop_file_path.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass
        self._stop_file_path = None

    def _is_running(self) -> bool:
        self._cleanup_finished_process()
        return self._process is not None and self._process.poll() is None

    def _status_details(self) -> dict[str, Any]:
        self._cleanup_finished_process()
        return {
            "project_path": str(self._project_path),
            "main_script_path": str(self._main_script_path),
            "project_path_exists": self._project_path.exists(),
            "main_script_exists": self._main_script_path.exists(),
            "python_path": None if self._resolved_python() is None else str(self._resolved_python()),
            "running": self._is_running(),
            "pid": None if self._process is None else getattr(self._process, "pid", None),
            "log_path": None if self._log_path is None else str(self._log_path),
            "stop_file_path": None if self._stop_file_path is None else str(self._stop_file_path),
        }

    def _availability_failure(self, *, request: CapabilityRequest, error_code: str) -> CapabilityResult:
        self._last_status = "unavailable"
        self._last_error_code = error_code
        return build_result(
            request=request,
            status="unavailable",
            spoken_text=self._localized(
                "مشروع الرؤية غير متاح حالياً.",
                "The vision project is currently unavailable.",
            ),
            payload=self._status_details(),
            error_code=error_code,
            backend_name=VISION_PROCESS_BACKEND_NAME,
        )

    def _spawn_process(self) -> None:
        log_dir = self._vision_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"assistive_vision_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"
        stop_file = self._new_stop_file()
        env = build_external_process_env(extra={VISION_STOP_FILE_ENV: str(stop_file)})
        env.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
        python_path = self._resolved_python()
        if python_path is None:
            raise RuntimeError("vision_python_missing")

        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        log_handle = log_path.open("a", encoding="utf-8", errors="replace")
        argv = [str(python_path), "-u", str(self._main_script_path)]
        write_launch_diagnostics(
            log_handle,
            label="vision",
            cwd=self._project_path,
            argv=argv,
            env=env,
            paths={
                "project_path": self._project_path,
                "main_script_path": self._main_script_path,
                "python_path": python_path,
                "stop_file_path": stop_file,
            },
        )
        process = self._popen_factory(
            argv,
            cwd=str(self._project_path),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            env=env,
            creationflags=creationflags,
        )
        self._process = process
        self._log_handle = log_handle
        self._log_path = log_path
        self._stop_file_path = stop_file

    def start(self, request: CapabilityRequest) -> CapabilityResult:
        ready, error_code = self._project_ready()
        if not ready:
            return self._availability_failure(request=request, error_code=error_code or "vision_project_missing")

        with self._lock:
            if self._is_running():
                self._last_status = "success"
                self._last_error_code = None
                return build_result(
                    request=request,
                    status="success",
                    spoken_text=self._localized(
                        "مشروع الرؤية شغال بالفعل.",
                        "The vision project is already running.",
                    ),
                    payload=self._status_details(),
                    backend_name=VISION_PROCESS_BACKEND_NAME,
                )

            self._spawn_process()
            startup_deadline = time.time() + 5.0
            while time.time() < startup_deadline:
                if not self._is_running():
                    break
                time.sleep(0.2)
            if not self._is_running():
                self._last_status = "failed"
                self._last_error_code = "vision_process_exited_early"
                return build_result(
                    request=request,
                    status="failed",
                    spoken_text=self._localized(
                        "تعذر تشغيل مشروع الرؤية بشكل صحيح.",
                        "The vision project exited before it was ready.",
                    ),
                    payload=self._status_details(),
                    error_code="vision_process_exited_early",
                    backend_name=VISION_PROCESS_BACKEND_NAME,
                )

            self._last_status = "success"
            self._last_error_code = None
            return build_result(
                request=request,
                status="success",
                spoken_text=self._localized(
                    "تم تشغيل مشروع الرؤية.",
                    "The vision project is now running.",
                ),
                payload={**self._status_details(), "suspend_assistant_listening": True},
                backend_name=VISION_PROCESS_BACKEND_NAME,
            )

    def _request_graceful_stop(self) -> None:
        if self._stop_file_path is not None:
            self._stop_file_path.write_text("stop\n", encoding="utf-8")

    def _wait_for_exit(self, timeout_s: float) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if not self._is_running():
                return True
            time.sleep(0.2)
        return not self._is_running()

    def _force_stop(self) -> None:
        process = self._process
        if process is None or process.poll() is not None:
            return
        if platform.system().lower() == "windows" and hasattr(signal, "CTRL_BREAK_EVENT"):
            try:
                process.send_signal(signal.CTRL_BREAK_EVENT)
                if self._wait_for_exit(1.5):
                    return
            except Exception:  # noqa: BLE001
                pass
        try:
            process.terminate()
            if self._wait_for_exit(1.5):
                return
        except Exception:  # noqa: BLE001
            pass
        try:
            process.kill()
        except Exception:  # noqa: BLE001
            pass

    def stop(self, request: CapabilityRequest) -> CapabilityResult:
        with self._lock:
            if not self._is_running():
                self._last_status = "success"
                self._last_error_code = None
                return build_result(
                    request=request,
                    status="success",
                    spoken_text=self._localized(
                        "مشروع الرؤية متوقف بالفعل.",
                        "The vision project is already stopped.",
                    ),
                    payload=self._status_details(),
                    backend_name=VISION_PROCESS_BACKEND_NAME,
                )

            self._request_graceful_stop()
            if not self._wait_for_exit(4.0):
                self._force_stop()
                self._wait_for_exit(2.0)

            stopped = not self._is_running()
            self._last_status = "success" if stopped else "failed"
            self._last_error_code = None if stopped else "vision_process_stop_failed"
            return build_result(
                request=request,
                status="success" if stopped else "failed",
                spoken_text=self._localized(
                    "تم إيقاف مشروع الرؤية.",
                    "The vision project has been stopped.",
                )
                if stopped
                else self._localized(
                    "تعذر إيقاف مشروع الرؤية بشكل صحيح.",
                    "The vision project could not be stopped cleanly.",
                ),
                payload=self._status_details(),
                error_code=None if stopped else "vision_process_stop_failed",
                backend_name=VISION_PROCESS_BACKEND_NAME,
            )

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        return self.start(request)

    def get_status(self, request: CapabilityRequest) -> CapabilityStatusSnapshot:
        ready, error_code = self._project_ready()
        running = self._is_running()
        details = self._status_details()
        if error_code is not None:
            details["error_code"] = error_code
        return CapabilityStatusSnapshot(
            capability_id=request.capability_id,
            lifecycle_state="active" if running else "inactive",
            availability="ready" if ready else "unavailable",
            using_fallback=False,
            backend_name=VISION_PROCESS_BACKEND_NAME,
            last_result_status=self._last_status,
            last_error_code=self._last_error_code,
            spoken_summary=self._localized(
                "مشروع الرؤية شغال حالياً." if running else "مشروع الرؤية متوقف حالياً.",
                "The vision project is running." if running else "The vision project is stopped.",
            )
            if ready
            else self._localized(
                "مشروع الرؤية غير متاح حالياً.",
                "The vision project is currently unavailable.",
            ),
            details=details,
        )
