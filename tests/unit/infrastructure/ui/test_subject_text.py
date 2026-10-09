import pytest
from src.domain.entities.recipient import Recipient
from src.domain.subject_fields import SubjectFieldError, SubjectTemplate
from src.infrastructure.ui.i18n import set_language
from src.infrastructure.ui.subject_text import subject_error_message, subject_example_line, subject_field_lines


@pytest.fixture(autouse=True)
def english():
    """Run every test with the English texts."""
    set_language("en")


class TestSubjectFieldLines:
    """Covers the list of fields or columns that can be used in the subject."""

    def test_shows_how_to_write_each_name(self):
        """Shows each name with the way it is written in the subject."""
        assert subject_field_lines(["num factura", "Cliente"]) == ["num factura → #num_factura#", "Cliente → #Cliente#"]

    def test_leaves_out_names_that_cannot_be_written(self):
        """Leaves out the names that cannot be written between # signs."""
        assert subject_field_lines(["con#almohadilla", "ok"]) == ["ok → #ok#"]


class TestSubjectErrorMessage:
    """Covers explaining why the fields of the subject cannot be used."""

    def test_unknown_custom_fields(self):
        """Names the fields that match no custom field."""
        error = SubjectFieldError(["num_factur", "fecha"], {})
        assert subject_error_message(error, rows=False) == (
            "The subject uses #num_factur#, #fecha#, which match no custom field.")

    def test_unknown_columns(self):
        """Names the fields that match no column of the file."""
        error = SubjectFieldError(["num_factur"], {})
        assert subject_error_message(error, rows=True) == "The subject uses #num_factur#, which match no column of the file."

    def test_ambiguous_names(self):
        """Names an ambiguous field and the names it matches."""
        error = SubjectFieldError([], {"num_factura": ["num factura", "num_factura"]})
        assert subject_error_message(error, rows=True) == (
            "The subject uses #num_factura#, which matches several names: num factura, num_factura.")

    def test_every_problem_on_its_own_line(self):
        """Puts the unknown fields first and each ambiguous one on its own line."""
        error = SubjectFieldError(["x"], {"a": ["a", "A"], "b": ["b", "B"]})
        assert len(subject_error_message(error, rows=False).splitlines()) == 3


class TestSubjectExampleLine:
    """Covers the example of a final subject shown in the summary."""

    @staticmethod
    def _recipient(subject: str) -> Recipient:
        """Build a sendable recipient with its final subject."""
        return Recipient(key="1", email="a@x.com", attachment="a.pdf", subject=subject)

    def test_shows_the_subject_of_the_first_recipient(self):
        """Shows the final subject of the first recipient that will be sent."""
        template = SubjectTemplate.bind("Factura #num#", ["num"])
        line = subject_example_line(template, [self._recipient("Factura 1"), self._recipient("Factura 2")])
        assert line == "Subject example: Factura 1"

    def test_no_example_without_fields(self):
        """Shows no example when every recipient gets the same subject."""
        assert subject_example_line(SubjectTemplate.bind("Hola", []), [self._recipient("Hola")]) is None

    def test_no_example_without_recipients(self):
        """Shows no example when nobody will be sent the email."""
        assert subject_example_line(SubjectTemplate.bind("#num#", ["num"]), []) is None

    def test_no_example_without_a_template(self):
        """Shows no example when the subject was never bound."""
        assert subject_example_line(None, [self._recipient("Hola")]) is None
