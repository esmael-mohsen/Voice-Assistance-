import logging

from settings.settings_manager import settings_manager

logger = logging.getLogger(__name__)


def _respond(event: str, ar_text: str, en_text: str):
    message = settings_manager.speak_localized(ar_text, en_text)
    logger.info("[MOCK][%s] %s", event, message)
    return message


# Obstacle
def enable_obstacle_detection():
    return _respond("Obstacle", "تم تشغيل مستشعر العوائق", "Obstacle detection enabled")


def disable_obstacle_detection():
    return _respond("Obstacle", "تم إيقاف مستشعر العوائق", "Obstacle detection disabled")


def get_obstacle_status():
    mock_data = {"distance": 1.2, "angle": 45, "speed": 0.3}
    message = settings_manager.speak_localized(
        "لا توجد عوائق قريبة، المسافة متر و عشرون سنتيمتر",
        "Obstacle clear. Distance is about one point two meters."
    )
    logger.info("[MOCK][Obstacle] %s -> %s", message, mock_data)
    return mock_data


# Vision
def recognize_face(store_new_face=False):
    face_id = "Face_001"
    if store_new_face:
        _respond("Vision", f"تم حفظ وجه جديد بالرقم {face_id}", f"Stored a new face profile {face_id}")
    return _respond("Vision", f"تم التعرف على الوجه {face_id}", f"Face {face_id} recognized")


def recognize_emotion(face_id=None):
    if face_id:
        emotion = "Happy"
        return _respond(
            "Vision",
            f"الحالة المزاجية للوجه {face_id} هي سعيدة",
            f"Detected a happy emotion for {face_id}"
        )
    logger.warning("[MOCK][Vision] No face detected for emotion analysis")
    return _respond("Vision", "لا أستطيع تحليل المشاعر بدون وجه معروف", "I need a known face to read the emotion")


# Money Detection
def enable_money_detection():
    return _respond("Money", "تم تشغيل نظام التعرف على العملات", "Money detection enabled")


def disable_money_detection():
    return _respond("Money", "تم إيقاف نظام التعرف على العملات", "Money detection disabled")


# OCR
def enable_OCR():
    return _respond("OCR", "تم تشغيل قراءة النصوص", "Text reading mode is on")


def disable_OCR():
    return _respond("OCR", "تم إيقاف قراءة النصوص", "Text reading mode is off")


# Settings
def set_language(lang_code):
    result = settings_manager.set_language(lang_code)
    if result.startswith("ar"):
        return _respond("Settings", "تم التحويل للغة العربية", "Switched to Arabic")
    return _respond("Settings", "تم التحويل للغة الإنجليزية", "Switched to English")


def set_voice_gender(gender):
    if not gender:
        logger.warning("[MOCK][Settings] Missing gender value")
        return _respond("Settings", "من فضلك حدد نوع الصوت", "Please tell me which voice you prefer")
    result = settings_manager.set_voice_gender(gender)
    if result == "male":
        return _respond("Settings", "تم اختيار صوت ذكري احترافي", "Switched to a professional male voice")
    return _respond("Settings", "تم اختيار صوت أنثوي نقي", "Switched to a clear female voice")


def set_speech_speed(speed):
    actual_speed = settings_manager.set_speech_speed(speed)
    if actual_speed > 1.0:
        return _respond("Settings", "سرعة التحدث أصبحت أسرع", "Speech speed increased")
    if actual_speed < 1.0:
        return _respond("Settings", "سرعة التحدث أصبحت أبطأ", "Speech speed decreased")
    return _respond("Settings", "تم ضبط سرعة التحدث للوضع الطبيعي", "Speech speed back to normal")


# System
def start_system():
    return _respond("System", "النظام يعمل الآن بخدمتكم", "System is up and ready")


def stop_system():
    return _respond("System", "تم إيقاف النظام بأمان", "System stopped safely")


def get_system_status():
    status = {
        "obstacle": True,
        "face": True,
        "emotion": True,
        "money": True,
        "OCR": True
    }
    _respond("System", "كل الأنظمة تعمل بشكل ممتاز", "All subsystems are healthy")
    logger.info("[MOCK][System] Status snapshot: %s", status)
    return status


def reset_settings():
    settings_manager.set_language("ar-EG")
    settings_manager.set_voice_gender("female")
    settings_manager.set_speech_speed(settings_manager.default_speech_speed)
    return _respond("System", "تمت إعادة ضبط الإعدادات", "Settings restored to defaults")
