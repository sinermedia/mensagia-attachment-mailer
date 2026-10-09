from unittest.mock import patch
from src.infrastructure.config import app_version
from src.infrastructure.config.app_version import DEV_VERSION, current_version


class TestCurrentVersion:
    """Covers which version number the running application reports."""

    def test_a_tagged_build_reports_its_tag(self):
        """Reports the version written by the build workflow."""
        with patch.object(app_version, "_built_version", return_value="v1.4.0"), \
                patch.object(app_version, "load_app_version_override", return_value=None):
            assert current_version() == "v1.4.0"

    def test_a_tagged_build_ignores_the_override(self):
        """Ignores MENSAGIA_APP_VERSION in a build that knows its version."""
        with patch.object(app_version, "_built_version", return_value="v1.4.0"), \
                patch.object(app_version, "load_app_version_override", return_value="v1.3.0"):
            assert current_version() == "v1.4.0"

    def test_source_code_reports_dev(self):
        """Reports the development version when no build wrote a version."""
        with patch.object(app_version, "_built_version", return_value=None), \
                patch.object(app_version, "load_app_version_override", return_value=None):
            assert current_version() == DEV_VERSION == "dev"

    def test_source_code_uses_the_override(self):
        """Reports MENSAGIA_APP_VERSION instead of dev, to try the notice from the source code."""
        with patch.object(app_version, "_built_version", return_value=None), \
                patch.object(app_version, "load_app_version_override", return_value="v1.3.0"):
            assert current_version() == "v1.3.0"

    def test_source_code_has_no_built_version(self):
        """Finds no built version in the repository, as the build file is never committed."""
        assert app_version._built_version() is None
