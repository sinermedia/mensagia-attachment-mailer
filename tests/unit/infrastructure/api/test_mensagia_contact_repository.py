from unittest.mock import MagicMock

from src.domain.entities.contact import Contact
from src.infrastructure.api.mensagia_contact_repository import MensagiaContactRepository


def _repository(raw: list) -> MensagiaContactRepository:
    """Build a repository over a client mock returning *raw* contacts."""
    client = MagicMock()
    client.get_contacts.return_value = raw
    return MensagiaContactRepository(client)


class TestMensagiaContactRepository:
    """Covers turning the contacts returned by the API into Contact objects."""

    def test_maps_the_basic_fields_and_the_custom_ones(self):
        """Reads the ID, name, email, phone number and custom fields of each contact."""
        raw = [{"id": 7, "name": "Ana", "email": "ana@x.com", "number": "34600000000",
                "extra_fields": {"cliente": "ACME"}}]
        assert _repository(raw).get_by_group(1) == [
            Contact(id=7, name="Ana", email="ana@x.com", number="34600000000", extra_fields={"cliente": "ACME"})
        ]

    def test_missing_values_become_empty(self):
        """Turns missing or null values into empty ones."""
        raw = [{"id": 7, "name": None, "email": None, "number": None, "extra_fields": None}]
        contact = _repository(raw).get_by_group(1)[0]
        assert (contact.name, contact.email, contact.number, contact.extra_fields) == ("", "", "", {})

    def test_a_numeric_phone_number_is_read_as_text(self):
        """Writes a phone number the API returns as a number as text."""
        contact = _repository([{"id": 7, "number": 34600000000}]).get_by_group(1)[0]
        assert contact.number == "34600000000"
