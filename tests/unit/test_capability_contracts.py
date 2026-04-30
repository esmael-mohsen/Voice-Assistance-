"""Unit tests for capability contracts and timeout helpers."""

from __future__ import annotations

import time

import pytest

from controllers.capability_contracts import (
    CapabilityDescriptor,
    CapabilityTimeoutPolicy,
    build_request,
    build_result,
    invoke_with_timeout,
)


def test_timeout_policy_rejects_hard_max_above_limit() -> None:
    with pytest.raises(ValueError):
        CapabilityTimeoutPolicy(capability_id="x", hard_max_s=10.1)


def test_timeout_policy_returns_action_specific_values() -> None:
    policy = CapabilityTimeoutPolicy(
        capability_id="obstacle_detection",
        start_timeout_s=2.5,
        stop_timeout_s=2.0,
        status_timeout_s=1.5,
        execute_timeout_s=3.0,
        hard_max_s=10.0,
    )
    assert policy.timeout_for("start") == 2.5
    assert policy.timeout_for("status") == 1.5


def test_descriptor_validates_supported_actions() -> None:
    with pytest.raises(ValueError):
        CapabilityDescriptor(
            capability_id="ocr",
            display_name="OCR",
            migrated=False,
            backend_mode="fallback",
            supported_actions=frozenset({"launch"}),
            fallback_policy="unmigrated_only",
        )


def test_build_result_requires_error_code_for_failure_status() -> None:
    request = build_request(capability_id="obstacle_detection", action="start", timeout_seconds=2.0)
    with pytest.raises(ValueError):
        build_result(
            request=request,
            status="failed",
            spoken_text="failed",
            payload={},
            error_code=None,
        )


def test_invoke_with_timeout_marks_slow_call_as_timeout() -> None:
    invocation = invoke_with_timeout(lambda: time.sleep(0.15), timeout_seconds=0.05)
    assert invocation.timed_out is True
    assert invocation.finished is False
    assert invocation.duration_ms >= 50
