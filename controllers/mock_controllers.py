import logging

from settings.settings_manager import settings_manager

logger = logging.getLogger(__name__)


def _respond(event: str, ar_text: str, en_text: str):
    message = settings_manager.speak_localized(ar_text, en_text)
    logger.info("[MOCK][%s] %s", event, message)
    return message


# Obstacle
def enable_obstacle_detection():
    return _respond("Obstacle", "تم تشغيل مستشعر العوائق.", "Obstacle detection enabled.")


def disable_obstacle_detection():
    return _respond("Obstacle", "تم إيقاف مستشعر العوائق.", "Obstacle detection disabled.")


def get_obstacle_status():
    mock_data = {"distance": 1.2, "angle": 45, "speed": 0.3}
    message = settings_manager.speak_localized(
        "لا توجد عوائق قريبة. المسافة تقريباً متر وعشرون سنتيمتراً.",
        "Obstacle clear. Distance is about one point two meters.",
    )
    logger.info("[MOCK][Obstacle] %s -> %s", message, mock_data)
    return mock_data


# Vision
def recognize_face(store_new_face=False):
    face_id = "Face_001"
    if store_new_face:
        _respond("Vision", f"تم حفظ وجه جديد بالمعرف {face_id}.", f"Stored a new face profile {face_id}.")
    spoken_text = _respond("Vision", f"تم التعرف على الوجه {face_id}.", f"Face {face_id} recognized.")
    return {"spoken_text": spoken_text, "face_id": face_id}


def recognize_emotion(face_id=None):
    if face_id:
        emotion = "Happy"
        spoken_text = _respond(
            "Vision",
            f"الحالة المزاجية للوجه {face_id} تبدو سعيدة.",
            f"Detected a happy emotion for {face_id}.",
        )
        return {"spoken_text": spoken_text, "face_id": face_id, "emotion": emotion}
    logger.warning("[MOCK][Vision] No face detected for emotion analysis")
    spoken_text = _respond(
        "Vision",
        "لا أستطيع تحليل المشاعر من دون وجه معروف.",
        "I need a known face to read the emotion.",
    )
    return {"spoken_text": spoken_text, "face_id": None, "emotion": None}


# Money Detection
def enable_money_detection():
    return _respond("Money", "تم تشغيل نظام التعرف على العملات.", "Money detection enabled.")


def disable_money_detection():
    return _respond("Money", "تم إيقاف نظام التعرف على العملات.", "Money detection disabled.")


# OCR
def enable_OCR():
    return _respond("OCR", "تم تشغيل قراءة النصوص.", "Text reading mode is on.")


def disable_OCR():
    return _respond("OCR", "تم إيقاف قراءة النصوص.", "Text reading mode is off.")


# Settings
def set_language(lang_code):
    result = settings_manager.set_language(lang_code)
    if result.startswith("ar"):
        return _respond("Settings", "تم التحويل إلى اللغة العربية.", "Switched to Arabic.")
    return _respond("Settings", "تم التحويل إلى اللغة الإنجليزية.", "Switched to English.")


def set_voice_gender(gender):
    if not gender:
        logger.warning("[MOCK][Settings] Missing gender value")
        return _respond("Settings", "من فضلك حدد نوع الصوت.", "Please tell me which voice you prefer.")
    result = settings_manager.set_voice_gender(gender)
    if result == "male":
        return _respond("Settings", "تم اختيار صوت ذكوري واضح.", "Switched to a clear male voice.")
    return _respond("Settings", "تم اختيار صوت أنثوي واضح.", "Switched to a clear female voice.")


def set_speech_speed(speed):
    actual_speed = settings_manager.set_speech_speed(speed)
    if actual_speed > 1.0:
        return _respond("Settings", "أصبحت سرعة الكلام أسرع.", "Speech speed increased.")
    if actual_speed < 1.0:
        return _respond("Settings", "أصبحت سرعة الكلام أبطأ.", "Speech speed decreased.")
    return _respond("Settings", "عادت سرعة الكلام إلى الوضع الطبيعي.", "Speech speed back to normal.")


# System
def start_system():
    return _respond("System", "النظام يعمل الآن وجاهز للخدمة.", "System is up and ready.")


def stop_system():
    return _respond("System", "تم إيقاف النظام بأمان.", "System stopped safely.")


def get_system_status():
    status = {
        "obstacle": True,
        "face": True,
        "emotion": True,
        "money": True,
        "OCR": True,
    }
    _respond("System", "كل الأنظمة تعمل بشكل ممتاز.", "All subsystems are healthy.")
    logger.info("[MOCK][System] Status snapshot: %s", status)
    return status


def reset_settings():
    settings_manager.set_language("ar-EG")
    settings_manager.set_voice_gender("female")
    settings_manager.set_speech_speed(settings_manager.default_speech_speed)
    return _respond("System", "تمت إعادة ضبط الإعدادات.", "Settings restored to defaults.")


def _fallback_result(capability_id: str, spoken_text: str, payload: dict | None = None) -> dict:
    result_payload = dict(payload or {})
    result_payload.setdefault("using_fallback", True)
    result_payload.setdefault("capability_id", capability_id)
    return {
        "spoken_text": spoken_text,
        "status": "success",
        "payload": result_payload,
        "used_fallback": True,
        "capability_id": capability_id,
    }


def fallback_ocr_start() -> dict:
    spoken_text = enable_OCR()
    return _fallback_result("ocr", spoken_text)


def fallback_ocr_stop() -> dict:
    spoken_text = disable_OCR()
    return _fallback_result("ocr", spoken_text)


def fallback_ocr_status() -> dict:
    spoken_text = settings_manager.speak_localized(
        "حالة قراءة النصوص متاحة عبر مسار احتياطي.",
        "OCR status is available through fallback path.",
    )
    return _fallback_result("ocr", spoken_text, {"lifecycle_state": "active"})


def fallback_money_start() -> dict:
    spoken_text = enable_money_detection()
    return _fallback_result("money_detection", spoken_text)


def fallback_money_stop() -> dict:
    spoken_text = disable_money_detection()
    return _fallback_result("money_detection", spoken_text)


def fallback_money_status() -> dict:
    spoken_text = settings_manager.speak_localized(
        "حالة كشف العملات متاحة عبر مسار احتياطي.",
        "Money detection status is available through fallback path.",
    )
    return _fallback_result("money_detection", spoken_text, {"lifecycle_state": "active"})


def fallback_face_execute(store_new_face: bool = False) -> dict:
    raw = recognize_face(store_new_face=store_new_face)
    payload = dict(raw)
    spoken_text = str(
        payload.pop("spoken_text", settings_manager.speak_localized("تم التعرف على الوجه.", "Face recognized."))
    )
    return _fallback_result("face_recognition", spoken_text, payload)


def fallback_face_status() -> dict:
    spoken_text = settings_manager.speak_localized(
        "حالة التعرف على الوجه متاحة عبر مسار احتياطي.",
        "Face recognition status is available through fallback path.",
    )
    return _fallback_result("face_recognition", spoken_text, {"lifecycle_state": "active"})


def fallback_emotion_execute(face_id: str | None = None) -> dict:
    raw = recognize_emotion(face_id=face_id)
    payload = dict(raw)
    spoken_text = str(
        payload.pop("spoken_text", settings_manager.speak_localized("تم تحليل المشاعر.", "Emotion analyzed."))
    )
    return _fallback_result("emotion_recognition", spoken_text, payload)


def fallback_emotion_status() -> dict:
    spoken_text = settings_manager.speak_localized(
        "حالة تحليل المشاعر متاحة عبر مسار احتياطي.",
        "Emotion recognition status is available through fallback path.",
    )
    return _fallback_result("emotion_recognition", spoken_text, {"lifecycle_state": "active"})


def fallback_system_status() -> dict:
    status_snapshot = get_system_status()
    spoken_text = settings_manager.speak_localized(
        "حالة النظام متاحة عبر مسار احتياطي.",
        "System status is available through fallback path.",
    )
    return _fallback_result("system_status", spoken_text, {"status": status_snapshot})
