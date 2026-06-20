"""Command parser with risk-aware intent validation profiles."""

from typing import Any

from rapidfuzz import fuzz

from core.command_models import CommandCatalogEntry, ParsedCommandIntent
from core.lexicon.loader import load_command_lexicon
from core.text_integrity import contains_arabic_mojibake, contains_unexpected_unicode, normalize_nfc


def _normalize_input_text(text: str) -> str:
    return normalize_nfc(str(text or "")).strip().lower()


def _encoding_failure_reason(text: str) -> str | None:
    candidate = str(text or "")
    if contains_unexpected_unicode(candidate):
        return "unexpected_unicode"
    if contains_arabic_mojibake(candidate):
        return "encoding_corruption"
    if normalize_nfc(candidate) != candidate:
        return "not_normalized"
    return None


COMMAND_KEYWORDS = {
    # =========================
    # Obstacle Detection
    # =========================
    "enable_obstacle_detection": [
        # English - direct
        "enable obstacle detection",
        "turn on obstacle detection",
        "start obstacle detection",
        "activate obstacle detection",
        "begin obstacle detection",
        "obstacle detection on",
        "obstacles on",
        "start obstacles",
        "enable obstacles",
        "activate obstacles",
        "turn on obstacles",
        "obstacle on",
        "obstacles",
        "start obstacle",

        # English - common STT mistakes / short
        "start obsticle",
        "start obstacle",
        "start ob",
        "enable ob",
        "obstacle detect on",
        "obstacle detector on",
        "activate obstacle",

        # Arabic - formal
        "تشغيل العوائق",
        "تفعيل العوائق",
        "ابدأ العوائق",
        "تشغيل اكتشاف العوائق",
        "تفعيل اكتشاف العوائق",
        "تشغيل نظام العوائق",
        "ابدأ نظام العوائق",
        "شغل العوائق",
        "افتح العوائق",
        "خلي العوائق شغالة",

        # Arabic - Egyptian / casual
        "شغل العوائق",
        "شغّل العوائق",
        "ابدأ العوائق",
        "شغل نظام العوائق",
        "شغل الكشف عن العوائق",
        "شغل التحذير من العوائق",
        "شغل تحذير العوائق",

        # Arabizi / phonetic Arabic
        "shaghal el 3awa2e2",
        "shaghal el 3awa2eq",
        "ebda2 el 3awa2e2",
        "ebda el 3awa2e2",

        # Mixed Arabic/English
        "start obstacle بالعربي",
        "obstacle شغل",
        "activate obstacles عربي",

        # Arabic STT romanization attempts
        "ستارت اوبستاكل",
        "ستارت اوبستكل",
        "ستارت اوبستاك",
        "ستارت اوب",
        "ستارت اوبستاكل",
        "ستارت اوبستكل ديتيكشن",
        "شغل اوبستاكل",
        "افتح اوبستاكل",
        "اكتيفيت اوبستاكل",
        "انابل اوبستاكل",
    ],

    "disable_obstacle_detection": [
        # English - direct
        "disable obstacle detection",
        "turn off obstacle detection",
        "stop obstacle detection",
        "deactivate obstacle detection",
        "end obstacle detection",
        "obstacle detection off",
        "obstacles off",
        "stop obstacles",
        "disable obstacles",
        "turn off obstacles",
        "stop obstacle",
        "obstacle off",

        # English - common STT mistakes / short
        "stop obsticle",
        "stop ob",
        "disable ob",
        "obstacle detect off",
        "deactivate obstacles",

        # Arabic - formal
        "إيقاف العوائق",
        "ايقاف العوائق",
        "تعطيل العوائق",
        "وقف العوائق",
        "إيقاف اكتشاف العوائق",
        "تعطيل اكتشاف العوائق",
        "اقفل العوائق",
        "اطفئ العوائق",
        "إطفاء العوائق",

        # Arabic - Egyptian / casual
        "اطفي العوائق",
        "اطفّي العوائق",
        "اقفل العوائق",
        "وقف العوائق",
        "وقف نظام العوائق",
        "اطفي نظام العوائق",
        "اقفل نظام العوائق",
        "اطفي تحذير العوائق",
        "اقفل تحذير العوائق",

        # Arabizi
        "otfi el 3awa2e2",
        "wa2af el 3awa2e2",
        "a2fel el 3awa2e2",

        # Arabic STT romanization attempts
        "ستوب اوبستاكل",
        "ستوب اوبستكل",
        "ستوب اوب",
        "ديزاابل اوبستاكل",
        "تور اوف اوبستاكل",
        "اوف اوبستاكل",
        "اطفي اوبستاكل",
    ],

    # =========================
    # Face Recognition
    # =========================
    "recognize_face": [
        # English - direct
        "recognize face",
        "detect face",
        "find face",
        "identify face",
        "face recognition",
        "run face recognition",
        "scan face",
        "analyze face",
        "who is this",
        "who is that",
        "who is in front of me",
        "identify person",
        "recognize person",

        # English - short / STT variants
        "recognise face",
        "face detect",
        "detect the face",
        "find the face",
        "identify the face",
        "recognize the face",
        "detect person",
        "recognize people",

        # Arabic - formal
        "تعرّف على الوجه",
        "تعرف على الوجه",
        "التعرف على الوجه",
        "شغل التعرف على الوجه",
        "ابدأ التعرف على الوجه",
        "حدد الوجه",
        "اكتشف الوجه",
        "اعرف الشخص",
        "مين ده",
        "مين دا",
        "مين اللي قدامي",
        "اعرف مين قدامي",

        # Arabic - Egyptian / casual
        "تعرّف على الوش",
        "تعرف على الوش",
        "اعرف الوش",
        "هات الوش",
        "اعرف ده مين",
        "هو مين ده",
        "مين الشخص ده",

        # Arabizi
        "e3raf el wish",
        "ta3arraf 3ala el wish",
        "meen da",
        "meen elly odammy",

        # Arabic STT romanization attempts
        "ريكونيز فيس",
        "ديتيكت فيس",
        "فايس ريكوجنيشن",
        "فيس ريكوجنيشن",
        "فايس ديتيكشن",
    ],

    # =========================
    # Emotion Recognition
    # =========================
    "recognize_emotion": [
        # English - direct
        "recognize emotion",
        "detect emotion",
        "detect mood",
        "analyze emotion",
        "analyze mood",
        "emotion recognition",
        "read emotion",
        "read facial emotion",
        "how does he feel",
        "how does she feel",
        "what is the emotion",
        "what is the mood",

        # English - short / STT variants
        "recognise emotion",
        "emotion detect",
        "detect feelings",
        "analyze feelings",
        "what is he feeling",
        "what is she feeling",

        # Arabic - formal
        "احساس الوجه",
        "إحساس الوجه",
        "مشاعر الوجه",
        "اعراض الوجه",  # STT mistake sometimes
        "التعرف على المشاعر",
        "تعرف على المشاعر",
        "حلل المشاعر",
        "اعرف مشاعره",
        "اعرف حالته النفسية",
        "هو حاسس بإيه",
        "هي حاسة بإيه",

        # Arabic - Egyptian / casual
        "احساس الوش",
        "مشاعر الوش",
        "اعرف احساسه",
        "حاسس بإيه",
        "حالته ايه",
        "مبسوط ولا زعلان",

        # Arabizi
        "e7sas el wish",
        "masha3er el wish",
        "7asoos beeh",
        "7aletoh eh",

        # Arabic STT romanization attempts
        "ريكونيز ايموشن",
        "ديتيكت ايموشن",
        "موود ديتيكشن",
        "ايموشن ريكوجنيشن",
    ],

    # =========================
    # Vision System
    # =========================
    "enable_vision": [
        "start vision",
        "run vision",
        "open vision",
        "start vision system",
        "run vision system",
        "open assistive vision system",
        "launch vision",
        "vision on",
        "start fision",
        "run fision",
        "شغل فيجن",
        "شغل الرؤية",
        "شغل نظام الرؤية",
        "افتح فيجن",
        "افتح الرؤية",
        "ابدأ فيجن",
        "ابدأ نظام الرؤية",
    ],

    "disable_vision": [
        "stop vision",
        "close vision",
        "turn off vision",
        "stop vision system",
        "close vision system",
        "stop assistive vision system",
        "vision off",
        "stop fision",
        "وقف فيجن",
        "اقفل فيجن",
        "اطفي فيجن",
        "وقف الرؤية",
        "اقفل الرؤية",
        "اطفي الرؤية",
        "ايقاف نظام الرؤية",
    ],

    # =========================
    # Money Detection
    # =========================
    "enable_money_detection": [
        # English
        "enable money detection",
        "start money detection",
        "turn on money detection",
        "activate money detection",
        "currency detection on",
        "detect money",
        "scan money",
        "identify money",
        "identify currency",
        "banknote detection",
        "detect banknotes",
        "money on",

        # English - short / STT variants
        "enable money",
        "start money",
        "money detection on",
        "currency on",
        "start currency detection",

        # Arabic
        "تشغيل كشف الفلوس",
        "تفعيل كشف الفلوس",
        "تشغيل كشف المال",
        "تشغيل كشف العملة",
        "تشغيل كشف النقود",
        "ابدأ كشف الفلوس",
        "شغل كشف الفلوس",
        "شغل الفلوس",
        "شغل كشف العملات",
        "شغل كشف الجنيه",
        "شغل كشف الورق",
        "شغل كشف الكاش",

        # Arabic - Egyptian
        "شغل كشف الفلوس",
        "شغل كشف الكاش",
        "شغل كشف العملة",
        "ابدأ الفلوس",

        # Arabizi
        "shaghal kashf el floos",
        "ebda2 kashf el floos",
        "kashf floos",

        # Arabic STT romanization
        "ستارت موني ديتيكشن",
        "انابل موني ديتيكشن",
        "موني ديتيكشن اون",
        "كاش ديتيكشن",
    ],

    "disable_money_detection": [
        # English
        "disable money detection",
        "stop money detection",
        "turn off money detection",
        "deactivate money detection",
        "currency detection off",
        "stop detecting money",
        "money off",

        # English - short
        "disable money",
        "stop money",
        "money detection off",
        "currency off",

        # Arabic
        "إيقاف كشف الفلوس",
        "ايقاف كشف الفلوس",
        "تعطيل كشف الفلوس",
        "وقف كشف الفلوس",
        "اقفل كشف الفلوس",
        "اطفي كشف الفلوس",
        "وقف كشف العملة",
        "اقفل كشف العملة",
        "اطفي كشف العملات",

        # Arabizi
        "otfi kashf el floos",
        "wa2af kashf el floos",

        # Arabic STT romanization
        "ستوب موني ديتيكشن",
        "ديزاابل موني ديتيكشن",
        "موني ديتيكشن اوف",
    ],

    # =========================
    # OCR
    # =========================
    "enable_OCR": [
        # English
        "enable ocr",
        "start ocr",
        "turn on ocr",
        "activate ocr",
        "read text",
        "read the text",
        "text recognition",
        "start text recognition",
        "read words",
        "read document",
        "read this",
        "scan text",
        "ocr on",

        # English - STT variants
        "start o c r",
        "enable o c r",
        "ocr start",
        "text reader on",
        "turn on text reader",

        # Arabic
        "تشغيل التعرف على النصوص",
        "تفعيل التعرف على النصوص",
        "تشغيل قراءة النص",
        "تفعيل قراءة النص",
        "تشغيل قراءة الكلام",
        "ابدأ قراءة النص",
        "شغل قراءة النص",
        "شغل النص",
        "ابدأ التعرف على النص",
        "اقرأ النص",
        "اقرأ الكلام",
        "اقرأ اللي قدامي",
        "شغل قارئ النص",

        # Arabic - Egyptian
        "شغل قراءة النص",
        "شغل القراية",
        "ابدأ القراية",
        "اقرأ",

        # Arabizi
        "shaghal qera2et el nas",
        "ebda2 qera2a",
        "ocr shaghala",

        # Arabic STT romanization
        "ستارت ocr",
        "ستارت او سي ار",
        "انابل او سي ار",
        "شغل او سي ار",
    ],

    "disable_OCR": [
        # English
        "disable ocr",
        "stop ocr",
        "turn off ocr",
        "deactivate ocr",
        "stop reading text",
        "stop reading",
        "ocr off",
        "text reader off",
        "turn off text reader",

        # English - short / STT variants
        "stop o c r",
        "disable o c r",
        "ocr stop",

        # Arabic
        "إيقاف التعرف على النصوص",
        "ايقاف التعرف على النصوص",
        "تعطيل التعرف على النصوص",
        "وقف التعرف على النصوص",
        "إيقاف النص",
        "ايقاف النص",
        "وقف النص",
        "اقفل النص",
        "اطفي قراءة النص",
        "وقف قراءة النص",
        "اقفل قراءة النص",
        "اطفي القراية",

        # Arabic - Egyptian
        "اطفي النص",
        "اقفل النص",
        "وقف القراية",
        "اطفي القراية",

        # Arabizi
        "otfi qera2et el nas",
        "wa2af el ocr",

        # Arabic STT romanization
        "ستوب ocr",
        "ديزاابل ocr",
        "اوف ocr",
    ],

    # =========================
    # Language Switching
    # =========================
    "set_language_ar": [
        # English
        "switch to arabic",
        "change language to arabic",
        "set language arabic",
        "set arabic",
        "arabic mode",
        "arabic language",
        "language arabic",
        "turn arabic on",

        # English - STT variants
        "switch to arab",
        "switch language arabic",
        "change to arabic",
        "arabic",

        # Arabic
        "غير اللغة للعربية",
        "تغيير اللغة للعربية",
        "خليها عربي",
        "حول للعربي",
        "بدل للعربي",
        "عربي",
        "اللغة عربي",
        "عايز عربي",
        "شغل العربي",
        "حط عربي",
        "لغة عربية",

        # Arabizi / mixed
        "3arabi",
        "araby",
        "khalyha 3araby",
    ],

    "set_language_en": [
        # English
        "switch to english",
        "change language to english",
        "set language english",
        "set english",
        "english mode",
        "english language",
        "language english",
        "turn english on",

        # English - STT variants
        "switch language english",
        "change to english",
        "english",
        "inglish",

        # Arabic
        "غير اللغة للانجليزي",
        "غير اللغة للإنجليزي",
        "تغيير اللغة للانجليزي",
        "تغيير اللغة للإنجليزي",
        "خليها انجليزي",
        "حول للانجليزي",
        "بدل للانجليزي",
        "انجليزي",
        "إنجليزي",
        "لغة انجليزي",
        "عايز انجليزي",
        "شغل الانجليزي",
        "حط انجليزي",

        # Arabizi
        "english",
        "englizy",
        "en",
        "inglsh",  # typo
    ],

    "set_language": [
        # English
        "change language",
        "language options",
        "language settings",
        "switch language",
        "set language",
        "choose language",
        "select language",
        "language menu",

        # Arabic
        "غير اللغة",
        "تغيير اللغة",
        "بدل اللغة",
        "اختيار اللغة",
        "اعدادات اللغة",
        "قائمة اللغة",
        "لغة",

        # Mixed
        "language",
        "lang",
    ],

    # =========================
    # Voice Gender
    # =========================
    "set_voice_gender_male": [
        # English
        "male voice",
        "set male voice",
        "make voice male",
        "switch to male voice",
        "voice male",
        "male",
        "man voice",
        "boy voice",
        "deep voice",

        # Arabic
        "ذكر",
        "صوت ذكر",
        "خلي الصوت ذكر",
        "خلي الصوت راجل",
        "صوت راجل",
        "صوت رجل",
        "غير الصوت لذكر",
        "بدل الصوت لذكر",

        # Arabizi
        "sout zakar",
        "khaly el sout zakar",
    ],

    "set_voice_gender_female": [
        # English
        "female voice",
        "set female voice",
        "make voice female",
        "switch to female voice",
        "voice female",
        "female",
        "woman voice",
        "girl voice",

        # Arabic
        "انثى",
        "أنثى",
        "صوت بنت",
        "صوت انثى",
        "خلي الصوت بنت",
        "خلي الصوت انثى",
        "غير الصوت لانثى",
        "بدل الصوت لانثى",

        # Arabizi
        "sout bnt",
        "sout ontha",
    ],

    "set_voice_gender": [
        # English
        "change voice",
        "voice options",
        "voice settings",
        "choose voice",
        "select voice",
        "change voice gender",
        "gender voice",

        # Arabic
        "تغيير الصوت",
        "اعدادات الصوت",
        "اختيار الصوت",
        "نوع الصوت",
        "صوت",
    ],

    # =========================
    # Speech Speed
    # =========================
    "speech_speed_increase": [
        # English
        "increase speech speed",
        "speed up",
        "faster",
        "make it faster",
        "talk faster",
        "speak faster",
        "boost speed",
        "increase speed",
        "raise speed",
        "speed higher",

        # Arabic
        "اسرع",
        "سرّع",
        "سرعة",
        "خلي الكلام اسرع",
        "كلام اسرع",
        "زود السرعة",
        "ارفع السرعة",
        "سرعة اعلى",
        "سرعة أكبر",
    ],

    "speech_speed_decrease": [
        # English
        "decrease speech speed",
        "slow down",
        "slower",
        "make it slower",
        "talk slower",
        "speak slower",
        "reduce speed",
        "decrease speed",
        "lower speed",
        "speed lower",

        # Arabic
        "ابطيء",
        "بطّئ",
        "بطيء",
        "خلي الكلام ابطأ",
        "كلام ابطأ",
        "قلل السرعة",
        "نزل السرعة",
        "سرعة اقل",
        "سرعة أقل",
    ],

    "speech_speed_normal": [
        # English
        "normal speech speed",
        "default speed",
        "reset speech speed",
        "normal speed",
        "back to normal speed",
        "make it normal",

        # Arabic
        "سرعة طبيعية",
        "رجع السرعة الطبيعية",
        "خليها طبيعية",
        "السرعة العادية",
        "رجع السرعة",
    ],

    "set_speech_speed": [
        # English
        "set speech speed",
        "adjust speed",
        "speech speed",
        "change speech speed",
        "set speed",
        "adjust speaking speed",
        "change speed",

        # Arabic
        "ضبط سرعة الكلام",
        "سرعة الكلام",
        "تعديل سرعة الكلام",
        "غير سرعة الكلام",
        "حدد سرعة الكلام",
        "سرعة",
        "سبيد",
    ],

    # =========================
    # System Control
    # =========================
    "start_system": [
        "start system",
        "system on",
        "turn on system",
        "activate system",
        "run system",
        "enable system",
        "boot system",

        "تشغيل النظام",
        "ابدأ النظام",
        "شغل النظام",
        "افتح النظام",
        "النظام شغال",
        "سيستم اون",
        "ستارت سيستم",
    ],

    "stop_system": [
        "stop system",
        "system off",
        "turn off system",
        "deactivate system",
        "shutdown system",
        "disable system",

        "إيقاف النظام",
        "ايقاف النظام",
        "اطفي النظام",
        "اقفل النظام",
        "وقف النظام",
        "سيستم اوف",
        "ستوب سيستم",
    ],

    "get_system_status": [
        "get status",
        "system status",
        "check status",
        "check system status",
        "show status",
        "what is the status",
        "status",

        "حالة النظام",
        "حاله النظام",
        "اعرض حالة النظام",
        "وضع النظام",
        "النظام عامل ايه",
        "الدنيا تمام",
        "الستاتس",
    ],

    "reset_settings": [
        "reset settings",
        "restore settings",
        "default settings",
        "factory reset",
        "reset configuration",
        "restore defaults",

        "اعادة ضبط الاعدادات",
        "إعادة ضبط الإعدادات",
        "ريست الاعدادات",
        "ارجع الاعدادات",
        "رجع الافتراضي",
        "الاعدادات الافتراضية",
    ],
}


CAPABILITY_INTENTS = {
    "enable_obstacle_detection",
    "disable_obstacle_detection",
    "enable_vision",
    "disable_vision",
    "recognize_face",
    "recognize_emotion",
    "enable_money_detection",
    "disable_money_detection",
    "enable_OCR",
    "disable_OCR",
}

SETTINGS_INTENTS = {
    "set_language_ar",
    "set_language_en",
    "set_language",
    "set_voice_gender_male",
    "set_voice_gender_female",
    "set_voice_gender",
    "speech_speed_increase",
    "speech_speed_decrease",
    "speech_speed_normal",
    "set_speech_speed",
}

PROTECTED_SYSTEM_INTENTS = {"stop_system", "reset_settings"}
ELEVATED_SYSTEM_INTENTS = {"start_system", "get_system_status"}
SYSTEM_INTENTS = PROTECTED_SYSTEM_INTENTS | ELEVATED_SYSTEM_INTENTS

PARAMETER_REQUIRED_INTENTS = {"set_language", "set_voice_gender"}

_INCOMPLETE_ACTION_TOKENS = frozenset(
    {
        "activate",
        "begin",
        "close",
        "detect",
        "disable",
        "enable",
        "off",
        "on",
        "open",
        "please",
        "put",
        "read",
        "run",
        "scan",
        "start",
        "stop",
        "turn",
        "افتح",
        "اقفل",
        "اقرا",
        "اطفي",
        "اوقف",
        "ايقاف",
        "تعرف",
        "تشغيل",
        "شغل",
        "وقف",
    }
)

_COMMAND_FILLER_TOKENS = frozenset(
    {
        "a",
        "an",
        "can",
        "could",
        "for",
        "me",
        "now",
        "please",
        "the",
        "to",
        "you",
        "على",
        "علي",
        "لي",
        "من",
    }
)

_CAPABILITY_OBJECT_MARKERS = {
    "ocr": (
        "ocr",
        "o c r",
        "reader",
        "reading",
        "text",
        "او سي ار",
        "النص",
        "النصوص",
        "قراءة",
    ),
    "obstacle_detection": (
        "ob",
        "obd",
        "obi",
        "obie",
        "obst",
        "obstacle",
        "obstacles",
        "اوبي",
        "اوبستاكل",
        "الحواجز",
        "العائق",
        "العو",
        "العوائق",
        "كاشف العو",
        "kashf الع",
    ),
    "money_detection": (
        "cash",
        "currency",
        "money",
        "monie",
        "munny",
        "الفلوس",
        "الماني",
        "النقود",
        "ماني",
    ),
    "face_recognition": (
        "face",
        "person",
        "wish",
        "الوجه",
        "الوجوه",
        "الوش",
        "فيس",
    ),
    "emotion_recognition": (
        "emotion",
        "feeling",
        "feelings",
        "mood",
        "ايموشن",
        "المشاعر",
        "المود",
    ),
    "vision_system": (
        "vision",
        "vision system",
        "fision",
        "assistive vision",
        "فيجن",
        "الرؤية",
        "نظام الرؤية",
    ),
}

RISK_PROFILES = {
    "normal": {"threshold": 70.0, "ambiguity_margin": 3.0},
    "elevated": {"threshold": 83.0, "ambiguity_margin": 5.0},
    "protected": {"threshold": 90.0, "ambiguity_margin": 7.0},
}


def _intent_category(intent_id: str) -> str:
    if intent_id in CAPABILITY_INTENTS:
        return "capability"
    if intent_id in SETTINGS_INTENTS:
        return "settings"
    if intent_id in SYSTEM_INTENTS:
        return "system"
    return "capability"


def _intent_risk(intent_id: str) -> str:
    if intent_id in PROTECTED_SYSTEM_INTENTS:
        return "protected"
    if intent_id in ELEVATED_SYSTEM_INTENTS:
        return "elevated"
    return "normal"


def _route_target_for_category(category: str) -> str:
    if category == "settings":
        return "settings_manager"
    return "controller"


def _lexicon_intent_metadata(intent_id: str) -> dict[str, str | None]:
    try:
        intent = load_command_lexicon().intents.get(intent_id)
    except Exception:  # noqa: BLE001
        return {}
    if intent is None:
        return {}
    return {
        "category": intent.category,
        "risk_level": intent.risk_level,
        "capability_id": intent.capability_id,
    }


def _intent_family(intent_id: str) -> str:
    normalized = str(intent_id or "").strip().lower()
    if normalized.startswith("set_language_"):
        return "set_language"
    if normalized.startswith("set_voice_gender_"):
        return "set_voice_gender"
    return normalized


def _normalized_keywords(keywords: list[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in keywords:
        value = _normalize_input_text(raw)
        if not value:
            continue
        if contains_unexpected_unicode(value) or contains_arabic_mojibake(value):
            continue
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return tuple(normalized)


def _build_command_catalog() -> dict[str, CommandCatalogEntry]:
    catalog: dict[str, CommandCatalogEntry] = {}
    effective_keywords: dict[str, list[str]] = {intent_id: list(keywords) for intent_id, keywords in COMMAND_KEYWORDS.items()}
    try:
        for intent_id, phrases in load_command_lexicon().parser_phrases_by_intent().items():
            effective_keywords.setdefault(intent_id, []).extend(phrases)
    except Exception:  # noqa: BLE001
        pass

    for intent_id, keywords in effective_keywords.items():
        metadata = _lexicon_intent_metadata(intent_id)
        risk_level = str(metadata.get("risk_level") or _intent_risk(intent_id))
        category = str(metadata.get("category") or _intent_category(intent_id))
        profile = RISK_PROFILES[risk_level]
        is_follow_up_source = intent_id == "recognize_face"
        catalog[intent_id] = CommandCatalogEntry(
            intent_id=intent_id,
            category=category,
            risk_level=risk_level,
            keywords=_normalized_keywords(keywords),
            base_threshold=float(profile["threshold"]),
            ambiguity_margin=float(profile["ambiguity_margin"]),
            requires_parameters=intent_id in PARAMETER_REQUIRED_INTENTS,
            requires_confirmation=intent_id in PROTECTED_SYSTEM_INTENTS,
            follow_up_source=is_follow_up_source,
            follow_up_target="recognize_emotion" if is_follow_up_source else None,
            route_target=_route_target_for_category(category),
        )
    return catalog


COMMAND_CATALOG = _build_command_catalog()


def _score_intents(normalized_text: str) -> list[tuple[str, float, str]]:
    scored: list[tuple[str, float, str]] = []
    if not normalized_text:
        return scored
    normalized_tokens = {token for token in normalized_text.split() if token}
    for intent_id, entry in COMMAND_CATALOG.items():
        best_score = 0.0
        best_keyword = ""
        for keyword in entry.keywords:
            keyword_value = keyword.lower()
            ratio_score = float(fuzz.ratio(keyword_value, normalized_text))
            partial_score = float(fuzz.partial_ratio(keyword_value, normalized_text))
            token_set_score = float(fuzz.token_set_ratio(keyword_value, normalized_text))
            token_sort_score = float(fuzz.token_sort_ratio(keyword_value, normalized_text))

            keyword_tokens = {token for token in keyword_value.split() if token}
            overlap_ratio = (
                len(keyword_tokens & normalized_tokens) / len(keyword_tokens)
                if keyword_tokens
                else 0.0
            )
            composite_score = max(
                ratio_score,
                (0.55 * partial_score) + (0.45 * token_set_score),
                (0.65 * token_set_score) + (0.35 * token_sort_score),
            )
            if overlap_ratio >= 0.95:
                composite_score += 7.0
            elif overlap_ratio >= 0.75:
                composite_score += 4.0
            elif overlap_ratio <= 0.25:
                composite_score -= 5.0

            extra_token_count = max(0, len(normalized_tokens) - len(keyword_tokens))
            if extra_token_count >= 5 and overlap_ratio < 0.6:
                composite_score -= 6.0

            score = max(0.0, min(100.0, composite_score))
            if score > best_score or (
                score == best_score
                and (
                    keyword_value == normalized_text
                    or len(keyword_value) > len(best_keyword)
                )
            ):
                best_score = score
                best_keyword = keyword
        if best_keyword:
            scored.append((intent_id, best_score, best_keyword))
    scored.sort(
        key=lambda item: (
            item[1],
            _normalize_input_text(item[2]) == normalized_text,
            len(_normalize_input_text(item[2])),
        ),
        reverse=True,
    )
    return scored


def _rejected_parse(
    *,
    raw_text: str,
    normalized_text: str,
    intent_id: str | None,
    category: str | None,
    risk_level: str | None,
    matched_keyword: str | None,
    score: float,
    threshold: float,
    runner_up_intent: str | None,
    runner_up_score: float | None,
    reason: str,
    extra_metadata: dict[str, Any] | None = None,
) -> ParsedCommandIntent:
    metadata = dict(extra_metadata or {})
    metadata.setdefault("normalized_text", normalized_text)
    return ParsedCommandIntent(
        raw_text=raw_text,
        normalized_text=normalized_text,
        intent_id=intent_id,
        category=category,
        risk_level=risk_level,
        matched_keyword=matched_keyword,
        score=score,
        threshold=threshold,
        runner_up_intent=runner_up_intent,
        runner_up_score=runner_up_score,
        accepted=False,
        rejection_reason=reason,
        metadata=metadata,
    )


def _is_incomplete_capability_command(normalized_text: str, entry: CommandCatalogEntry) -> bool:
    if entry.category != "capability":
        return False

    text = _normalize_input_text(normalized_text)
    if not text:
        return False

    capability_markers = _CAPABILITY_OBJECT_MARKERS.get(_intent_family(entry.intent_id), ())
    if any(marker in text for marker in capability_markers):
        return False

    tokens = tuple(token for token in text.replace("-", " ").split() if token)
    if not tokens:
        return False

    content_tokens = tuple(token for token in tokens if token not in _COMMAND_FILLER_TOKENS)
    if not content_tokens:
        return True

    has_action = any(token in _INCOMPLETE_ACTION_TOKENS for token in content_tokens)
    if not has_action:
        return False

    return all(
        token in _INCOMPLETE_ACTION_TOKENS or token in _COMMAND_FILLER_TOKENS
        for token in content_tokens
    )


def parse_command(
    text: str,
    *,
    canonical_command_text: str | None = None,
    recognition_metadata: dict[str, Any] | None = None,
) -> ParsedCommandIntent:
    raw_text = str(text or "")
    parser_input_raw = canonical_command_text if canonical_command_text is not None else raw_text
    encoding_failure = _encoding_failure_reason(parser_input_raw)
    parser_input_text = normalize_nfc(parser_input_raw)
    raw_text = normalize_nfc(raw_text)
    normalized_text = _normalize_input_text(parser_input_text)
    metadata: dict[str, Any] = {
        "normalized_text": normalized_text,
        "canonical_command_text": parser_input_text.strip() or normalized_text,
    }
    if recognition_metadata:
        metadata["recognition"] = dict(recognition_metadata)

    if encoding_failure is not None:
        return _rejected_parse(
            raw_text=raw_text,
            normalized_text=normalized_text,
            intent_id=None,
            category=None,
            risk_level=None,
            matched_keyword=None,
            score=0.0,
            threshold=float(RISK_PROFILES["normal"]["threshold"]),
            runner_up_intent=None,
            runner_up_score=None,
            reason=encoding_failure,
            extra_metadata=metadata,
        )

    if not normalized_text:
        return _rejected_parse(
            raw_text=raw_text,
            normalized_text=normalized_text,
            intent_id=None,
            category=None,
            risk_level=None,
            matched_keyword=None,
            score=0.0,
            threshold=float(RISK_PROFILES["normal"]["threshold"]),
            runner_up_intent=None,
            runner_up_score=None,
            reason="below_threshold",
            extra_metadata=metadata,
        )

    scored = _score_intents(normalized_text)
    if not scored:
        return _rejected_parse(
            raw_text=raw_text,
            normalized_text=normalized_text,
            intent_id=None,
            category=None,
            risk_level=None,
            matched_keyword=None,
            score=0.0,
            threshold=float(RISK_PROFILES["normal"]["threshold"]),
            runner_up_intent=None,
            runner_up_score=None,
            reason="below_threshold",
            extra_metadata=metadata,
        )

    best_intent, best_score, best_keyword = scored[0]
    runner_up_intent = scored[1][0] if len(scored) > 1 else None
    runner_up_score = scored[1][1] if len(scored) > 1 else None
    runner_up_keyword = scored[1][2] if len(scored) > 1 else None
    entry = COMMAND_CATALOG[best_intent]
    threshold = float(entry.base_threshold)

    if best_score < threshold:
        return _rejected_parse(
            raw_text=raw_text,
            normalized_text=normalized_text,
            intent_id=best_intent,
            category=entry.category,
            risk_level=entry.risk_level,
            matched_keyword=best_keyword,
            score=best_score,
            threshold=threshold,
            runner_up_intent=runner_up_intent,
            runner_up_score=runner_up_score,
            reason="below_threshold",
            extra_metadata=metadata,
        )

    if _is_incomplete_capability_command(normalized_text, entry):
        metadata["matched_keyword_candidate"] = best_keyword
        return _rejected_parse(
            raw_text=raw_text,
            normalized_text=normalized_text,
            intent_id=best_intent,
            category=entry.category,
            risk_level=entry.risk_level,
            matched_keyword=best_keyword,
            score=best_score,
            threshold=threshold,
            runner_up_intent=runner_up_intent,
            runner_up_score=runner_up_score,
            reason="incomplete_command",
            extra_metadata=metadata,
        )

    if runner_up_intent is not None and runner_up_score is not None:
        if (best_score - runner_up_score) < float(entry.ambiguity_margin):
            best_is_exact = _normalize_input_text(best_keyword) == normalized_text
            runner_is_exact = _normalize_input_text(runner_up_keyword or "") == normalized_text
            if best_is_exact and not runner_is_exact:
                return ParsedCommandIntent(
                    raw_text=raw_text,
                    normalized_text=normalized_text,
                    intent_id=best_intent,
                    category=entry.category,
                    risk_level=entry.risk_level,
                    matched_keyword=best_keyword,
                    score=best_score,
                    threshold=threshold,
                    runner_up_intent=runner_up_intent,
                    runner_up_score=runner_up_score,
                    accepted=True,
                    rejection_reason=None,
                    metadata=metadata,
                )
            best_family = _intent_family(best_intent)
            runner_family = _intent_family(runner_up_intent)
            if (
                best_family == runner_family
                and best_family in PARAMETER_REQUIRED_INTENTS
                and best_family in COMMAND_CATALOG
            ):
                family_entry = COMMAND_CATALOG[best_family]
                metadata["intent_family"] = best_family
                metadata["ambiguous_variants"] = [best_intent, runner_up_intent]
                return ParsedCommandIntent(
                    raw_text=raw_text,
                    normalized_text=normalized_text,
                    intent_id=best_family,
                    category=family_entry.category,
                    risk_level=family_entry.risk_level,
                    matched_keyword=best_keyword,
                    score=best_score,
                    threshold=float(family_entry.base_threshold),
                    runner_up_intent=runner_up_intent,
                    runner_up_score=runner_up_score,
                    accepted=True,
                    rejection_reason=None,
                    metadata=metadata,
                )
            return _rejected_parse(
                raw_text=raw_text,
                normalized_text=normalized_text,
                intent_id=best_intent,
                category=entry.category,
                risk_level=entry.risk_level,
                matched_keyword=best_keyword,
                score=best_score,
                threshold=threshold,
                runner_up_intent=runner_up_intent,
                runner_up_score=runner_up_score,
                reason="ambiguous",
                extra_metadata=metadata,
            )

    return ParsedCommandIntent(
        raw_text=raw_text,
        normalized_text=normalized_text,
        intent_id=best_intent,
        category=entry.category,
        risk_level=entry.risk_level,
        matched_keyword=best_keyword,
        score=best_score,
        threshold=threshold,
        runner_up_intent=runner_up_intent,
        runner_up_score=runner_up_score,
        accepted=True,
        rejection_reason=None,
        metadata=metadata,
    )
