from unittest.mock import patch
from src.infrastructure.config import app_version
from src.infrastructure.config.app_version import DEV_VERSION, current_version


class TestCurrentVersion:
    """Covers which version number the running application reports."""

    def test_a_tagged_build_reports_its_tag(self):
        """Reports the version written by the build workflow."""
        with patch.object(app_version, "_built_version", return_value="v1.4.0"):
            assert current_version() == "v1.4.0"

    def test_source_code_reports_dev(self):
        """Reports the development version when no build wrote a version."""
        with patch.object(app_version, "_built_version", return_value=None):
            assert current_version() == DEV_VERSION == "dev"
