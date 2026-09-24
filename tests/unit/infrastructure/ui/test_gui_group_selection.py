import time
from unittest.mock import MagicMock, patch
import pytest
from src.domain.entities.agenda import Agenda, AgendaPage
from src.infrastructure.ui.i18n import set_language


def _tk_available() -> bool:
    """Report whether a Tk window can be created in this environment.

    Returns:
        True if Tk initialises, False on machines without a usable display.
    """
    try:
        import customtkinter as ctk
        root = ctk.CTk()
        root.withdraw()
        root.destroy()
        return True
    except Exception:
        return False


# The whole module drives a real window, which is not available everywhere
pytestmark = pytest.mark.skipif(not _tk_available(), reason="Tk is not available")


@pytest.fixture
def app():
    """Create a hidden App window and destroy it once the test finishes.

    Yields:
        An App instance sitting on the token step, ready to be driven.
    """
    set_language("en")
    from src.infrastructure.ui.gui.gui_app import App
    window = App()
    window.withdraw()
    yield window
    window.destroy()


def _wait_until(window, predicate, timeout: float = 5.0) -> bool:
    """Pump the Tk event loop until *predicate* holds or the timeout expires.

    The group listing is populated from a background thread, so the test has
    to keep the event loop alive while waiting for it.

    Args:
        window: The App instance whose event loop should be pumped.
        predicate: Zero-argument callable returning the condition to wait for.
        timeout: Maximum number of seconds to wait.

    Returns:
        True if the predicate held before the timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        window.update()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def _radio_buttons(window) -> list:
    """Collect the group radio buttons currently in the listing.

    Args:
        window: The App instance to inspect.

    Returns:
        The child widgets of the group list, in display order.
    """
    return list(window._group_list.winfo_children())


class TestGuiGroupListing:
    """Covers the paged, searchable group listing of the GUI wizard."""

    def test_requests_a_single_page(self, app):
        """Fetches one page of groups instead of every group of the account."""
        repo = MagicMock()
        repo.search.return_value = AgendaPage([Agenda(id=1, name="A", total_users=3)], total=3241)
        with patch("src.infrastructure.ui.gui.gui_app.MensagiaAgendaRepository", return_value=repo):
            app._search_groups()
            _wait_until(app, lambda: len(_radio_buttons(app)) == 1)

        repo.search.assert_called_once_with(name="")

    def test_reports_the_total_number_of_matches(self, app):
        """Shows how many groups exist beyond the ones listed."""
        repo = MagicMock()
        repo.search.return_value = AgendaPage([Agenda(id=1, name="A", total_users=3)], total=3241)
        with patch("src.infrastructure.ui.gui.gui_app.MensagiaAgendaRepository", return_value=repo):
            app._search_groups()
            _wait_until(app, lambda: "3241" in app._group_count.cget("text"))

        assert "3241" in app._group_count.cget("text")

    def test_disables_groups_without_contacts(self, app):
        """Renders a group with no contacts as an unselectable entry."""
        repo = MagicMock()
        repo.search.return_value = AgendaPage(
            [Agenda(id=1, name="Empty", total_users=0), Agenda(id=2, name="Full", total_users=4)],
            total=2,
        )
        with patch("src.infrastructure.ui.gui.gui_app.MensagiaAgendaRepository", return_value=repo):
            app._search_groups()
            _wait_until(app, lambda: len(_radio_buttons(app)) == 2)

        empty, full = _radio_buttons(app)
        assert str(empty.cget("state")) == "disabled"
        assert str(full.cget("state")) == "normal"

    def test_keeps_empty_groups_visible(self, app):
        """Still lists groups without contacts so they can be found."""
        repo = MagicMock()
        repo.search.return_value = AgendaPage([Agenda(id=1, name="Empty", total_users=0)], total=1)
        with patch("src.infrastructure.ui.gui.gui_app.MensagiaAgendaRepository", return_value=repo):
            app._search_groups()
            _wait_until(app, lambda: len(_radio_buttons(app)) == 1)

        assert "Empty" in _radio_buttons(app)[0].cget("text")

    def test_sends_the_search_text_as_a_name_filter(self, app):
        """Passes what the user typed to the repository as a name filter."""
        repo = MagicMock()
        repo.search.return_value = AgendaPage([Agenda(id=9, name="Barcelona", total_users=7)], total=1)
        with patch("src.infrastructure.ui.gui.gui_app.MensagiaAgendaRepository", return_value=repo):
            app._group_search.insert(0, "barcelona")
            app._search_groups()
            _wait_until(app, lambda: len(_radio_buttons(app)) == 1)

        repo.search.assert_called_once_with(name="barcelona")

    def test_search_results_replace_the_previous_listing(self, app):
        """Drops the earlier entries when a search returns different groups."""
        repo = MagicMock()
        repo.search.side_effect = [
            AgendaPage([Agenda(id=1, name="Madrid", total_users=3)], total=3241),
            AgendaPage([Agenda(id=9, name="Barcelona", total_users=7)], total=1),
        ]
        with patch("src.infrastructure.ui.gui.gui_app.MensagiaAgendaRepository", return_value=repo):
            app._search_groups()
            _wait_until(app, lambda: len(_radio_buttons(app)) == 1)
            app._group_search.insert(0, "barcelona")
            app._search_groups()
            _wait_until(
                app,
                lambda: bool(_radio_buttons(app))
                and "Barcelona" in _radio_buttons(app)[0].cget("text"),
            )

        texts = [w.cget("text") for w in _radio_buttons(app)]
        assert not any("Madrid" in text for text in texts)

    def test_reports_a_search_with_no_matches(self, app):
        """Tells the user when no group matches the search."""
        repo = MagicMock()
        repo.search.return_value = AgendaPage([], total=0)
        with patch("src.infrastructure.ui.gui.gui_app.MensagiaAgendaRepository", return_value=repo):
            app._group_search.insert(0, "zzz")
            app._search_groups()
            _wait_until(app, lambda: "No group" in app._group_error.cget("text"))

        assert "No group" in app._group_error.cget("text")


class TestGuiSummaryGuards:
    """Covers the summary step refusing to start a send with no recipients."""

    def _prepare(self, window):
        """Fill in the wizard selections the summary step depends on.

        Args:
            window: The App instance to prepare.
        """
        window.selected_agenda = Agenda(id=1, name="Group", total_users=5)
        window.selected_template = MagicMock(id=10, name="Template")
        window.selected_sender = MagicMock(id=20, name="Sender", email="from@example.com")
        window.selected_field = MagicMock(id=30)
        window.selected_field.name = "attachment"
        window._subject_entry.insert(0, "Subject")

    def test_disables_the_send_actions_when_no_contact_is_eligible(self, app):
        """Leaves both send buttons disabled when no contact can be written to."""
        self._prepare(app)
        repo = MagicMock()
        repo.get_by_group.return_value = [MagicMock(email="", extra_fields={})]
        with patch("src.infrastructure.ui.gui.gui_app.MensagiaContactRepository", return_value=repo):
            app._load_summary()
            _wait_until(app, lambda: app._summary_error.cget("text") != "")

        assert str(app._send_btn.cget("state")) == "disabled"
        assert str(app._dry_run_btn.cget("state")) == "disabled"

    def test_explains_why_the_send_cannot_start(self, app):
        """States that no contact of the group can receive the send."""
        self._prepare(app)
        repo = MagicMock()
        repo.get_by_group.return_value = [MagicMock(email="", extra_fields={})]
        with patch("src.infrastructure.ui.gui.gui_app.MensagiaContactRepository", return_value=repo):
            app._load_summary()
            _wait_until(app, lambda: app._summary_error.cget("text") != "")

        assert "No contact in this group" in app._summary_error.cget("text")

    def test_enables_the_send_actions_when_contacts_are_eligible(self, app):
        """Re-enables both send buttons once the group yields recipients."""
        self._prepare(app)
        repo = MagicMock()
        repo.get_by_group.return_value = [
            MagicMock(email="a@example.com", extra_fields={"attachment": "file.pdf"})
        ]
        with patch("src.infrastructure.ui.gui.gui_app.MensagiaContactRepository", return_value=repo):
            app._load_summary()
            _wait_until(app, lambda: str(app._send_btn.cget("state")) == "normal")

        assert str(app._send_btn.cget("state")) == "normal"
        assert app._summary_error.cget("text") == ""

    def test_reports_an_api_failure_without_a_modal_dialog(self, app):
        """Shows an API failure inline so the Back button stays reachable."""
        from src.infrastructure.api.mensagia_client import MensagiaAPIError

        self._prepare(app)
        repo = MagicMock()
        repo.get_by_group.side_effect = MensagiaAPIError("boom")
        with patch("src.infrastructure.ui.gui.gui_app.MensagiaContactRepository", return_value=repo):
            app._load_summary()
            _wait_until(app, lambda: app._summary_error.cget("text") != "")

        assert "boom" in app._summary_error.cget("text")
        assert str(app._send_btn.cget("state")) == "disabled"


class TestGuiSendFailure:
    """Covers the sending step always offering a way back after a failure."""

    def test_offers_a_way_back_when_the_send_fails(self, app):
        """Adds a button to return to the summary when a send fails."""
        app._fail_send("something went wrong")

        actions = app._sending_actions.winfo_children()
        assert len(actions) == 1
        assert "something went wrong" in app._result_label.cget("text")
