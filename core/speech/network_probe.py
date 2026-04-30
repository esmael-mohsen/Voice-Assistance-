"""Injectable TCP-based connectivity probe helpers."""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from typing import Callable, Sequence

from core.speech.provider_resolver import NetworkProbeResult, normalize_detected_status


@dataclass(frozen=True)
class ProbeTarget:
    host: str
    port: int
    timeout_s: float = 0.8
    label: str = "tcp_target"


def _default_targets() -> tuple[ProbeTarget, ...]:
    return (
        ProbeTarget(host="1.1.1.1", port=53, timeout_s=0.8, label="tcp_primary"),
        ProbeTarget(host="8.8.8.8", port=53, timeout_s=0.8, label="tcp_secondary"),
    )


def _default_dialer(host: str, port: int, timeout_s: float) -> None:
    with socket.create_connection((host, port), timeout=timeout_s):
        return None


class TCPNetworkProbe:
    """Minimal TCP probe that can be injected in tests with fake dialers/clocks."""

    def __init__(
        self,
        *,
        targets: Sequence[ProbeTarget] | None = None,
        dialer: Callable[[str, int, float], None] | None = None,
        monotonic: Callable[[], float] | None = None,
        now_fn: Callable[[], float] | None = None,
    ) -> None:
        self._targets = tuple(targets or _default_targets())
        self._dialer = dialer or _default_dialer
        self._monotonic = monotonic or time.perf_counter
        self._now_fn = now_fn or time.time

    def probe(self, *, source: str = "background") -> NetworkProbeResult:
        started_at = self._monotonic()
        uncertain_reason: str | None = None
        uncertain_label: str | None = None
        offline_reason: str | None = None
        offline_label: str | None = None

        for target in self._targets:
            try:
                self._dialer(target.host, int(target.port), float(target.timeout_s))
            except TimeoutError:
                uncertain_reason = "timeout"
                uncertain_label = target.label
                continue
            except socket.timeout:
                uncertain_reason = "timeout"
                uncertain_label = target.label
                continue
            except OSError as exc:  # e.g. network unreachable / refused / DNS
                offline_reason = type(exc).__name__.lower() or "connection_error"
                offline_label = target.label
                continue

            latency_ms = int((self._monotonic() - started_at) * 1000)
            return NetworkProbeResult(
                source=str(source or "background"),
                target_label=target.label,
                status="online",
                latency_ms=max(0, latency_ms),
                checked_at=float(self._now_fn()),
                failure_reason=None,
            )

        latency_ms = int((self._monotonic() - started_at) * 1000)
        if uncertain_reason is not None:
            return NetworkProbeResult(
                source=str(source or "background"),
                target_label=uncertain_label or "tcp_primary",
                status=normalize_detected_status("uncertain"),
                latency_ms=max(0, latency_ms),
                checked_at=float(self._now_fn()),
                failure_reason=uncertain_reason,
            )

        return NetworkProbeResult(
            source=str(source or "background"),
            target_label=offline_label or "tcp_primary",
            status=normalize_detected_status("offline"),
            latency_ms=max(0, latency_ms),
            checked_at=float(self._now_fn()),
            failure_reason=offline_reason or "connection_error",
        )
