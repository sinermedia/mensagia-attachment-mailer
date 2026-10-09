from unittest.mock import patch

import pytest

from src.infrastructure.ui.console import console_app
from src.infrastructure.ui.i18n import set_language


@pytest.fixture(autouse=True)
def _english_ui():
    """Pin the UI language so assertions on printed text are deterministic."""
    set_language("en")


def write_csv(path, text: str) -> str:
    """Write a UTF-8 .csv file and return its path as text."""
    path.write_bytes(text.encode("utf-8"))
    return str(path)


class TestConsoleBindSubject:
    """Covers matching the subject fields with the names of the source in the console."""

    def test_a_known_field_is_bound_without_asking(self):
        """Returns the bound subject at once when every field matches a name."""
        with patch("builtins.input") as fake_input:
            template = console_app._bind_subject("Factura #num_factura#", ["num factura"], rows=False)
        fake_input.assert_not_called()
        assert template.fields == {"num_factura": "num factura"}

    def test_an_unknown_field_asks_for_the_subject_again(self, capsys):
        """Explains the problem, lists the usable names and asks for a new subject."""
        with patch("builtins.input", side_effect=["", "Factura #cliente#"]):
            template = console_app._bind_subject("Factura #num_factur#", ["Cliente", "num factura"], rows=False)
        out = capsys.readouterr().out
        assert "#num_factur#, which match no custom field" in out
        assert "num factura → #num_factura#" in out
        assert "Type the subject again." in out
        assert template.text == "Factura #cliente#"

    def test_a_file_names_its_columns(self, capsys):
        """Speaks of columns when the names come from a file."""
        with patch("builtins.input", side_effect=["Hola"]):
            console_app._bind_subject("#x#", ["Correo"], rows=True)
        out = capsys.readouterr().out
        assert "match no column of the file" in out
        assert "Columns you can use in the subject:" in out


class TestConsoleSubjectHint:
    """Covers explaining the #name# notation before asking for the subject."""

    def test_the_hint_is_printed_before_the_subject(self, capsys):
        """Prints the help text about fields, then reads the subject."""
        with patch("builtins.input", side_effect=["", "Hola"]):
            assert console_app._ask_subject() == "Hola"
        assert "between # signs, without spaces" in capsys.readouterr().out


class TestConsoleFileSubject:
    """Covers binding the subject to the columns of the chosen file."""

    def test_the_file_source_gets_the_bound_subject(self, tmp_path):
        """Binds the subject to the file's columns and hands it to the source."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto;Num factura\na@x.com;a.pdf;1\n")
        with patch("builtins.input", side_effect=[path, "1", "1"]):
            source = console_app._select_file(subject="Factura #num_factura#")
        assert source.subject.fields == {"num_factura": "Num factura"}
        assert source.get_recipients()[0].subject == "Factura 1"
