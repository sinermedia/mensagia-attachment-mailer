from unittest.mock import MagicMock
from src.infrastructure.api.mensagia_agenda_repository import MensagiaAgendaRepository


def _response(items: list, total: int) -> dict:
    """Build a Mensagia API response body for the agendas endpoint.

    Args:
        items: Raw agenda dictionaries to place in the data section.
        total: Total number of matches reported by the pagination metadata.

    Returns:
        A dictionary shaped like a real /agendas response.
    """
    return {"data": items, "meta": {"pagination": {"total": total}}}


class TestMensagiaAgendaRepositorySearch:
    """Covers the paginated, name-filtered agenda search against the Mensagia API."""

    def test_maps_raw_items_to_domain_agendas(self):
        """Converts each raw API dictionary into an Agenda entity."""
        client = MagicMock()
        client.get_agendas_page.return_value = _response(
            [{"id": 7, "name": "Clients", "total_users": 12}], total=1
        )

        page = MensagiaAgendaRepository(client).search()

        assert len(page.agendas) == 1
        assert page.agendas[0].id == 7
        assert page.agendas[0].name == "Clients"
        assert page.agendas[0].total_users == 12

    def test_defaults_total_users_to_zero_when_absent(self):
        """Falls back to zero contacts when the API omits total_users."""
        client = MagicMock()
        client.get_agendas_page.return_value = _response([{"id": 7, "name": "Clients"}], total=1)

        page = MensagiaAgendaRepository(client).search()

        assert page.agendas[0].total_users == 0

    def test_reads_the_total_from_pagination_metadata(self):
        """Takes the overall match count from meta.pagination.total."""
        client = MagicMock()
        client.get_agendas_page.return_value = _response([{"id": 1, "name": "A"}], total=3241)

        page = MensagiaAgendaRepository(client).search()

        assert page.total == 3241

    def test_falls_back_to_item_count_when_metadata_is_missing(self):
        """Uses the number of returned items when pagination metadata is absent."""
        client = MagicMock()
        client.get_agendas_page.return_value = {"data": [{"id": 1, "name": "A"}]}

        page = MensagiaAgendaRepository(client).search()

        assert page.total == 1

    def test_forwards_the_search_arguments_to_the_client(self):
        """Passes the name filter and pagination arguments through to the client."""
        client = MagicMock()
        client.get_agendas_page.return_value = _response([], total=0)

        MensagiaAgendaRepository(client).search(name="barcelona", page=2, per_page=25)

        client.get_agendas_page.assert_called_once_with(name="barcelona", page=2, per_page=25)

    def test_requests_a_single_page_of_ten_by_default(self):
        """Requests only the first ten agendas when no arguments are given."""
        client = MagicMock()
        client.get_agendas_page.return_value = _response([], total=0)

        MensagiaAgendaRepository(client).search()

        client.get_agendas_page.assert_called_once_with(name="", page=1, per_page=10)

    def test_returns_an_empty_page_when_nothing_matches(self):
        """Returns an empty page instead of failing when the search matches nothing."""
        client = MagicMock()
        client.get_agendas_page.return_value = _response([], total=0)

        page = MensagiaAgendaRepository(client).search(name="nonexistent")

        assert page.agendas == []
        assert page.total == 0
