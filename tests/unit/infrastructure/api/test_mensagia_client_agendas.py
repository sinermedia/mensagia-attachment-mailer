from unittest.mock import patch
from src.infrastructure.api.mensagia_client import MensagiaClient


class TestGetAgendasPage:
    """Covers the single-page agenda request used by the group selection step."""

    def test_requests_one_page_without_following_pagination(self):
        """Performs exactly one GET request regardless of how many pages exist."""
        client = MensagiaClient("token")
        with patch.object(client, "_get", return_value={"data": []}) as mock_get:
            client.get_agendas_page()

        mock_get.assert_called_once()

    def test_sends_the_pagination_arguments(self):
        """Sends the requested page number and page size to the API."""
        client = MensagiaClient("token")
        with patch.object(client, "_get", return_value={"data": []}) as mock_get:
            client.get_agendas_page(page=3, per_page=25)

        assert mock_get.call_args[0][0] == "agendas"
        assert mock_get.call_args[0][1]["page"] == 3
        assert mock_get.call_args[0][1]["per_page"] == 25

    def test_sends_a_contains_search_when_a_name_is_given(self):
        """Adds the name filter and a 'contains' search type when a name is given."""
        client = MensagiaClient("token")
        with patch.object(client, "_get", return_value={"data": []}) as mock_get:
            client.get_agendas_page(name="barcelona")

        params = mock_get.call_args[0][1]
        assert params["name"] == "barcelona"
        assert params["search_type"] == "contains"

    def test_omits_the_name_filter_when_no_name_is_given(self):
        """Leaves the name filter out entirely when searching for everything."""
        client = MensagiaClient("token")
        with patch.object(client, "_get", return_value={"data": []}) as mock_get:
            client.get_agendas_page()

        params = mock_get.call_args[0][1]
        assert "name" not in params
        assert "search_type" not in params

    def test_ignores_a_blank_name(self):
        """Treats a whitespace-only name as no filter at all."""
        client = MensagiaClient("token")
        with patch.object(client, "_get", return_value={"data": []}) as mock_get:
            client.get_agendas_page(name="   ")

        assert "name" not in mock_get.call_args[0][1]

    def test_returns_the_parsed_response_untouched(self):
        """Returns the parsed response body so the caller can read its metadata."""
        body = {"data": [{"id": 1}], "meta": {"pagination": {"total": 1}}}
        client = MensagiaClient("token")
        with patch.object(client, "_get", return_value=body):
            assert client.get_agendas_page() == body
