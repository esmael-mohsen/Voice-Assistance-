"""Unit tests for provider persistence and deferred switching settings."""

from __future__ import annotations


def test_settings_snapshot_includes_provider_fields(isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "speech_provider": "legacy",
            "pending_speech_provider": None,
            "deferred_provider_switch": False,
        },
        persist=False,
    )
    snapshot = isolated_settings_manager.get_settings_snapshot()
    assert snapshot["speech_provider"] == "legacy"
    assert snapshot["pending_speech_provider"] is None
    assert snapshot["deferred_provider_switch"] is False


def test_provider_switch_is_deferred_during_active_runtime(isolated_settings_manager) -> None:
    state = isolated_settings_manager.request_speech_provider("speakkit", runtime_active=True)
    assert state["speech_provider"] == "legacy"
    assert state["pending_speech_provider"] == "speakkit"
    assert state["deferred_provider_switch"] is True


def test_deferred_provider_is_applied_on_restart(isolated_settings_manager) -> None:
    isolated_settings_manager.request_speech_provider("speakkit", runtime_active=True)
    applied = isolated_settings_manager.consume_deferred_speech_provider()

    assert applied == "speakkit"
    snapshot = isolated_settings_manager.get_settings_snapshot()
    assert snapshot["speech_provider"] == "speakkit"
    assert snapshot["pending_speech_provider"] is None
    assert snapshot["deferred_provider_switch"] is False


def test_wearable_runtime_bounds_and_policies_persist_in_snapshot(isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "max_listen_seconds": 6.0,
            "max_speak_seconds": 5.0,
            "priority_coalescing_window_s": 2.0,
            "concise_word_limit": 10,
            "command_confidence_high_threshold": 0.9,
            "command_confidence_medium_threshold": 0.7,
            "command_protected_threshold": 0.95,
            "command_max_retry_cycles": 1,
            "command_fallback_enabled": True,
            "command_offline_local_allowed": True,
            "network_available": False,
            "network_override_mode": "force_offline",
            "connectivity_detected_status": "offline",
            "offline_allowlisted_capabilities": ["system_status", "obstacle_detection"],
            "wake_primary_mode": "keyword_low_power",
            "wake_fallback_mode": "hardware_trigger",
            "wake_dev_fallback_mode": "stt_based_wake",
            "stt_wake_allowed_in_production": False,
            "non_speech_cues_enabled": True,
        },
        persist=False,
    )
    snapshot = isolated_settings_manager.get_settings_snapshot()
    assert snapshot["max_listen_seconds"] == 6.0
    assert snapshot["max_speak_seconds"] == 5.0
    assert snapshot["priority_coalescing_window_s"] == 2.0
    assert snapshot["concise_word_limit"] == 10
    assert snapshot["command_confidence_high_threshold"] == 0.9
    assert snapshot["command_confidence_medium_threshold"] == 0.7
    assert snapshot["command_protected_threshold"] == 0.95
    assert snapshot["command_max_retry_cycles"] == 1
    assert snapshot["command_fallback_enabled"] is True
    assert snapshot["command_offline_local_allowed"] is True
    assert snapshot["network_available"] is False
    assert snapshot["network_override_mode"] == "force_offline"
    assert snapshot["connectivity_detected_status"] == "offline"
    assert set(snapshot["offline_allowlisted_capabilities"]) == {"system_status", "obstacle_detection"}
    assert snapshot["wake_primary_mode"] == "keyword_low_power"
    assert snapshot["wake_fallback_mode"] == "hardware_trigger"
    assert snapshot["wake_dev_fallback_mode"] == "stt_based_wake"
    assert snapshot["stt_wake_allowed_in_production"] is False


def test_release_threshold_policy_is_available_in_snapshot(isolated_settings_manager) -> None:
    snapshot = isolated_settings_manager.get_settings_snapshot()
    policy = snapshot["release_threshold_policy"]
    assert "wake_to_listen" in policy
    assert snapshot["release_artifact_retention_days"] == 180


def test_startup_reset_forces_network_override_to_auto(isolated_settings_manager) -> None:
    isolated_settings_manager.set_network_override_mode("force_online")
    snapshot = isolated_settings_manager.reset_network_override_for_startup()

    assert snapshot["override_mode"] == "auto"
    assert snapshot["startup_reset_applied"] is True
