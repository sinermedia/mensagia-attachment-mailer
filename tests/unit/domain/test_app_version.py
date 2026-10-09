import pytest
from src.domain.app_version import is_newer, parse_version


class TestParseVersion:
    """Covers reading a release number such as v1.4.0 into comparable parts."""

    def test_reads_a_tag(self):
        """Reads the three numbers of a vX.Y.Z tag."""
        assert parse_version("v1.4.0") == (1, 4, 0)

    def test_reads_a_number_without_the_v(self):
        """Reads a version written without the leading v."""
        assert parse_version("1.12.3") == (1, 12, 3)

    def test_ignores_surrounding_spaces(self):
        """Ignores spaces around the version, as typed in a .env file."""
        assert parse_version("  v2.0.1 ") == (2, 0, 1)

    @pytest.mark.parametrize("text", ["dev", "", None, "v1.4", "v1.4.0.1", "v1.5.0-rc1", "version 1.4.0", "v1.a.0"])
    def test_rejects_anything_else(self, text):
        """Returns None for text that is not a plain three-number version."""
        assert parse_version(text) is None


class TestIsNewer:
    """Covers deciding whether a published release is newer than the running one."""

    def test_a_higher_patch_is_newer(self):
        """Reports a release with a higher last number as newer."""
        assert is_newer("v1.3.1", "v1.3.0") is True

    def test_compares_numbers_not_text(self):
        """Compares each part as a number, so v1.10.0 is newer than v1.9.0."""
        assert is_newer("v1.10.0", "v1.9.0") is True

    def test_the_same_version_is_not_newer(self):
        """Does not report the running version itself as newer."""
        assert is_newer("v1.4.0", "v1.4.0") is False

    def test_an_older_release_is_not_newer(self):
        """Does not report an older release as newer."""
        assert is_newer("v1.3.1", "v1.4.0") is False

    @pytest.mark.parametrize("latest, current", [("v1.5.0", "dev"), (None, "v1.4.0"), ("latest", "v1.4.0")])
    def test_unreadable_versions_are_never_newer(self, latest, current):
        """Never reports a newer version when either side cannot be read."""
        assert is_newer(latest, current) is False
