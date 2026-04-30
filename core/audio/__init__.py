"""Audio capture profile, preprocessing, and endpointing helpers."""

from core.audio.endpointing import (
    build_capture_attempt,
    derive_endpoint_quality_hints,
    should_trigger_bounded_relisten,
)
from core.audio.preprocessing import PreprocessingOutcome, preprocess_audio_for_capture
from core.audio.profiles import (
    default_capture_profiles,
    normalize_usage_mode,
    select_capture_profile,
)

__all__ = [
    "PreprocessingOutcome",
    "build_capture_attempt",
    "default_capture_profiles",
    "derive_endpoint_quality_hints",
    "normalize_usage_mode",
    "preprocess_audio_for_capture",
    "select_capture_profile",
    "should_trigger_bounded_relisten",
]

