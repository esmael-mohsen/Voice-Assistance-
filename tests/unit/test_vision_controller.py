"""Unit tests for the real vision capability controller boundary."""

from __future__ import annotations

from pathlib import Path
import types

from controllers.capability_contracts import CapabilityTimeoutPolicy, build_request
from controllers.vision_controller import (
    AssistiveVisionAdapter,
    AssistiveVisionProcessController,
    VisionCapabilityController,
)


def _policy(capability_id: str) -> CapabilityTimeoutPolicy:
    return CapabilityTimeoutPolicy(
        capability_id=capability_id,
        start_timeout_s=0.1,
        stop_timeout_s=0.1,
        status_timeout_s=0.1,
        execute_timeout_s=0.1,
        hard_max_s=10.0,
    )


def test_face_execute_returns_real_payload_without_fallback(vision_adapter_factory) -> None:
    adapter = vision_adapter_factory(
        face_response={
            "status": "success",
            "spoken_text": "Face Ahmed recognized.",
            "payload": {
                "face_id": "Ahmed",
                "allow_emotion_follow_up": True,
                "identified": True,
            },
        }
    )
    controller = VisionCapabilityController(
        capability_id="face_recognition",
        adapter=adapter,
        timeout_policy=_policy("face_recognition"),
    )

    request = build_request(capability_id="face_recognition", action="execute", timeout_seconds=0.1)
    result = controller.execute(request)

    assert result.status == "success"
    assert result.used_fallback is False
    assert result.backend_name == "assistive_vision_system"
    assert result.payload["face_id"] == "Ahmed"
    assert result.payload["allow_emotion_follow_up"] is True


def test_face_execute_returns_unavailable_when_adapter_is_down(vision_adapter_factory) -> None:
    adapter = vision_adapter_factory(face_available=False)
    controller = VisionCapabilityController(
        capability_id="face_recognition",
        adapter=adapter,
        timeout_policy=_policy("face_recognition"),
    )

    request = build_request(capability_id="face_recognition", action="execute", timeout_seconds=0.1)
    result = controller.execute(request)

    assert result.status == "unavailable"
    assert result.error_code == "vision_unavailable"
    assert result.used_fallback is False


def test_emotion_execute_passes_follow_up_face_id_to_adapter(vision_adapter_factory) -> None:
    adapter = vision_adapter_factory(
        emotion_response={
            "status": "success",
            "spoken_text": "Detected a happy emotion for Face_007.",
            "payload": {
                "face_id": "Face_007",
                "emotion": "Happy",
            },
        }
    )
    controller = VisionCapabilityController(
        capability_id="emotion_recognition",
        adapter=adapter,
        timeout_policy=_policy("emotion_recognition"),
    )

    request = build_request(
        capability_id="emotion_recognition",
        action="execute",
        timeout_seconds=0.1,
        params={"face_id": "Face_007"},
    )
    result = controller.execute(request)

    assert result.status == "success"
    assert adapter.emotion_calls[-1]["face_id"] == "Face_007"
    assert result.payload["emotion"] == "Happy"


def test_vision_execute_timeout_is_bounded(vision_adapter_factory) -> None:
    adapter = vision_adapter_factory(face_delay_s=0.2)
    controller = VisionCapabilityController(
        capability_id="face_recognition",
        adapter=adapter,
        timeout_policy=_policy("face_recognition"),
    )

    request = build_request(capability_id="face_recognition", action="execute", timeout_seconds=0.05)
    result = controller.execute(request)

    assert result.status == "timeout"
    assert result.error_code == "capability_timeout"
    assert result.duration_ms >= 50


def test_vision_status_snapshot_reports_health(vision_adapter_factory) -> None:
    adapter = vision_adapter_factory(face_available=True, emotion_available=False)
    controller = VisionCapabilityController(
        capability_id="emotion_recognition",
        adapter=adapter,
        timeout_policy=_policy("emotion_recognition"),
    )

    request = build_request(capability_id="emotion_recognition", action="status", timeout_seconds=0.1)
    snapshot = controller.get_status(request)

    assert snapshot.capability_id == "emotion_recognition"
    assert snapshot.availability == "unavailable"
    assert snapshot.using_fallback is False
    assert "health" in snapshot.details


def test_assistive_vision_adapter_retries_camera_capture_after_transient_failure() -> None:
    class _FakeCapture:
        def __init__(self, *, opened: bool, frame):
            self._opened = opened
            self._frame = frame

        def isOpened(self) -> bool:
            return self._opened

        def set(self, *_args) -> bool:
            return True

        def read(self):
            return (self._frame is not None), self._frame

        def release(self) -> None:
            return None

    class _FakeCV2:
        CAP_DSHOW = 700
        CAP_PROP_FRAME_WIDTH = 3
        CAP_PROP_FRAME_HEIGHT = 4

        def __init__(self) -> None:
            self.calls = 0

        def VideoCapture(self, *_args):
            self.calls += 1
            if self.calls == 1:
                return _FakeCapture(opened=False, frame=None)
            return _FakeCapture(opened=True, frame="frame-ok")

    adapter = AssistiveVisionAdapter(camera_index=0, frame_warmup_reads=1)
    adapter._cv2 = _FakeCV2()
    adapter._vision_config = type("VisionConfig", (), {"FRAME_WIDTH": 640, "FRAME_HEIGHT": 480})()
    adapter._capture_attempts = 2
    adapter._capture_retry_delay_s = 0.0

    frame, error = adapter._capture_frame()

    assert error is None
    assert frame == "frame-ok"


def test_assistive_vision_adapter_falls_back_from_configured_camera_index(monkeypatch) -> None:
    monkeypatch.delenv("EGB_RUNTIME_TARGET", raising=False)

    class _FakeCapture:
        def __init__(self, *, opened: bool, frame):
            self._opened = opened
            self._frame = frame

        def isOpened(self) -> bool:
            return self._opened

        def set(self, *_args) -> bool:
            return True

        def read(self):
            return (self._frame is not None), self._frame

        def release(self) -> None:
            return None

    class _FakeCV2:
        CAP_DSHOW = 700
        CAP_PROP_FRAME_WIDTH = 3
        CAP_PROP_FRAME_HEIGHT = 4

        def __init__(self) -> None:
            self.indices: list[int] = []

        def VideoCapture(self, index, *_args):
            self.indices.append(index)
            if index == 1:
                return _FakeCapture(opened=False, frame=None)
            if index == 0:
                return _FakeCapture(opened=True, frame="frame-from-zero")
            return _FakeCapture(opened=False, frame=None)

    adapter = AssistiveVisionAdapter(frame_warmup_reads=1)
    adapter._cv2 = _FakeCV2()
    adapter._vision_config = type(
        "VisionConfig",
        (),
        {"FRAME_WIDTH": 640, "FRAME_HEIGHT": 480, "CAMERA_INDEX": 1},
    )()
    adapter._capture_attempts = 1
    adapter._capture_retry_delay_s = 0.0

    frame, error = adapter._capture_frame()

    assert error is None
    assert frame == "frame-from-zero"
    assert adapter._cv2.indices[:2] == [1, 1]
    assert 0 in adapter._cv2.indices


def test_assistive_vision_adapter_skips_dshow_when_raspberry_pi_target(monkeypatch) -> None:
    monkeypatch.setenv("EGB_RUNTIME_TARGET", "raspberry_pi")

    class _FakeCapture:
        def isOpened(self) -> bool:
            return True

        def set(self, *_args) -> bool:
            return True

        def read(self):
            return True, "frame-pi"

        def release(self) -> None:
            return None

    class _FakeCV2:
        CAP_DSHOW = 700
        CAP_PROP_FRAME_WIDTH = 3
        CAP_PROP_FRAME_HEIGHT = 4

        def __init__(self) -> None:
            self.calls: list[tuple[object, ...]] = []

        def VideoCapture(self, *args):
            self.calls.append(args)
            return _FakeCapture()

    adapter = AssistiveVisionAdapter(camera_index=0, frame_warmup_reads=1)
    adapter._cv2 = _FakeCV2()
    adapter._vision_config = type("VisionConfig", (), {"FRAME_WIDTH": 640, "FRAME_HEIGHT": 480})()
    adapter._capture_attempts = 1

    frame, error = adapter._capture_frame()

    assert error is None
    assert frame == "frame-pi"
    assert adapter._cv2.calls == [(0,)]


def test_vision_process_controller_prefers_env_python(monkeypatch, tmp_path: Path) -> None:
    project_dir = tmp_path / "vision-project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('vision app')\n", encoding="utf-8")
    env_python = tmp_path / "vision-python"
    env_python.write_text("", encoding="utf-8")
    monkeypatch.setenv("EGB_VISION_PYTHON", str(env_python))

    controller = AssistiveVisionProcessController(
        project_path=project_dir,
        timeout_policy=_policy("vision_system"),
    )

    assert controller._resolved_python() == env_python.resolve()


def test_assistive_vision_adapter_flags_missing_deepface_for_512d_database() -> None:
    class _Record:
        def __init__(self, embeddings):
            self.embeddings = embeddings

    class _FaceDB:
        def all(self):
            return {"Ismail": _Record([[0.0] * 512])}

    class _FaceProcessor:
        _df_ok = False

    adapter = AssistiveVisionAdapter()
    adapter._face_db = _FaceDB()
    adapter._face_processor = _FaceProcessor()

    error_code = adapter._validate_face_runtime()

    assert error_code == "vision_face_embedding_backend_missing"


def test_assistive_vision_adapter_bootstraps_emotion_before_face_runtime(monkeypatch) -> None:
    import controllers.vision_controller as vision_module

    adapter = AssistiveVisionAdapter(project_path="D:/fake-vision-project")

    events: list[str] = []

    class _FakeProjectPath:
        def __init__(self, label: str) -> None:
            self._label = label

        def exists(self) -> bool:
            return True

        def __truediv__(self, value: str):
            return _FakeProjectPath(f"{self._label}/{value}")

        def __str__(self) -> str:
            return self._label

    adapter._project_path = _FakeProjectPath("D:/fake-vision-project")

    class _FakeModelPath:
        def __init__(self, label: str) -> None:
            self._label = label

        def exists(self) -> bool:
            return self._label == "emotion_fixed.h5"

        def __str__(self) -> str:
            return self._label

    class _FakeVisionConfig:
        MODEL_PATH = _FakeModelPath("emotion_fixed.h5")
        FACE_DB_PATH = "face_data.pkl"
        CAMERA_INDEX = 1
        FRAME_WIDTH = 640
        FRAME_HEIGHT = 480

    class _FakeFaceProcessor:
        _df_ok = True

        def __init__(self) -> None:
            events.append("face_processor_init")

    class _FakeFaceDB:
        def __init__(self, *_, **__) -> None:
            events.append("face_db_init")

        def all(self):
            return {}

    class _FakeFaceEmotionDetector:
        def __init__(self, _model) -> None:
            events.append("emotion_detector_init")

    def _load_model(_path: str, compile: bool = False):  # noqa: A002
        assert compile is False
        events.append("load_model")
        return object()

    def _fake_import_module(name: str):
        if name == "cv2":
            return object()
        if name == "numpy":
            return object()
        if name == "config":
            return _FakeVisionConfig
        if name == "tensorflow.keras.models":
            return types.SimpleNamespace(load_model=_load_model)
        if name == "emotion.face_detector":
            return types.SimpleNamespace(FaceEmotionDetector=_FakeFaceEmotionDetector)
        if name == "face.face_processor":
            return types.SimpleNamespace(FaceProcessor=_FakeFaceProcessor)
        if name == "face.face_db":
            return types.SimpleNamespace(FaceDB=_FakeFaceDB)
        raise AssertionError(f"Unexpected import: {name}")

    monkeypatch.setattr(vision_module.importlib, "import_module", _fake_import_module)
    monkeypatch.setattr(vision_module, "Path", lambda value: _FakeModelPath(str(value)))

    adapter._bootstrap()

    assert events[:2] == ["load_model", "emotion_detector_init"]
    assert "face_processor_init" in events
    assert adapter._emotion_health_error is None


def test_vision_process_controller_starts_and_stops_subprocess(tmp_path: Path) -> None:
    project_dir = tmp_path / "vision-project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('vision app')\n", encoding="utf-8")

    class _FakeProcess:
        def __init__(self) -> None:
            self.pid = 4321
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

    controller = AssistiveVisionProcessController(
        project_path=project_dir,
        timeout_policy=_policy("vision_system"),
        popen_factory=_fake_popen,
    )

    start_request = build_request(capability_id="vision_system", action="start", timeout_seconds=0.1)
    start_result = controller.start(start_request)

    assert start_result.status == "success"
    assert start_result.payload["running"] is True
    assert launches

    stop_request = build_request(capability_id="vision_system", action="stop", timeout_seconds=0.1)
    stop_result = controller.stop(stop_request)

    assert stop_result.status == "success"
    assert stop_result.payload["running"] is False


def test_vision_process_controller_reports_already_running(tmp_path: Path) -> None:
    project_dir = tmp_path / "vision-project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('vision app')\n", encoding="utf-8")

    class _FakeProcess:
        pid = 99

        def poll(self):
            return None

    launches = 0

    def _fake_popen(*_args, **_kwargs):
        nonlocal launches
        launches += 1
        return _FakeProcess()

    controller = AssistiveVisionProcessController(
        project_path=project_dir,
        timeout_policy=_policy("vision_system"),
        popen_factory=_fake_popen,
    )

    request = build_request(capability_id="vision_system", action="start", timeout_seconds=0.1)
    first = controller.start(request)
    second = controller.start(request)

    assert first.status == "success"
    assert second.status == "success"
    assert launches == 1


def test_vision_process_controller_uses_configured_terminal_command(monkeypatch, tmp_path: Path) -> None:
    project_dir = tmp_path / "vision-project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('vision app')\n", encoding="utf-8")
    monkeypatch.setenv("EGB_VISION_COMMAND", "bash -lc 'source .venv/bin/activate && exec python -u main.py'")

    class _FakeProcess:
        pid = 97

        def poll(self):
            return None

    launches: list[dict[str, object]] = []

    def _fake_popen(args, **kwargs):
        launches.append({"args": args, **kwargs})
        return _FakeProcess()

    controller = AssistiveVisionProcessController(
        project_path=project_dir,
        timeout_policy=_policy("vision_system"),
        popen_factory=_fake_popen,
    )

    result = controller.start(build_request(capability_id="vision_system", action="start", timeout_seconds=0.1))

    assert result.status == "success"
    assert launches[0]["args"] == ["bash", "-lc", "source .venv/bin/activate && exec python -u main.py"]
    assert launches[0]["cwd"] == str(project_dir.resolve())


def test_vision_process_controller_opens_visible_terminal_when_enabled(monkeypatch, tmp_path: Path) -> None:
    project_dir = tmp_path / "vision-project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('vision app')\n", encoding="utf-8")
    monkeypatch.setenv("EGB_VISION_COMMAND", "bash -lc 'source .venv/bin/activate && exec python -u main.py'")
    monkeypatch.setenv("EGB_EXTERNAL_TERMINAL_ENABLED", "1")
    monkeypatch.setenv("EGB_EXTERNAL_TERMINAL_APP", "lxterminal")

    class _FakeProcess:
        pid = 102

        def poll(self):
            return None

    launches: list[dict[str, object]] = []

    def _fake_popen(args, **kwargs):
        launches.append({"args": args, **kwargs})
        return _FakeProcess()

    controller = AssistiveVisionProcessController(
        project_path=project_dir,
        timeout_policy=_policy("vision_system"),
        popen_factory=_fake_popen,
    )

    result = controller.start(build_request(capability_id="vision_system", action="start", timeout_seconds=0.1))

    assert result.status == "success"
    assert launches[0]["args"][:3] == ["lxterminal", f"--working-directory={project_dir.resolve()}", "--command"]
    assert "source .venv/bin/activate && exec python -u main.py" in launches[0]["args"][3]
    assert launches[0]["cwd"] == str(project_dir.resolve())
