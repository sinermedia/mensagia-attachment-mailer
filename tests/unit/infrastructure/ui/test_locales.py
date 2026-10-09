import re

import pytest

from src.infrastructure.ui.i18n import LANGUAGES


# Spanish is the reference language: every other one must match it
_REFERENCE = LANGUAGES["es"][1]

# Placeholders filled in by str.format(), such as {count}
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


class TestLocales:
    """Covers that every language offers the same texts as the reference one."""

    @pytest.mark.parametrize("code", [code for code in LANGUAGES if code != "es"])
    def test_same_keys_as_spanish(self, code):
        """Each language defines exactly the keys of the Spanish texts."""
        strings = LANGUAGES[code][1]
        assert set(strings) - set(_REFERENCE) == set(), "keys not in Spanish"
        assert set(_REFERENCE) - set(strings) == set(), "keys missing"

    @pytest.mark.parametrize("code", [code for code in LANGUAGES if code != "es"])
    def test_same_placeholders_as_spanish(self, code):
        """Each translation uses the same placeholders as the Spanish text, so formatting never fails."""
        strings = LANGUAGES[code][1]
        for key, text in _REFERENCE.items():
            if key in strings:
                assert set(_PLACEHOLDER.findall(strings[key])) == set(_PLACEHOLDER.findall(text)), key
