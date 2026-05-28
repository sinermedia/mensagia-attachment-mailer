import locale
from src.infrastructure.ui.locales import es, ca, gl, eu, en

LANGUAGES = {
    "es": ("Español", es.STRINGS),
    "ca": ("Català", ca.STRINGS),
    "gl": ("Galego", gl.STRINGS),
    "eu": ("Euskera", eu.STRINGS),
    "en": ("English", en.STRINGS),
}

_current_lang = "es"


def detect_system_language() -> str:
    try:
        lang_code = locale.getdefaultlocale()[0] or "es"
        code = lang_code[:2].lower()
        return code if code in LANGUAGES else "es"
    except Exception:
        return "es"


def set_language(lang_code: str):
    global _current_lang
    if lang_code in LANGUAGES:
        _current_lang = lang_code


def get_language() -> str:
    return _current_lang


def t(key: str, **kwargs) -> str:
    strings = LANGUAGES[_current_lang][1]
    text = strings.get(key, LANGUAGES["es"][1].get(key, key))
    return text.format(**kwargs) if kwargs else text


def language_names() -> dict[str, str]:
    return {code: name for code, (name, _) in LANGUAGES.items()}
