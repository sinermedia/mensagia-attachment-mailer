import pytest
from src.domain.subject_fields import (
    SubjectFieldError, SubjectTemplate, clean_field_value, subject_placeholder, subject_placeholders,
)


class TestSubjectPlaceholders:
    """Covers finding the #name# fields written in a subject."""

    def test_finds_a_field(self):
        """Finds the name written between two # signs."""
        assert subject_placeholders("#Asunto#") == ["Asunto"]

    def test_finds_several_fields_in_order(self):
        """Finds every field of a subject that mixes text and fields, in order."""
        assert subject_placeholders("Factura #num_factura# - #cliente#") == ["num_factura", "cliente"]

    def test_a_field_used_twice_is_listed_once(self):
        """Lists a field repeated in the subject only once."""
        assert subject_placeholders("#a# y #a#") == ["a"]

    def test_text_with_spaces_between_signs_is_not_a_field(self):
        """Does not take text with spaces between two # signs as a field."""
        assert subject_placeholders("Pedido #12 y #34") == []

    @pytest.mark.parametrize("subject", ["Sin campos", "", "## vacío", "Solo #uno"])
    def test_subjects_without_fields(self, subject):
        """Finds no field in a subject without a complete #name#."""
        assert subject_placeholders(subject) == []


class TestSubjectPlaceholder:
    """Covers how a field or column name is written in the subject."""

    def test_spaces_become_underscores(self):
        """Writes the spaces of a name as underscores."""
        assert subject_placeholder("num factura") == "#num_factura#"

    def test_keeps_the_case(self):
        """Keeps the name's case, which the match ignores anyway."""
        assert subject_placeholder("Cliente") == "#Cliente#"

    @pytest.mark.parametrize("name", ["con#almohadilla", "dos\tpartes", "", "   "])
    def test_names_that_cannot_be_written(self, name):
        """Returns None for a name that cannot be written between # signs."""
        assert subject_placeholder(name) is None


class TestCleanFieldValue:
    """Covers how a field value is put into the subject."""

    def test_strips_surrounding_spaces(self):
        """Removes the spaces at both ends."""
        assert clean_field_value("  ACME  ") == "ACME"

    def test_line_breaks_become_spaces(self):
        """Turns line breaks, of any kind, into single spaces."""
        assert clean_field_value("Línea 1\r\nLínea 2\nLínea 3") == "Línea 1 Línea 2 Línea 3"


class TestSubjectTemplateBind:
    """Covers matching the fields of a subject with the available field or column names."""

    def test_matches_a_name_ignoring_case_and_spaces(self):
        """Matches #num_factura# with a column named 'Num Factura'."""
        template = SubjectTemplate.bind("Factura #num_factura#", ["Correo", "Num Factura"])
        assert template.fields == {"num_factura": "Num Factura"}

    def test_matches_an_exact_name(self):
        """Matches a field written exactly as its name."""
        assert SubjectTemplate.bind("#Asunto#", ["Asunto"]).fields == {"Asunto": "Asunto"}

    def test_a_subject_without_fields_needs_no_names(self):
        """Accepts a subject without fields whatever names are available."""
        template = SubjectTemplate.bind("Tu factura", [])
        assert template.fields == {} and not template.has_fields

    def test_reports_unknown_names(self):
        """Reports every field of the subject that matches no name."""
        with pytest.raises(SubjectFieldError) as error:
            SubjectTemplate.bind("#num_factur# #cliente# #fecha#", ["cliente"])
        assert error.value.unknown == ["num_factur", "fecha"]
        assert error.value.ambiguous == {}

    def test_reports_ambiguous_names(self):
        """Reports a field that matches more than one name, with the names it matches."""
        with pytest.raises(SubjectFieldError) as error:
            SubjectTemplate.bind("#num_factura#", ["num factura", "NUM_FACTURA", "otra"])
        assert error.value.ambiguous == {"num_factura": ["num factura", "NUM_FACTURA"]}
        assert error.value.unknown == []

    def test_ambiguous_names_not_used_are_fine(self):
        """Accepts names that would be ambiguous when the subject does not use them."""
        assert SubjectTemplate.bind("#cliente#", ["num factura", "num_factura", "cliente"]).has_fields

    def test_names_used_by_the_subject(self):
        """Lists the field or column names the subject needs, once each."""
        template = SubjectTemplate.bind("#Cliente# #cliente# #num#", ["cliente", "num"])
        assert template.names == ["cliente", "num"]


class TestSubjectTemplateRender:
    """Covers building the final subject of each recipient."""

    def test_replaces_the_fields_with_the_values(self):
        """Writes each value in place of its field."""
        template = SubjectTemplate.bind("Factura #num_factura# - #cliente#", ["num factura", "cliente"])
        assert template.render({"num factura": "123", "cliente": "ACME"}) == ("Factura 123 - ACME", None)

    def test_cleans_the_values(self):
        """Strips the values and turns their line breaks into spaces."""
        template = SubjectTemplate.bind("#asunto#", ["asunto"])
        assert template.render({"asunto": "  Hola\nmundo "}) == ("Hola mundo", None)

    def test_reports_the_first_empty_field(self):
        """Names the first field whose value is empty, so the recipient can be skipped."""
        template = SubjectTemplate.bind("#a# #b# #c#", ["a", "b", "c"])
        assert template.render({"a": "1", "b": "  ", "c": ""}) == (None, "b")

    def test_a_missing_value_is_empty(self):
        """Treats a value the recipient does not have as empty."""
        template = SubjectTemplate.bind("#a#", ["a"])
        assert template.render({}) == (None, "a")

    def test_leaves_other_text_alone(self):
        """Keeps the text that is not a field, # signs included."""
        template = SubjectTemplate.bind("Pedido #12 y #a#", ["a"])
        assert template.render({"a": "X"}) == ("Pedido #12 y X", None)

    def test_a_subject_without_fields_is_kept(self):
        """Returns a subject without fields unchanged."""
        assert SubjectTemplate.bind("Tu factura", []).render({}) == ("Tu factura", None)
