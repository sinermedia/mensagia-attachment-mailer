from unittest.mock import patch
import pytest
from src.infrastructure.ui.console import console_app
from src.infrastructure.ui.i18n import set_language


@pytest.fixture(autouse=True)
def _english_ui():
    """Pin the UI language so the accepted answers are deterministic."""
    set_language("en")


class TestConsoleSendAction:
    """Covers the final console question: send, simulate or cancel, and simulate-only when nothing can be sent."""

    def test_offers_send_simulate_or_cancel_when_there_is_something_to_send(self):
        """Accepts a real send when at least one contact can be sent to."""
        with patch("builtins.input", return_value="yes"):
            assert console_app._choose_action(can_send=True) == "send"

    def test_accepts_a_simulation_when_there_is_something_to_send(self):
        """Accepts a simulation when at least one contact can be sent to."""
        with patch("builtins.input", return_value="sim"):
            assert console_app._choose_action(can_send=True) == "dry_run"

    def test_a_yes_means_simulate_when_nothing_can_be_sent(self):
        """Turns a yes into a simulation when no contact can be sent to."""
        with patch("builtins.input", return_value="yes"):
            assert console_app._choose_action(can_send=False) == "dry_run"

    def test_a_no_cancels_when_nothing_can_be_sent(self):
        """Cancels when the user declines the simulation and no contact can be sent to."""
        with patch("builtins.input", return_value="no"):
            assert console_app._choose_action(can_send=False) is None

    def test_asks_only_about_simulating_when_nothing_can_be_sent(self):
        """Asks a simulate-only question that never offers a real send."""
        with patch("builtins.input", return_value="no") as fake_input:
            console_app._choose_action(can_send=False)

        assert "simulat" in fake_input.call_args[0][0].lower()
