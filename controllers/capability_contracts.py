"""Shared capability contracts and timeout helpers for controller refactor."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
import threading
import time
from typing import Any, Callable, Protocol
from uuid import uuid4

logger = logging.getLogger(__name__)

VALID_ACTIONS = frozenset({"start", "stop", "execute", "status"})
SUCCESS_STATUSES = frozenset({"success"})
FAILURE_STATUSES = frozenset({"unavailable", "timeout", "failed", "rejected"})
VALID_STATUSES = SUCCESS_STATUSES | FAILURE_STATUSES


@dataclass(frozen=True)
class CapabilityTimeoutPolicy:
    capability_id: str
    start_timeout_s: float = 3.0
    stop_timeout_s: float = 3.0
    status_timeout_s: float = 3.0
    execute_timeout_s: float = 3.0
    hard_max_s: float = 10.0

    def __post_init__(self) -> None:
        if self.hard_max_s <= 0:
            raise ValueError("hard_max_s must be positive")
        if self.hard_max_s > 10.0:
            raise ValueError("hard_max_s must not exceed 10 seconds")
        for timeout_value in (
            self.start_timeout_s,
            self.stop_timeout_s,
            self.status_timeout_s,
            self.execute_timeout_s,
        ):
            if timeout_value <= 0:
                raise ValueError("timeout values must be positive")
            if timeout_value > self.hard_max_s:
                raise ValueError("timeout values must be <= hard_max_s")

    def timeout_for(self, action: str) -> float:
        if action == "start":
            return self.start_timeout_s
        if action == "stop":
            return self.stop_timeout_s
        if action == "status":
            return self.status_timeout_s
        if action == "execute":
            return self.execute_timeout_s
        raise ValueError(f"Unsupported action '{action}'")


@dataclass(frozen=True)
class CapabilityDescriptor:
    capability_id: str
    display_name: str
    migrated: bool
    backend_mode: str
    supported_actions: frozenset[str]
    fallback_policy: str
    requires_network: bool = False
    dependency_name: str = "unknown"
    timeout_policy_id: str | None = None

    def __post_init__(self) -> None:
        if not self.capability_id:
            raise ValueError("capability_id is required")
        if self.backend_mode not in {"real", "fallback", "test_double"}:
            raise ValueError("backend_mode must be one of: real, fallback, test_double")
        if self.fallback_policy not in {"disabled", "unmigrated_only", "test_only"}:
            raise ValueError("fallback_policy must be one of: disabled, unmigrated_only, test_only")
        if not self.supported_actions:
            raise ValueError("supported_actions cannot be empty")
        unsupported = set(self.supported_actions) - VALID_ACTIONS
        if unsupported:
            raise ValueError(f"unsupported actions: {sorted(unsupported)}")

    def supports(self, action: str) -> bool:
        return action in self.supported_actions


@dataclass(frozen=True)
class CapabilityRequest:
    request_id: str
    capability_id: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    source_mode: str = "runtime"
    issued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    timeout_seconds: float = 3.0
    correlation_id: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self) -> None:
        if self.action not in VALID_ACTIONS:
            raise ValueError(f"Unsupported action '{self.action}'")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not isinstance(self.params, dict):
            raise TypeError("params must be a dictionary")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityResult:
    request_id: str
    capability_id: str
    action: str
    status: str
    spoken_text: str
    payload: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    duration_ms: int = 0
    used_fallback: bool = False
    backend_name: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Unsupported status '{self.status}'")
        if not self.spoken_text:
            raise ValueError("spoken_text is required")
        if self.status in FAILURE_STATUSES and not self.error_code:
            raise ValueError("error_code is required for failure statuses")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityStatusSnapshot:
    capability_id: str
    lifecycle_state: str
    availability: str
    using_fallback: bool
    backend_name: str
    last_result_status: str
    last_error_code: str | None = None
    spoken_summary: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TimedInvocation:
    finished: bool
    timed_out: bool
    duration_ms: int
    result: Any = None
    exception: Exception | None = None


class CapabilityHandler(Protocol):
    def start(self, request: CapabilityRequest) -> CapabilityResult: ...
    def stop(self, request: CapabilityRequest) -> CapabilityResult: ...
    def execute(self, request: CapabilityRequest) -> CapabilityResult: ...
    def get_status(self, request: CapabilityRequest) -> CapabilityStatusSnapshot: ...


def build_request(
    *,
    capability_id: str,
    action: str,
    timeout_seconds: float,
    params: dict[str, Any] | None = None,
    source_mode: str = "runtime",
    correlation_id: str | None = None,
) -> CapabilityRequest:
    return CapabilityRequest(
        request_id=uuid4().hex,
        capability_id=capability_id,
        action=action,
        params=dict(params or {}),
        source_mode=source_mode,
        timeout_seconds=timeout_seconds,
        correlation_id=correlation_id or uuid4().hex,
    )


def invoke_with_timeout(operation: Callable[[], Any], *, timeout_seconds: float) -> TimedInvocation:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    started_at = time.perf_counter()
    state: dict[str, Any] = {"result": None, "exception": None}
    done = threading.Event()

    def _runner() -> None:
        try:
            state["result"] = operation()
        except Exception as exc:  # noqa: BLE001
            state["exception"] = exc
        finally:
            done.set()

    worker = threading.Thread(target=_runner, name="CapabilityInvocation", daemon=True)
    worker.start()
    finished = done.wait(timeout_seconds)
    duration_ms = int((time.perf_counter() - started_at) * 1000)

    if not finished:
        logger.warning("[CAPABILITY] Invocation timed out after %.2fs", timeout_seconds)
        return TimedInvocation(finished=False, timed_out=True, duration_ms=duration_ms)

    if state["exception"] is not None:
        return TimedInvocation(
            finished=True,
            timed_out=False,
            duration_ms=duration_ms,
            exception=state["exception"],
        )

    return TimedInvocation(
        finished=True,
        timed_out=False,
        duration_ms=duration_ms,
        result=state["result"],
    )


def build_result(
    *,
    request: CapabilityRequest,
    status: str,
    spoken_text: str,
    payload: dict[str, Any] | None = None,
    error_code: str | None = None,
    duration_ms: int = 0,
    used_fallback: bool = False,
    backend_name: str = "unknown",
    metadata: dict[str, Any] | None = None,
) -> CapabilityResult:
    return CapabilityResult(
        request_id=request.request_id,
        capability_id=request.capability_id,
        action=request.action,
        status=status,
        spoken_text=spoken_text,
        payload=dict(payload or {}),
        error_code=error_code,
        duration_ms=duration_ms,
        used_fallback=used_fallback,
        backend_name=backend_name,
        metadata=dict(metadata or {}),
    )

