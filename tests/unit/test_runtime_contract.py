"""Unit tests for runtime lifecycle contract vocabulary and transitions."""

from core.assistant_runtime import (
    CANONICAL_RUNTIME_STATES,
    RuntimeMode,
    RuntimeSession,
    RuntimeState,
    canonical_runtime_state,
    error_event,
    status_event,
)
from core.command_models import (
    GuidedDialogOutcome,
    InteractionPriorityEvent,
    NameCandidate,
    PilotVoiceUXEvaluationRun,
    RuntimeRecoveryOutcome,
    SpeechLoopRecoveryResult,
    StandbyWakeOutcome,
    TurnTakingWindowOutcome,
    WakeReliabilityOutcome,
    WakePolicySelection,
)


def test_canonical_lifecycle_vocabulary_is_stable() -> None:
    expected = {
        RuntimeState.STANDBY,
        RuntimeState.WAKE,
        RuntimeState.SETUP,
        RuntimeState.LISTENING,
        RuntimeState.THINKING,
        RuntimeState.SPEAKING,
        RuntimeState.ERROR,
        RuntimeState.OFFLINE,
    }
    assert CANONICAL_RUNTIME_STATES == expected


def test_runtime_transition_rules_cover_expected_paths() -> None:
    session = RuntimeSession(mode=RuntimeMode.GUI)
    assert session.can_transition_to(RuntimeState.STANDBY)
    session.transition_to(RuntimeState.STANDBY)
    assert session.can_transition_to(RuntimeState.WAKE)
    assert session.can_transition_to(RuntimeState.OFFLINE)
    assert session.can_transition_to(RuntimeState.THINKING) is False

    session.transition_to(RuntimeState.WAKE)
    assert session.can_transition_to(RuntimeState.SETUP)
    assert session.can_transition_to(RuntimeState.LISTENING)
    assert session.can_transition_to(RuntimeState.SPEAKING) is False


def test_status_event_canonicalizes_compatibility_states() -> None:
    session = RuntimeSession(mode=RuntimeMode.CONSOLE)
    online_event = status_event(session, RuntimeState.ONLINE)
    stopping_event = status_event(session, RuntimeState.STOPPING)

    assert online_event.payload["state"] == RuntimeState.LISTENING.value
    assert online_event.payload["raw_state"] == RuntimeState.ONLINE.value
    assert stopping_event.payload["state"] == RuntimeState.OFFLINE.value
    assert stopping_event.payload["raw_state"] == RuntimeState.STOPPING.value
    assert canonical_runtime_state("online") == RuntimeState.LISTENING
    assert canonical_runtime_state("stopping") == RuntimeState.OFFLINE


def test_error_event_payload_marks_recoverable_vs_unrecoverable() -> None:
    session = RuntimeSession(mode=RuntimeMode.GUI)
    recoverable = error_event(
        session,
        message="temporary issue",
        recoverable=True,
        next_state=RuntimeState.STANDBY,
    )
    unrecoverable = error_event(
        session,
        message="fatal issue",
        recoverable=False,
        next_state=RuntimeState.OFFLINE,
    )

    assert recoverable.payload == {
        "message": "temporary issue",
        "recoverable": True,
        "next_state": "standby",
    }
    assert unrecoverable.payload == {
        "message": "fatal issue",
        "recoverable": False,
        "next_state": "offline",
    }


def test_wearable_priority_event_contract_requires_supported_priority() -> None:
    event = InteractionPriorityEvent(
        event_id="evt-1",
        priority="warning",
        message_text="Obstacle ahead",
        message_key="obstacle_warning",
        created_at_s=1.0,
        source="runtime",
        coalescing_group="obstacle_warning",
    )
    assert event.priority == "warning"
    assert event.coalescing_group == "obstacle_warning"


def test_runtime_recovery_outcome_contract_has_machine_readable_fields() -> None:
    outcome = RuntimeRecoveryOutcome(
        trigger="interrupt",
        status="recovered",
        spoken_text="Stopped.",
        error_code="interrupt_applied",
        duration_ms=200,
        next_runtime_state="standby",
        completion_status="interrupted",
    )
    payload = outcome.to_dict()
    assert payload["trigger"] == "interrupt"
    assert payload["status"] == "recovered"
    assert payload["error_code"] == "interrupt_applied"
    assert payload["next_runtime_state"] == "standby"


def test_wake_policy_and_standby_outcome_contract_shapes_are_machine_readable() -> None:
    selection = WakePolicySelection(
        selected_mode="keyword_low_power",
        fallback_mode="hardware_trigger",
        dev_fallback_mode="stt_based_wake",
        selection_source="configured",
    )
    outcome = StandbyWakeOutcome(
        trigger="wake_policy",
        status="wake_accepted",
        spoken_text="",
        next_runtime_state="wake",
        selected_wake_mode="keyword_low_power",
        attempt_source_mode="keyword_low_power",
        payload={"wake_cycle_locked": True},
    )
    selection_payload = selection.to_dict()
    outcome_payload = outcome.to_dict()

    assert selection_payload["selected_mode"] == "keyword_low_power"
    assert selection_payload["selection_source"] == "configured"
    assert outcome_payload["status"] == "wake_accepted"
    assert outcome_payload["next_runtime_state"] == "wake"
    assert outcome_payload["payload"]["wake_cycle_locked"] is True


def test_standby_wake_outcome_contract_supports_wake_missed_field_safe_payload() -> None:
    outcome = StandbyWakeOutcome(
        trigger="wake_policy",
        status="wake_missed",
        spoken_text="",
        error_code="strict_grammar_no_match",
        next_runtime_state="standby",
        selected_wake_mode="stt_based_wake",
        attempt_source_mode="stt_based_wake",
        source_classification="wake_strict_vosk_fallback",
        canonical_wake_alias=None,
        command_suffix_ignored=False,
        payload={
            "fallback_attempted": True,
            "fallback_used": True,
            "field_safe": True,
            "raw_user_content_present": False,
            "wake_miss_streak": 7,
        },
    )
    payload = outcome.to_dict()
    assert payload["status"] == "wake_missed"
    assert payload["source_classification"] == "wake_strict_vosk_fallback"
    assert payload["payload"]["field_safe"] is True
    assert payload["payload"]["raw_user_content_present"] is False


def test_standby_wake_outcome_contract_supports_noncanonical_rejection() -> None:
    outcome = StandbyWakeOutcome(
        trigger="wake_policy",
        status="wake_rejected",
        spoken_text="",
        error_code="wake_phrase_not_approved",
        next_runtime_state="standby",
        selected_wake_mode="stt_based_wake",
        attempt_source_mode="stt_based_wake",
        source_classification="noncanonical_rejected",
        canonical_wake_alias=None,
        command_suffix_ignored=False,
        payload={"field_safe": True, "raw_user_content_present": False},
    )
    payload = outcome.to_dict()
    assert payload["status"] == "wake_rejected"
    assert payload["source_classification"] == "noncanonical_rejected"


def test_wake_reliability_outcome_contract_supports_confirmation_flow() -> None:
    outcome = WakeReliabilityOutcome(
        trigger="wake_reliability",
        status="confirmation_required",
        spoken_text="I heard that. Please repeat once.",
        next_runtime_state="wake_confirmation",
        selected_wake_mode="keyword_low_power",
        canonical_wake_alias="hi egb",
        weak_detection=True,
        confirmation_required=True,
        payload={
            "score": 0.71,
            "wake_to_listen_ms": None,
            "probable_false_accept_review": False,
            "probable_false_reject_review": False,
        },
    )
    payload = outcome.to_dict()
    assert payload["status"] == "confirmation_required"
    assert payload["confirmation_required"] is True
    assert payload["payload"]["score"] == 0.71


def test_speech_loop_recovery_contract_requires_standby_after_third_fault() -> None:
    outcome = SpeechLoopRecoveryResult(
        trigger="speech_loop_recovery",
        status="recovered_to_standby",
        spoken_text="Let's try again. Back to standby.",
        returned_state="standby",
        degraded_mode=False,
        fault_sequence_count=3,
        last_fault_type="stt_failure",
        payload={
            "provider_status": "degraded",
            "reset_triggered": True,
            "retry_allowed": False,
            "telemetry_recorded": True,
        },
    )
    payload = outcome.to_dict()
    assert payload["fault_sequence_count"] == 3
    assert payload["returned_state"] == "standby"
    assert payload["payload"]["reset_triggered"] is True


def test_turn_taking_window_outcome_contract_is_machine_readable() -> None:
    outcome = TurnTakingWindowOutcome(
        trigger="turn_taking",
        status="closed_vocabulary_listening",
        spoken_text="Choose a language: Arabic or English.",
        error_code=None,
        next_runtime_state="listening",
        prompt_surface_id="runtime.onboarding.language",
        prompt_class="onboarding_choice",
        barge_in_allowed=True,
        closed_vocabulary_id="onboarding.language_choice",
        payload={"window_id": "turn-window-01", "retry_count": 0},
    )
    payload = outcome.to_dict()
    assert payload["status"] == "closed_vocabulary_listening"
    assert payload["closed_vocabulary_id"] == "onboarding.language_choice"


def test_guided_dialog_outcome_contract_supports_safe_default_and_graceful_exit() -> None:
    safe_default = GuidedDialogOutcome(
        trigger="guided_dialog",
        status="safe_default_applied",
        spoken_text="Continuing with a safe default.",
        error_code=None,
        next_runtime_state="listening",
        closed_vocabulary_id="onboarding.speed_choice",
        payload={
            "dialog_session_id": "guided-dialog-01",
            "accepted_option_id": None,
            "retry_count": 2,
            "retry_limit": 2,
            "prompt_echo_suppressed": False,
            "safe_default_applied": True,
            "graceful_exit": False,
            "preserved_safety_state": "guided_context_active",
            "fallback_or_exit_reason": "retry_exhausted_keep_default",
        },
    )
    graceful_exit = GuidedDialogOutcome(
        trigger="guided_dialog",
        status="graceful_exit",
        spoken_text="I cannot continue safely.",
        error_code="retry_exhausted",
        next_runtime_state="listening",
        closed_vocabulary_id="confirmation.yes_no_cancel",
        payload={
            "dialog_session_id": "guided-dialog-02",
            "accepted_option_id": None,
            "retry_count": 1,
            "retry_limit": 1,
            "prompt_echo_suppressed": False,
            "safe_default_applied": False,
            "graceful_exit": True,
            "preserved_safety_state": "guided_context_active",
            "fallback_or_exit_reason": "no_safe_value_available",
        },
    )
    assert safe_default.to_dict()["status"] == "safe_default_applied"
    assert graceful_exit.to_dict()["status"] == "graceful_exit"


def test_name_candidate_contract_requires_explicit_acceptance_timestamp() -> None:
    candidate = NameCandidate(
        candidate_id="candidate-01",
        session_id="session-01",
        normalized_candidate_text="sara",
        capture_quality="clear",
        confirmation_status="accepted",
        confirmed_at_ms=1000,
    )
    payload = candidate.to_dict()
    assert payload["confirmation_status"] == "accepted"
    assert payload["confirmed_at_ms"] == 1000


def test_pilot_voice_ux_evaluation_contract_is_field_safe() -> None:
    run = PilotVoiceUXEvaluationRun(
        run_id="pilot-ux-01",
        scenario_label="mixed-language-onboarding",
        journey_type="onboarding",
        completion_status="completed",
        retries_used=1,
        accepted_barge_in_count=2,
        prompt_echo_suppression_count=1,
        out_of_domain_rejection_count=1,
        fallback_or_exit_reason=None,
        raw_utterance_present=False,
        artifact_path="artifacts/pilot-ux-01/voice-ux-summary.json",
    )
    payload = run.to_dict()
    assert payload["raw_utterance_present"] is False
    assert payload["accepted_barge_in_count"] == 2
