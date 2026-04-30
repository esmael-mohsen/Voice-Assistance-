"""Unit coverage for confidence-band command decision policy."""

from core import parser
from core.assistant_runtime import AssistantRuntime, RuntimeMode
from core.command_models import CommandRecognitionResult, ConfidenceDecisionPolicy
from core.command_post_processing import process_command_transcript


def _runtime(
    *,
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> AssistantRuntime:
    listener = listener_factory()
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=lambda _event: None,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,  # noqa: ARG005
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text, **_kwargs: None,
    )
    runtime._listener = listener
    runtime._provider_state.session_provider = "legacy"
    return runtime


def test_high_confidence_non_protected_command_executes(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )
    recognition = CommandRecognitionResult(
        session_id="s1",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="start obstacle detection",
        confidence_score=0.95,
        confidence_available=True,
        alternative_transcripts=("start obstacle detection",),
        detected_language="en-US",
        latency_ms=10,
        error_code=None,
    )
    parsed = parser.parse_command("start obstacle detection")
    post = process_command_transcript("start obstacle detection")
    decision = runtime._evaluate_confidence_decision(
        recognition_result=recognition,
        post_processing=post,
        parsed_intent=parsed,
        policy=ConfidenceDecisionPolicy(),
        retry_count=0,
    )
    assert decision.decision_band == "high"
    assert decision.decision_action == "execute"


def test_high_confidence_same_intent_alternatives_do_not_force_retry(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )
    recognition = CommandRecognitionResult(
        session_id="s1b",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="switch language to Arab",
        confidence_score=0.9,
        confidence_available=True,
        alternative_transcripts=("switch language to Arab", "switch language to Arabic", "switch language"),
        detected_language="en-US",
        selected_language="en-US",
        latency_ms=10,
        error_code=None,
    )
    post = process_command_transcript(
        "switch language to Arab",
        alternative_transcripts=recognition.alternative_transcripts,
    )
    parsed = parser.parse_command(post.canonical_command_text, canonical_command_text=post.canonical_command_text)
    decision = runtime._evaluate_confidence_decision(
        recognition_result=recognition,
        post_processing=post,
        parsed_intent=parsed,
        policy=ConfidenceDecisionPolicy(),
        retry_count=0,
    )
    assert "conflicting_alternatives" in post.ambiguity_flags
    assert parsed.intent_id == "set_language_ar"
    assert decision.decision_band == "high"
    assert decision.decision_action == "execute"


def test_high_confidence_opposing_parameter_alternatives_still_recover(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )
    recognition = CommandRecognitionResult(
        session_id="s1c",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="switch to arabic",
        confidence_score=0.9,
        confidence_available=True,
        alternative_transcripts=("switch to arabic", "switch to english"),
        detected_language="en-US",
        selected_language="en-US",
        latency_ms=10,
        error_code=None,
    )
    post = process_command_transcript(
        "switch to arabic",
        alternative_transcripts=recognition.alternative_transcripts,
    )
    parsed = parser.parse_command(post.canonical_command_text, canonical_command_text=post.canonical_command_text)
    decision = runtime._evaluate_confidence_decision(
        recognition_result=recognition,
        post_processing=post,
        parsed_intent=parsed,
        policy=ConfidenceDecisionPolicy(),
        retry_count=0,
    )
    assert parsed.intent_id == "set_language_ar"
    assert decision.decision_action == "fallback"


def test_high_confidence_obstacle_variants_do_not_fallback_on_put_en_noise(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )
    alternatives = (
        "put on the obstacle detection please",
        "run obstacle detection please",
        "put on obstacle detection please",
        "put en obstacle detection please",
    )
    recognition = CommandRecognitionResult(
        session_id="s1d",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript=alternatives[0],
        confidence_score=0.92,
        confidence_available=True,
        alternative_transcripts=alternatives,
        detected_language="en-US",
        selected_language="en-US",
        latency_ms=10,
        error_code=None,
    )
    post = process_command_transcript(
        recognition.primary_transcript,
        alternative_transcripts=recognition.alternative_transcripts,
    )
    parsed = parser.parse_command(post.canonical_command_text, canonical_command_text=post.canonical_command_text)
    decision = runtime._evaluate_confidence_decision(
        recognition_result=recognition,
        post_processing=post,
        parsed_intent=parsed,
        policy=ConfidenceDecisionPolicy(),
        retry_count=0,
    )
    assert parsed.intent_id == "enable_obstacle_detection"
    assert decision.decision_band == "high"
    assert decision.decision_action == "execute"


def test_missing_confidence_unprotected_unambiguous_may_execute(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )
    recognition = CommandRecognitionResult(
        session_id="s2",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="switch to english",
        confidence_score=None,
        confidence_available=False,
        alternative_transcripts=("switch to english",),
        detected_language="en-US",
        latency_ms=8,
        error_code=None,
    )
    parsed = parser.parse_command("switch to english")
    post = process_command_transcript("switch to english")
    decision = runtime._evaluate_confidence_decision(
        recognition_result=recognition,
        post_processing=post,
        parsed_intent=parsed,
        policy=ConfidenceDecisionPolicy(),
        retry_count=0,
    )
    assert decision.decision_band == "missing_confidence"
    assert decision.decision_action == "execute"


def test_medium_confidence_prefers_fallback_before_retry(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )
    recognition = CommandRecognitionResult(
        session_id="s3",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="start obsticle maybe",
        confidence_score=0.6,
        confidence_available=True,
        alternative_transcripts=("start obsticle maybe", "start obstacle detection"),
        detected_language="en-US",
        latency_ms=20,
        error_code=None,
    )
    parsed = parser.parse_command("start obstacle detection")
    post = process_command_transcript(
        "start obsticle maybe",
        alternative_transcripts=("start obsticle maybe", "start obstacle detection"),
    )
    decision = runtime._evaluate_confidence_decision(
        recognition_result=recognition,
        post_processing=post,
        parsed_intent=parsed,
        policy=ConfidenceDecisionPolicy(),
        retry_count=0,
    )
    assert decision.decision_band == "medium"
    assert decision.decision_action == "fallback"


def test_medium_confidence_normalized_rescue_command_executes(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )
    recognition = CommandRecognitionResult(
        session_id="s3b",
        recognition_path="rescue",
        provider_id="legacy",
        primary_transcript="\u0627\u0646\u064a\u0628\u0644 \u0627\u0648 \u0633\u064a \u0627\u0631",
        confidence_score=0.81,
        confidence_available=True,
        alternative_transcripts=("\u0627\u0646\u064a\u0628\u0644 \u0627\u0648 \u0633\u064a \u0627\u0631", "enable OCR"),
        detected_language="ar-EG",
        selected_language="ar-EG",
        latency_ms=30,
        error_code=None,
    )
    post = process_command_transcript(
        recognition.primary_transcript,
        alternative_transcripts=recognition.alternative_transcripts,
    )
    parsed = parser.parse_command(post.canonical_command_text, canonical_command_text=post.canonical_command_text)
    decision = runtime._evaluate_confidence_decision(
        recognition_result=recognition,
        post_processing=post,
        parsed_intent=parsed,
        policy=ConfidenceDecisionPolicy(max_retry_cycles=1),
        retry_count=0,
    )
    assert parsed.intent_id == "enable_OCR"
    assert decision.decision_band == "medium"
    assert decision.decision_action == "execute"


def test_protected_command_requires_confirmation_under_uncertainty(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )
    recognition = CommandRecognitionResult(
        session_id="s4",
        recognition_path="fallback",
        provider_id="legacy",
        primary_transcript="stop system",
        confidence_score=0.5,
        confidence_available=True,
        alternative_transcripts=("stop system", "start system"),
        detected_language="en-US",
        latency_ms=30,
        error_code=None,
    )
    parsed = parser.parse_command("stop system")
    post = process_command_transcript(
        "stop system",
        alternative_transcripts=("stop system", "start system"),
    )
    decision = runtime._evaluate_confidence_decision(
        recognition_result=recognition,
        post_processing=post,
        parsed_intent=parsed,
        policy=ConfidenceDecisionPolicy(),
        retry_count=0,
    )
    assert decision.protected_command is True
    assert decision.decision_action == "confirm"
    assert decision.confirmation_required is True


def test_retry_cycles_are_bounded_to_single_additional_attempt(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )
    recognition = CommandRecognitionResult(
        session_id="s5",
        recognition_path="fallback",
        provider_id="legacy",
        primary_transcript="unclear command",
        confidence_score=0.57,
        confidence_available=True,
        alternative_transcripts=("unclear command", "clear command"),
        detected_language="en-US",
        latency_ms=22,
        error_code=None,
    )
    parsed = parser.parse_command("unclear command")
    post = process_command_transcript(
        "unclear command",
        alternative_transcripts=("unclear command", "clear command"),
    )
    decision = runtime._evaluate_confidence_decision(
        recognition_result=recognition,
        post_processing=post,
        parsed_intent=parsed,
        policy=ConfidenceDecisionPolicy(max_retry_cycles=1),
        retry_count=1,
    )
    assert decision.retry_count == 1
    assert decision.decision_action == "refuse"


def test_protected_high_confidence_cloud_command_still_requires_confirmation(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )
    recognition = CommandRecognitionResult(
        session_id="s6",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="stop system",
        confidence_score=0.98,
        confidence_available=True,
        alternative_transcripts=("stop system", "start system"),
        detected_language="en-US",
        selected_language="en-US",
        latency_ms=18,
        error_code=None,
        recognition_source="cloud_primary",
    )
    parsed = parser.parse_command("stop system")
    post = process_command_transcript(
        "stop system",
        alternative_transcripts=("stop system", "start system"),
    )
    decision = runtime._evaluate_confidence_decision(
        recognition_result=recognition,
        post_processing=post,
        parsed_intent=parsed,
        policy=ConfidenceDecisionPolicy(),
        retry_count=0,
    )
    assert decision.decision_action == "confirm"
    assert decision.confirmation_required is True


def test_medium_confidence_with_conflicting_alternatives_requires_recovery_path(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )
    recognition = CommandRecognitionResult(
        session_id="s7",
        recognition_path="fallback",
        provider_id="legacy",
        primary_transcript="start system",
        confidence_score=0.57,
        confidence_available=True,
        alternative_transcripts=("start system", "stop system"),
        detected_language="en-US",
        selected_language="en-US",
        latency_ms=28,
        error_code=None,
        recognition_source="strict_vosk_fallback",
    )
    parsed = parser.parse_command("start system")
    post = process_command_transcript(
        "start system",
        alternative_transcripts=("start system", "stop system"),
    )
    decision = runtime._evaluate_confidence_decision(
        recognition_result=recognition,
        post_processing=post,
        parsed_intent=parsed,
        policy=ConfidenceDecisionPolicy(max_retry_cycles=1),
        retry_count=0,
    )
    assert decision.decision_action in {"retry", "confirm", "refuse"}
