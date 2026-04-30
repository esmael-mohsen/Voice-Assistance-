"""Unit tests for wearable priority routing, coalescing, and feedback cues."""

from __future__ import annotations

from core.assistant_runtime import map_non_speech_cue, truncate_to_word_limit
from core.command_models import InteractionPriorityEvent, coalesce_priority_events


def _event(
    *,
    event_id: str,
    priority: str,
    key: str,
    created_at_s: float,
    text: str = "status updated",
) -> InteractionPriorityEvent:
    return InteractionPriorityEvent(
        event_id=event_id,
        priority=priority,
        message_text=text,
        message_key=key,
        created_at_s=created_at_s,
        source="runtime",
        coalescing_group=key,
    )


def test_priority_ordering_prefers_warning_then_action_confirmation_then_info() -> None:
    events = [
        _event(event_id="1", priority="info", key="info_1", created_at_s=1.0),
        _event(event_id="2", priority="warning", key="warn_1", created_at_s=2.0),
        _event(event_id="3", priority="action_confirmation", key="confirm_1", created_at_s=3.0),
    ]
    ordered = coalesce_priority_events(events, coalescing_window_s=2.0)
    assert [event.priority for event in ordered] == ["warning", "action_confirmation", "info"]


def test_same_priority_duplicates_coalesce_within_two_seconds() -> None:
    events = [
        _event(event_id="1", priority="info", key="dup", created_at_s=1.0, text="duplicate"),
        _event(event_id="2", priority="info", key="dup", created_at_s=2.2, text="duplicate"),
        _event(event_id="3", priority="info", key="other", created_at_s=2.5, text="other"),
    ]
    coalesced = coalesce_priority_events(events, coalescing_window_s=2.0)
    assert len(coalesced) == 2
    assert coalesced[0].message_key == "dup"
    assert coalesced[1].message_key == "other"


def test_concise_response_limit_defaults_to_twelve_words() -> None:
    text = "this response should be shortened for wearable mode and stay concise by default"
    concise = truncate_to_word_limit(text, word_limit=12)
    assert len(concise.split()) <= 12


def test_non_speech_cue_mapping_includes_ready_standby_and_error() -> None:
    assert map_non_speech_cue("ready") == "tone_ready"
    assert map_non_speech_cue("standby") == "haptic_standby"
    assert map_non_speech_cue("error") == "tone_error"


def test_critical_prompt_catalog_replaces_corrupted_prompt_text(isolated_settings_manager) -> None:
    isolated_settings_manager._critical_prompt_catalog["offline_guidance"]["ar"] = ""
    isolated_settings_manager._repaired_prompt_keys = set()

    resolved = isolated_settings_manager.resolve_critical_surface("runtime.offline.safe_refusal")

    assert resolved["integrity_status"] == "fallback_used"
    assert resolved["fallback_used"] is True
