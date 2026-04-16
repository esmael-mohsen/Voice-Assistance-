"""Command resolver routes dispatcher intent to controllers."""

import logging
import re

from controllers import mock_controllers as mc
from settings.settings_manager import settings_manager

logger = logging.getLogger(__name__)

# حفظ الحالة الحالية
SESSION_STATE = {
    "last_face_id": None
}

COMMAND_FUNCTION_MAPPING = {
    "enable_obstacle_detection": mc.enable_obstacle_detection,
    "disable_obstacle_detection": mc.disable_obstacle_detection,
    "recognize_face": mc.recognize_face,
    "recognize_emotion": mc.recognize_emotion,
    "enable_money_detection": mc.enable_money_detection,
    "disable_money_detection": mc.disable_money_detection,
    "enable_OCR": mc.enable_OCR,
    "disable_OCR": mc.disable_OCR,
    "start_system": mc.start_system,
    "stop_system": mc.stop_system,
    "get_system_status": mc.get_system_status,
    "reset_settings": mc.reset_settings
}

LANGUAGE_COMMANDS = {
    "set_language_ar": "ar-EG",
    "set_language_en": "en-US"
}

VOICE_GENDER_COMMANDS = {
    "set_voice_gender_male": "male",
    "set_voice_gender_female": "female"
}

SPEECH_SPEED_PRESETS = {
    "speech_speed_normal": 1.0
}

SPEECH_SPEED_DELTAS = {
    "speech_speed_increase": 0.15,
    "speech_speed_decrease": -0.15
}


def _clamp_speed(value):
    return max(settings_manager.min_speech_speed, min(value, settings_manager.max_speech_speed))


def _extract_numeric_speed(command_text):
    if not command_text:
        return None
    number_match = re.search(r"(\d+(?:\.\d+)?)", command_text)
    if number_match:
        return float(number_match.group(1))
    lowered = command_text.lower()
    if any(word in lowered for word in ("fast", "سريع")):
        return 1.4
    if any(word in lowered for word in ("slow", "بطي")):
        return 0.8
    return None


def resolve_command(command_key, command_text=None, params=None, metadata=None):
    logger.info("[RESOLVER] Resolving '%s'", command_key)

    if command_key in LANGUAGE_COMMANDS:
        lang_code = LANGUAGE_COMMANDS[command_key]
        return mc.set_language(lang_code)

    if command_key == "set_language":
        lang_code = _infer_language_from_text(command_text)
        if lang_code:
            return mc.set_language(lang_code)
        logger.warning("[RESOLVER] Language parameter missing for text: %s", command_text)
        return None

    if command_key in VOICE_GENDER_COMMANDS:
        gender = VOICE_GENDER_COMMANDS[command_key]
        return mc.set_voice_gender(gender=gender)

    if command_key == "set_voice_gender":
        gender = _infer_gender_from_text(command_text)
        if gender:
            return mc.set_voice_gender(gender=gender)
        logger.warning("[RESOLVER] Gender parameter missing for text: %s", command_text)
        return None

    if command_key in SPEECH_SPEED_PRESETS:
        speed = _clamp_speed(SPEECH_SPEED_PRESETS[command_key])
        return mc.set_speech_speed(speed=speed)

    if command_key in SPEECH_SPEED_DELTAS:
        delta = SPEECH_SPEED_DELTAS[command_key]
        target_speed = _clamp_speed(settings_manager.speech_speed + delta)
        return mc.set_speech_speed(speed=target_speed)

    if command_key == "set_speech_speed":
        speed = _extract_numeric_speed(command_text)
        if speed is None:
            speed = settings_manager.default_speech_speed
        speed = _clamp_speed(speed)
        return mc.set_speech_speed(speed=speed)

    func = COMMAND_FUNCTION_MAPPING.get(command_key)
    if not func:
        logger.warning("[RESOLVER] Command '%s' not found", command_key)
        return None

    if command_key == "recognize_face":
        face_id = func(**params) if params else func()
        SESSION_STATE["last_face_id"] = face_id
        return face_id

    if command_key == "recognize_emotion":
        if params is None:
            params = {}
        if "face_id" not in params:
            params["face_id"] = SESSION_STATE.get("last_face_id")
        return func(**params)

    return func(**params) if params else func()


def _infer_language_from_text(command_text):
    if not command_text:
        return None
    lowered = command_text.lower()
    if any(word in lowered for word in ("arabic", "عربي", "العربية")):
        return "ar-EG"
    if any(word in lowered for word in ("english", "inglish", "انجلش")):
        return "en-US"
    return None


def _infer_gender_from_text(command_text):
    if not command_text:
        return None
    lowered = command_text.lower()
    if any(word in lowered for word in ("male", "ذكر")):
        return "male"
    if any(word in lowered for word in ("female", "انثى", "بنت")):
        return "female"
    return None
