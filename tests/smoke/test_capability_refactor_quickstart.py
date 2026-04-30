"""Smoke checks aligned with capability-refactor quickstart scenarios."""

from __future__ import annotations

from controllers import capability_registry as cap_registry
from controllers.capability_contracts import CapabilityTimeoutPolicy
from core import resolver
from core.dispatcher import dispatch


def setup_function() -> None:
    resolver.reset_session_context()
    cap_registry.reset_default_registry()


def test_quickstart_validation_matrix_basics() -> None:
    scenarios = [
        ("start obstacle detection", "success"),
        ("stop obstacle detection", "success"),
        ("start ocr", "success"),
        ("start money detection", "success"),
        ("recognize face", "success"),
        ("recognize emotion", "success"),
        ("get status", "success"),
    ]
    for text, expected in scenarios:
        result = dispatch(text)
        assert result.status == expected


def test_migrated_obstacle_timeout_is_safe_and_bounded(obstacle_adapter_factory) -> None:
    registry = cap_registry.get_default_registry()
    registry._timeouts["obstacle_detection"] = CapabilityTimeoutPolicy(  # noqa: SLF001
        capability_id="obstacle_detection",
        start_timeout_s=0.05,
        stop_timeout_s=0.05,
        status_timeout_s=0.05,
        execute_timeout_s=0.05,
        hard_max_s=10.0,
    )
    cap_registry.set_obstacle_adapter(obstacle_adapter_factory(available=True, start_delay_s=0.2))

    result = dispatch("start obstacle detection")
    assert result.status == "failed"
    assert result.error_code == "capability_timeout"
    assert result.payload is not None
    assert result.payload.get("used_fallback") is False


def test_unmigrated_capabilities_keep_explicit_fallback_path() -> None:
    ocr = dispatch("start ocr")
    money = dispatch("start money detection")

    assert ocr.payload is not None and ocr.payload.get("used_fallback") is True
    assert money.payload is not None and money.payload.get("used_fallback") is True


def test_runtime_recovers_after_capability_failure(obstacle_adapter_factory) -> None:
    cap_registry.set_obstacle_adapter(obstacle_adapter_factory(available=True, fail_on_start=True))
    failed = dispatch("start obstacle detection")
    next_result = dispatch("switch to english")

    assert failed.status == "failed"
    assert next_result.status == "success"
