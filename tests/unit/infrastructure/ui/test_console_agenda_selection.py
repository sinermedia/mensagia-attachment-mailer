from unittest.mock import MagicMock, patch
import pytest
from src.domain.entities.agenda import Agenda, AgendaPage
from src.infrastructure.ui.console import console_app
from src.infrastructure.ui.i18n import set_language


@pytest.fixture(autouse=True)
def _english_ui():
    """Pin the UI language so assertions on printed text are deterministic."""
    set_language("en")


def _page(*agendas: Agenda, total: int = None) -> AgendaPage:
    """Build an AgendaPage for the given agendas.

    Args:
        agendas: Agenda entities to place in the page.
        total: Overall match count. Defaults to the number of agendas.

    Returns:
        An AgendaPage ready to be returned by a stubbed repository.
    """
    return AgendaPage(agendas=list(agendas), total=len(agendas) if total is None else total)


class TestConsoleAgendaSelection:
    """Covers the console group selector: paged listing, search and empty groups."""

    def test_returns_the_agenda_matching_the_entered_number(self):
        """Returns the agenda whose position number the user typed."""
        repo = MagicMock()
        repo.search.return_value = _page(
            Agenda(id=1, name="A", total_users=5), Agenda(id=2, name="B", total_users=9)
        )
        with patch.object(console_app, "MensagiaAgendaRepository", return_value=repo), \
             patch("builtins.input", side_effect=["2"]):
            selected = console_app._select_agenda(MagicMock(), show_ids=False)

        assert selected.id == 2

    def test_loads_a_single_page_on_entry(self):
        """Requests only the first page instead of every agenda of the account."""
        repo = MagicMock()
        repo.search.return_value = _page(Agenda(id=1, name="A", total_users=5), total=3241)
        with patch.object(console_app, "MensagiaAgendaRepository", return_value=repo), \
             patch("builtins.input", side_effect=["1"]):
            console_app._select_agenda(MagicMock(), show_ids=False)

        repo.search.assert_called_once_with()

    def test_treats_non_numeric_input_as_a_search(self):
        """Searches by name when the input is not a number."""
        repo = MagicMock()
        repo.search.side_effect = [
            _page(Agenda(id=1, name="Madrid", total_users=5), total=3241),
            _page(Agenda(id=9, name="Barcelona", total_users=7)),
        ]
        with patch.object(console_app, "MensagiaAgendaRepository", return_value=repo), \
             patch("builtins.input", side_effect=["barcelona", "1"]):
            selected = console_app._select_agenda(MagicMock(), show_ids=False)

        assert selected.id == 9
        assert repo.search.call_args_list[1].kwargs == {"name": "barcelona"}

    def test_treats_an_out_of_range_number_as_a_search(self):
        """Searches by name when the number typed is outside the listed range."""
        repo = MagicMock()
        repo.search.side_effect = [
            _page(Agenda(id=1, name="A", total_users=5)),
            _page(Agenda(id=42, name="Group 2024", total_users=3)),
        ]
        with patch.object(console_app, "MensagiaAgendaRepository", return_value=repo), \
             patch("builtins.input", side_effect=["2024", "1"]):
            selected = console_app._select_agenda(MagicMock(), show_ids=False)

        assert selected.id == 42
        assert repo.search.call_args_list[1].kwargs == {"name": "2024"}

    def test_replaces_the_previous_listing_with_the_search_results(self, capsys):
        """Shows only the search results after a search, not the earlier listing."""
        repo = MagicMock()
        repo.search.side_effect = [
            _page(Agenda(id=1, name="Madrid", total_users=5)),
            _page(Agenda(id=9, name="Barcelona", total_users=7)),
        ]
        with patch.object(console_app, "MensagiaAgendaRepository", return_value=repo), \
             patch("builtins.input", side_effect=["barcelona", "1"]):
            console_app._select_agenda(MagicMock(), show_ids=False)

        # Everything printed after the search results appear must belong to the
        # new listing, so the entries of the first listing cannot linger there
        last_listing = capsys.readouterr().out.rsplit("Barcelona", 1)[1]
        assert "Madrid" not in last_listing

    def test_refuses_to_select_an_agenda_without_contacts(self):
        """Rejects an empty agenda and keeps asking instead of returning it."""
        repo = MagicMock()
        repo.search.return_value = _page(
            Agenda(id=1, name="Empty", total_users=0), Agenda(id=2, name="Full", total_users=4)
        )
        with patch.object(console_app, "MensagiaAgendaRepository", return_value=repo), \
             patch("builtins.input", side_effect=["1", "2"]):
            selected = console_app._select_agenda(MagicMock(), show_ids=False)

        assert selected.id == 2

    def test_warns_when_an_empty_agenda_is_chosen(self, capsys):
        """Explains why an empty agenda cannot be selected."""
        repo = MagicMock()
        repo.search.return_value = _page(
            Agenda(id=1, name="Empty", total_users=0), Agenda(id=2, name="Full", total_users=4)
        )
        with patch.object(console_app, "MensagiaAgendaRepository", return_value=repo), \
             patch("builtins.input", side_effect=["1", "2"]):
            console_app._select_agenda(MagicMock(), show_ids=False)

        assert "no contacts" in capsys.readouterr().out

    def test_lists_empty_agendas_so_the_user_can_see_them(self, capsys):
        """Keeps agendas without contacts visible in the listing."""
        repo = MagicMock()
        repo.search.return_value = _page(
            Agenda(id=1, name="Empty", total_users=0), Agenda(id=2, name="Full", total_users=4)
        )
        with patch.object(console_app, "MensagiaAgendaRepository", return_value=repo), \
             patch("builtins.input", side_effect=["2"]):
            console_app._select_agenda(MagicMock(), show_ids=False)

        assert "Empty" in capsys.readouterr().out

    def test_reports_how_many_agendas_were_left_out(self, capsys):
        """Tells the user how many matches exist beyond the ones listed."""
        repo = MagicMock()
        repo.search.return_value = _page(Agenda(id=1, name="A", total_users=5), total=3241)
        with patch.object(console_app, "MensagiaAgendaRepository", return_value=repo), \
             patch("builtins.input", side_effect=["1"]):
            console_app._select_agenda(MagicMock(), show_ids=False)

        assert "3241" in capsys.readouterr().out

    def test_blank_input_does_not_trigger_a_search(self):
        """Re-prompts without querying the API when the input is empty."""
        repo = MagicMock()
        repo.search.return_value = _page(Agenda(id=1, name="A", total_users=5))
        with patch.object(console_app, "MensagiaAgendaRepository", return_value=repo), \
             patch("builtins.input", side_effect=["", "   ", "1"]):
            console_app._select_agenda(MagicMock(), show_ids=False)

        repo.search.assert_called_once_with()

    def test_allows_searching_again_when_nothing_matched(self):
        """Keeps accepting searches after one that returned no results."""
        repo = MagicMock()
        repo.search.side_effect = [
            _page(Agenda(id=1, name="A", total_users=5)),
            _page(),
            _page(Agenda(id=3, name="Found", total_users=2)),
        ]
        with patch.object(console_app, "MensagiaAgendaRepository", return_value=repo), \
             patch("builtins.input", side_effect=["zzz", "found", "1"]):
            selected = console_app._select_agenda(MagicMock(), show_ids=False)

        assert selected.id == 3

    def test_shows_agenda_ids_when_enabled(self, capsys):
        """Prefixes each entry with the agenda id when the show_ids option is on."""
        repo = MagicMock()
        repo.search.return_value = _page(Agenda(id=77, name="A", total_users=5))
        with patch.object(console_app, "MensagiaAgendaRepository", return_value=repo), \
             patch("builtins.input", side_effect=["1"]):
            console_app._select_agenda(MagicMock(), show_ids=True)

        assert "[77]" in capsys.readouterr().out
