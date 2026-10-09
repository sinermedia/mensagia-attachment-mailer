import pytest


@pytest.fixture(autouse=True)
def _no_update_check(monkeypatch):
    """Keep every test away from GitHub when the app starts.

    The windows and console flows built by the tests check for a new
    version on start-up, and a MENSAGIA_APP_VERSION in the developer's .env
    would make them query GitHub for real. A variable already in the
    environment wins over the .env file, so this turns the check off; the
    tests of the check itself patch its settings directly.
    """
    monkeypatch.setenv("MENSAGIA_CHECK_UPDATES", "false")
