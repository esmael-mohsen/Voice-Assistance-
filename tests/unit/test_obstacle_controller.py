"""Unit tests for obstacle capability controller."""

from __future__ import annotations

from core.critical_prompts import contains_arabic_mojibake
from controllers.capability_contracts import CapabilityTimeoutPolicy, build_request
from controllers.obstacle_controller import ObstacleCapabilityController
from settings.settings_manager import settings_manager


def _policy() -> CapabilityTimeoutPolicy:
    return CapabilityTimeoutPolicy(
        capability_id="obstacle_detection",
        start_timeout_s=0.1,
        stop_timeout_s=0.1,
        status_timeout_s=0.1,
        execute_timeout_s=0.1,
        hard_max_s=10.0,
    )


def test_obstacle_start_and_stop_are_idempotent(obstacle_adapter_factory) -> None:
    adapter = obstacle_adapter_factory(available=True)
    controller = ObstacleCapabilityController(adapter=adapter, timeout_policy=_policy())

    start_request = build_request(capability_id="obstacle_detection", action="start", timeout_seconds=0.1)
    first_start = controller.start(start_request)
    second_start = controller.start(start_request)

    stop_request = build_request(capability_id="obstacle_detection", action="stop", timeout_seconds=0.1)
    first_stop = controller.stop(stop_request)
    second_stop = controller.stop(stop_request)

    assert first_start.status == "success"
    assert second_start.payload.get("idempotent") is True
    assert first_stop.status == "success"
    assert second_stop.payload.get("idempotent") is True


def test_obstacle_execute_returns_machine_readable_observation(obstacle_adapter_factory) -> None:
    adapter = obstacle_adapter_factory(
        available=True,
        observation={
            "detected": True,
            "distance_meters": 0.8,
            "angle_degrees": 15.0,
            "severity": "warning",
            "confidence": 0.95,
            "sensor_source": "fake_adapter",
        },
    )
    controller = ObstacleCapabilityController(adapter=adapter, timeout_policy=_policy())
    request = build_request(capability_id="obstacle_detection", action="execute", timeout_seconds=0.1)
    result = controller.execute(request)

    assert result.status == "success"
    assert result.payload["observation"]["detected"] is True
    assert result.payload["observation"]["severity"] == "warning"


def test_obstacle_unavailable_returns_safe_failure(obstacle_adapter_factory) -> None:
    adapter = obstacle_adapter_factory(available=False)
    controller = ObstacleCapabilityController(adapter=adapter, timeout_policy=_policy())
    request = build_request(capability_id="obstacle_detection", action="start", timeout_seconds=0.1)
    result = controller.start(request)

    assert result.status == "unavailable"
    assert result.error_code == "capability_unavailable"
    assert result.used_fallback is False


def test_obstacle_execute_timeout_is_bounded(obstacle_adapter_factory) -> None:
    adapter = obstacle_adapter_factory(available=True, read_delay_s=0.2)
    controller = ObstacleCapabilityController(adapter=adapter, timeout_policy=_policy())
    request = build_request(capability_id="obstacle_detection", action="execute", timeout_seconds=0.05)
    result = controller.execute(request)

    assert result.status == "timeout"
    assert result.error_code == "capability_timeout"
    assert result.duration_ms >= 50


def test_obstacle_status_snapshot_is_machine_readable(obstacle_adapter_factory) -> None:
    adapter = obstacle_adapter_factory(available=True)
    controller = ObstacleCapabilityController(adapter=adapter, timeout_policy=_policy())
    request = build_request(capability_id="obstacle_detection", action="status", timeout_seconds=0.1)
    snapshot = controller.get_status(request)

    assert snapshot.capability_id == "obstacle_detection"
    assert isinstance(snapshot.details, dict)
    assert "health" in snapshot.details


def test_obstacle_arabic_spoken_messages_are_readable(obstacle_adapter_factory) -> None:
    previous_language = settings_manager.language
    settings_manager.language = "ar-EG"
    try:
        adapter = obstacle_adapter_factory(
            available=True,
            observation={
                "detected": True,
                "severity": "warning",
                "distance_meters": 0.8,
                "sensor_source": "fake_adapter",
            },
        )
        controller = ObstacleCapabilityController(adapter=adapter, timeout_policy=_policy())
        request = build_request(capability_id="obstacle_detection", action="execute", timeout_seconds=0.1)

        result = controller.execute(request)

        assert "عائق" in result.spoken_text
        assert not contains_arabic_mojibake(result.spoken_text)
    finally:
        settings_manager.language = previous_language
