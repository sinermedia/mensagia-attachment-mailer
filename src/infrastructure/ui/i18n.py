import locale
from src.infrastructure.ui.locales import es, ca, gl, eu, en


# Registry of all supported languages: maps language code to (display name, strings dict)
LANGUAGES = {
    "es": ("Español", es.STRINGS),
    "ca": ("Català", ca.STRINGS),
    "gl": ("Galego", gl.STRINGS),
    "eu": ("Euskera", eu.STRINGS),
    "en": ("English", en.STRINGS),
}

# Module-level state: the language code currently active in this session.
# Spanish is the default because it is the primary market for Mensagia.
_current_lang = "es"


def detect_system_language() -> str:
    """Detect the user's preferred language from the OS locale settings.

    Reads the system's default locale and maps it to one of the supported
    language codes. Falls back to Spanish ('es') if the locale is
    undetectable, unsupported, or raises an exception.

    Returns:
        A two-letter language code from the LANGUAGES registry.
    """
    try:
        lang_code = locale.getdefaultlocale()[0] or "es"
        code = lang_code[:2].lower()
        # Return the detected code only if it is actually supported
        return code if code in LANGUAGES else "es"
    except Exception:
        return "es"


def set_language(lang_code: str):
    """Set the active UI language for the current session.

    Updates the module-level language state. Subsequent calls to t()
    will use the new language immediately. Silently ignores unknown
    codes so a bad .env value or OS locale never crashes the app.

    Args:
        lang_code: Two-letter code of the language to activate
            (must be a key in LANGUAGES).
    """
    global _current_lang
    if lang_code in LANGUAGES:
        _current_lang = lang_code


def get_language() -> str:
    """Return the currently active language code.

    Returns:
        The two-letter language code currently in use (e.g. 'es', 'ca').
    """
    return _current_lang


def t(key: str, **kwargs) -> str:
    """Translate a UI string key to the current language.

    Looks up *key* in the active language's string dictionary. Falls back
    to the Spanish dictionary if the key is missing in the current language
    (so new strings added in Spanish are visible in all languages until they
    are translated). Falls back to the raw key string if not found anywhere,
    so missing translations are visible but do not crash the app.

    Supports Python str.format()-style interpolation: pass keyword arguments
    to substitute placeholders in the translated string (e.g.
    t('send_progress', current=3, total=10)).

    Args:
        key: String key defined in the locale dictionaries.
        **kwargs: Optional placeholder values for str.format() substitution.

    Returns:
        The translated and interpolated string for the active language.
    """
    strings = LANGUAGES[_current_lang][1]
    # Spanish is the fallback for keys not yet translated in the active language
    text = strings.get(key, LANGUAGES["es"][1].get(key, key))
    return text.format(**kwargs) if kwargs else text


def language_names() -> dict[str, str]:
    """Return a mapping of language codes to their display names.

    Used to populate language selector UI elements with human-readable
    names like 'Español', 'Català', etc.

    Returns:
        Dictionary mapping each supported language code to its display name.
    """
    return {code: name for code, (name, _) in LANGUAGES.items()}
