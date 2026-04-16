# core/parser.py
from dataclasses import dataclass
from rapidfuzz import fuzz

MATCH_THRESHOLD = 70  

@dataclass
class CommandMatch:
    key: str
    keyword: str
    score: float


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



def parse_command(text):
    text_lower = text.lower()
    best_match = None
    highest_score = 0
    matched_keyword = ""

    for command, keywords in COMMAND_KEYWORDS.items():
        for keyword in keywords:
            score = fuzz.ratio(keyword.lower(), text_lower)
            if score > highest_score:
                highest_score = score
                best_match = command
                matched_keyword = keyword

    if highest_score >= MATCH_THRESHOLD and best_match:
        return CommandMatch(key=best_match, keyword=matched_keyword, score=highest_score)
    return None
