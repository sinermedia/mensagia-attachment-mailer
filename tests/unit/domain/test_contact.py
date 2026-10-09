from src.domain.entities.contact import SUBJECT_BASIC_FIELDS, Contact


class TestContactSubjectValues:
    """Covers the values of a contact that a subject can use."""

    def test_basic_fields_are_email_name_and_number(self):
        """Offers the basic fields Mensagia lets a message use, by their #name#."""
        assert SUBJECT_BASIC_FIELDS == ("email", "name", "number")

    def test_holds_the_basic_and_the_custom_fields(self):
        """Gives the email, name, phone number and every custom field, as text."""
        contact = Contact(id=1, name="Ana", email="ana@x.com", number="34600000000",
                          extra_fields={"cliente": "ACME", "importe": 12, "vacio": None})
        assert contact.subject_values() == {
            "email": "ana@x.com", "name": "Ana", "number": "34600000000",
            "cliente": "ACME", "importe": "12", "vacio": "",
        }
