"""Unit tests for connectivity-state transitions and probe behavior."""

from __future__ import annotations

import socket

from core.speech.network_probe import ProbeTarget, TCPNetworkProbe
from core.speech.provider_resolver import build_connectivity_state


def test_connectivity_state_uses_last_known_online_during_grace_window() -> None:
    state = build_connectivity_state(
        override_mode="auto",
        detected_status="uncertain",
        last_confirmed_status="online",
        grace_window_deadline_at=12.0,
        now_s=11.0,
    )
    assert state.grace_window_active is True
    assert state.effective_network_available is True


def test_connectivity_state_converges_offline_after_grace_window() -> None:
    state = build_connectivity_state(
        override_mode="auto",
        detected_status="uncertain",
        last_confirmed_status="online",
        grace_window_deadline_at=12.0,
        now_s=12.5,
    )
    assert state.grace_window_active is False
    assert state.effective_network_available is False


def test_settings_manager_applies_override_modes(isolated_settings_manager) -> None:
    isolated_settings_manager.set_network_available(True)
    isolated_settings_manager.set_network_override_mode("force_offline")
    assert isolated_settings_manager.get_connectivity_state_snapshot()["effective_network_available"] is False

    isolated_settings_manager.set_network_override_mode("force_online")
    assert isolated_settings_manager.get_connectivity_state_snapshot()["effective_network_available"] is True


def test_settings_manager_tracks_uncertain_probe_with_bounded_grace(isolated_settings_manager) -> None:
    isolated_settings_manager.set_network_available(True)
    isolated_settings_manager.apply_network_probe_result(
        {"status": "uncertain", "checked_at": 10.0},
        grace_window_s=2.0,
    )

    in_grace = isolated_settings_manager.get_connectivity_state_snapshot(now_s=11.0)
    assert in_grace["detected_status"] == "uncertain"
    assert in_grace["grace_window_active"] is True
    assert in_grace["effective_network_available"] is True

    after_grace = isolated_settings_manager.get_connectivity_state_snapshot(now_s=13.0)
    assert after_grace["grace_window_active"] is False
    assert after_grace["effective_network_available"] is False


def test_probe_flapping_sequence_remains_deterministic(isolated_settings_manager) -> None:
    isolated_settings_manager.set_network_available(True)
    isolated_settings_manager.apply_network_probe_result(
        {"status": "uncertain", "checked_at": 20.0},
        grace_window_s=1.0,
    )
    assert isolated_settings_manager.get_connectivity_state_snapshot(now_s=20.5)["effective_network_available"] is True

    isolated_settings_manager.apply_network_probe_result(
        {"status": "offline", "checked_at": 21.1},
        grace_window_s=1.0,
    )
    assert isolated_settings_manager.get_connectivity_state_snapshot(now_s=21.1)["effective_network_available"] is False

    isolated_settings_manager.apply_network_probe_result(
        {"status": "uncertain", "checked_at": 22.0},
        grace_window_s=1.0,
    )
    assert isolated_settings_manager.get_connectivity_state_snapshot(now_s=22.5)["effective_network_available"] is False

    isolated_settings_manager.apply_network_probe_result(
        {"status": "online", "checked_at": 23.0},
        grace_window_s=1.0,
    )
    assert isolated_settings_manager.get_connectivity_state_snapshot(now_s=23.0)["effective_network_available"] is True


def test_tcp_probe_reports_online_with_successful_dial() -> None:
    probe = TCPNetworkProbe(
        targets=[ProbeTarget(host="127.0.0.1", port=53, label="local")],
        dialer=lambda _host, _port, _timeout: None,
        monotonic=lambda: 1.0,
        now_fn=lambda: 100.0,
    )
    result = probe.probe(source="manual")
    assert result.status == "online"
    assert result.failure_reason is None
    assert result.target_label == "local"


def test_tcp_probe_reports_uncertain_on_timeout() -> None:
    probe = TCPNetworkProbe(
        targets=[ProbeTarget(host="127.0.0.1", port=53, label="local")],
        dialer=lambda _host, _port, _timeout: (_ for _ in ()).throw(socket.timeout()),
        monotonic=lambda: 1.0,
        now_fn=lambda: 100.0,
    )
    result = probe.probe(source="manual")
    assert result.status == "uncertain"
    assert result.failure_reason == "timeout"


def test_tcp_probe_reports_offline_on_os_error() -> None:
    probe = TCPNetworkProbe(
        targets=[ProbeTarget(host="127.0.0.1", port=53, label="local")],
        dialer=lambda _host, _port, _timeout: (_ for _ in ()).throw(OSError("unreachable")),
        monotonic=lambda: 1.0,
        now_fn=lambda: 100.0,
    )
    result = probe.probe(source="manual")
    assert result.status == "offline"
    assert result.failure_reason is not None
