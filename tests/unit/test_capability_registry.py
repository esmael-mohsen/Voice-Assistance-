"""Unit tests for capability registry bindings and fallback policy."""

from __future__ import annotations

from controllers import capability_registry as cap_registry
from controllers.capability_contracts import build_result


def setup_function() -> None:
    cap_registry.reset_default_registry()


def test_registry_binds_obstacle_start_intent_to_migrated_capability() -> None:
    registry = cap_registry.get_default_registry()
    descriptor = registry.descriptor_for_intent("enable_obstacle_detection")
    assert descriptor is not None
    assert descriptor.capability_id == "obstacle_detection"
    assert descriptor.migrated is True
    assert descriptor.backend_mode == "real"


def test_registry_executes_obstacle_via_real_path_without_fallback() -> None:
    result = cap_registry.execute_intent("enable_obstacle_detection")
    assert result.status == "success"
    assert result.used_fallback is False
    assert result.metadata["migrated"] is True


def test_registry_executes_unmigrated_ocr_via_explicit_fallback() -> None:
    result = cap_registry.execute_intent("enable_OCR")
    assert result.status == "success"
    assert result.used_fallback is True
    assert result.metadata["backend_mode"] == "fallback"


def test_registry_rejects_unknown_intent() -> None:
    result = cap_registry.execute_intent("unknown_intent")
    assert result.status == "rejected"
    assert result.error_code == "unsupported_capability_intent"


def test_registry_blocks_migrated_runtime_fallback_injection() -> None:
    registry = cap_registry.get_default_registry()

    class FallbackPretender:
        def start(self, request):
            return build_result(
                request=request,
                status="success",
                spoken_text="fallback used",
                payload={"using_fallback": True},
                used_fallback=True,
                backend_name="mock_fallback",
            )

        def stop(self, request):  # pragma: no cover - not used in this test
            return self.start(request)

        def execute(self, request):  # pragma: no cover - not used in this test
            return self.start(request)

        def get_status(self, request):  # pragma: no cover - not used in this test
            return None

    registry._handlers["obstacle_detection"] = FallbackPretender()  # noqa: SLF001
    result = registry.execute_intent("enable_obstacle_detection")

    assert result.status == "failed"
    assert result.error_code == "fallback_not_allowed"


def test_registry_returns_system_status_snapshot_for_fallback_capability() -> None:
    registry = cap_registry.get_default_registry()
    snapshot = registry.get_status_snapshot("system_status")
    assert snapshot.capability_id == "system_status"
    assert snapshot.using_fallback is True
    assert "using_fallback" in snapshot.details
