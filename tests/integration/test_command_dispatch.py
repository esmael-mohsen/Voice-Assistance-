"""Integration tests for structured command dispatch contract."""

from core.dispatcher import dispatch
from core import resolver


def setup_function() -> None:
    resolver.reset_session_context()


def test_dispatch_returns_structured_success_for_everyday_command() -> None:
    result = dispatch("start obstacle detection")
    assert result.status == "success"
    assert result.intent_id == "enable_obstacle_detection"
    assert isinstance(result.spoken_text, str)
    assert result.spoken_text


def test_dispatch_returns_rejected_for_unknown_input() -> None:
    result = dispatch("open the pod bay doors")
    assert result.status == "rejected"
    assert result.error_code in {"below_threshold", "ambiguous", "unrecognized_command"}
    assert isinstance(result.spoken_text, str)


def test_dispatch_protected_command_confirmation_flow() -> None:
    first = dispatch("stop system")
    assert first.status == "confirmation_required"
    assert first.intent_id == "stop_system"

    second = dispatch("yes please")
    assert second.status == "success"
    assert second.intent_id == "stop_system"


def test_dispatch_confirmation_mixed_yes_cancel_stays_safe() -> None:
    first = dispatch("reset settings")
    assert first.status == "confirmation_required"
    second = dispatch("yes cancel")
    assert second.status == "rejected"
    assert second.error_code == "confirmation_declined"
    assert second.metadata.get("dialog_safe_precedence_applied") is True


def test_dispatch_clarification_flow_fails_after_two_retries() -> None:
    first = dispatch("set language")
    assert first.status == "clarification_required"

    second = dispatch("set language")
    assert second.status == "clarification_required"

    third = dispatch("set language")
    assert third.status == "failed"
    assert third.error_code == "clarification_failed"


def test_dispatch_clarification_resolves_from_option_response() -> None:
    first = dispatch("set voice gender")
    assert first.status == "clarification_required"

    second = dispatch("female")
    assert second.status == "success"
    assert second.payload is not None
    assert second.payload["params"]["gender"] == "female"


def test_dispatch_follow_up_context_consumes_once() -> None:
    face = dispatch("recognize face")
    assert face.status == "success"

    emotion = dispatch("recognize emotion")
    assert emotion.status == "success"
    assert emotion.metadata.get("used_session_context") is True

    context_after = resolver.get_session_context()
    assert context_after.remaining_follow_ups == 0


def test_dispatch_clears_stale_follow_up_when_clarification_starts() -> None:
    face = dispatch("recognize face")
    assert face.status == "success"
    assert resolver.get_session_context().remaining_follow_ups == 1

    clarification = dispatch("set language")
    assert clarification.status == "clarification_required"
    assert resolver.get_session_context().remaining_follow_ups == 0


def test_dispatch_accepts_canonical_text_and_recognition_metadata() -> None:
    result = dispatch(
        "reed txt",
        canonical_command_text="read text",
        recognition_metadata={
            "recognition_path": "local_first",
            "confidence_available": False,
            "confidence_score": None,
        },
    )
    assert result.metadata["canonical_command_text"] == "read text"
    assert result.metadata["recognition"]["recognition_path"] == "local_first"


def test_dispatch_preserves_closed_vocabulary_metadata() -> None:
    result = dispatch(
        "yes",
        canonical_command_text="yes",
        recognition_metadata={
            "recognition_path": "rescue",
            "closed_vocabulary_id": "confirmation.yes_no",
            "dictionary_bias_applied": True,
        },
    )
    assert result.metadata["recognition"]["recognition_path"] == "rescue"
    assert result.metadata["recognition"]["closed_vocabulary_id"] == "confirmation.yes_no"
