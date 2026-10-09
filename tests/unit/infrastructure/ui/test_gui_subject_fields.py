from unittest.mock import MagicMock, patch

from src.domain.entities.extra_field import ExtraField
from src.domain.scheduling import StartMode
from src.infrastructure.ui.i18n import t
# Reuse the window fixture, the event-loop helper and the Tk availability skip
from tests.unit.infrastructure.ui.test_gui_group_selection import _wait_until, app, pytestmark  # noqa: F401


def write_csv(path, text: str) -> str:
    """Write a UTF-8 .csv file and return its path as text."""
    path.write_bytes(text.encode("utf-8"))
    return str(path)


def _box_text(box) -> str:
    """Return the text of a subject fields box, without the trailing newline."""
    return box.get("1.0", "end").strip()


def _agenda_ready(window, subject: str):
    """Leave the wizard on the extra field step of an agenda send with *subject*."""
    window._subject_entry.insert(0, subject)
    window._start_mode = StartMode.NOW
    window._source_kind = "agenda"
    window.extra_fields = [ExtraField(1, "Adjunto"), ExtraField(2, "num factura"), ExtraField(3, "Cliente")]
    window._field_var.set("1")


def _file_ready(window, tmp_path, subject: str):
    """Leave the wizard on the columns step of a file send with *subject*, the columns chosen."""
    window._subject_entry.insert(0, subject)
    window._start_mode = StartMode.NOW
    window._source_kind = "file"
    window._load_file(write_csv(tmp_path / "f.csv", "Correo;Adjunto;Num factura\na@x.com;a.pdf;1\n"))
    window._show_columns_step()
    window._email_column_var.set("Correo")
    window._attachment_column_var.set("Adjunto")


class TestGuiSubjectHint:
    """Covers explaining the #name# notation on the subject step."""

    def test_the_subject_step_explains_the_notation(self, app):
        """Shows the help text about fields in the subject on its step."""
        import customtkinter as ctk
        texts = [w.cget("text") for w in app._frames["subject"].winfo_children() if isinstance(w, ctk.CTkLabel)]
        assert t("subject_hint") in texts


class TestGuiSubjectFieldsAgenda:
    """Covers the subject fields on the extra field step of an agenda send."""

    def test_lists_the_fields_and_how_to_write_them(self, app):
        """Lists every custom field with the way it is written in the subject."""
        app._fill_subject_fields_box(app._field_subject_box, ["num factura", "Cliente"])
        assert _box_text(app._field_subject_box) == "num factura → #num_factura#\nCliente → #Cliente#"

    def test_a_known_field_lets_the_user_go_on(self, app):
        """Binds the subject and moves on when every field matches a custom field."""
        _agenda_ready(app, "Factura #num_factura#")
        with patch.object(app, "_show_frame") as show:
            app._field_next()
        show.assert_called_once_with("certified")
        assert app._subject_template.fields == {"num_factura": "num factura"}

    def test_an_unknown_field_stops_the_user(self, app):
        """Explains which field is unknown and stays on the step."""
        _agenda_ready(app, "Factura #num_factur#")
        with patch.object(app, "_show_frame") as show:
            app._field_next()
        show.assert_not_called()
        assert "#num_factur#" in app._field_error.cget("text")
        assert app._subject_template is None

    def test_the_source_builds_the_subject_of_each_contact(self, app):
        """Hands the bound subject to the agenda source."""
        _agenda_ready(app, "#cliente#")
        app.client = MagicMock()
        app.selected_agenda = MagicMock(id=7)
        with patch.object(app, "_show_frame"):
            app._field_next()
        assert app._recipient_source().subject.fields == {"cliente": "Cliente"}


class TestGuiSubjectFieldsFile:
    """Covers the subject fields on the columns step of a file send."""

    def test_lists_the_columns_and_how_to_write_them(self, app, tmp_path):
        """Lists every column of the file with the way it is written in the subject."""
        _file_ready(app, tmp_path, "Hola")
        assert _box_text(app._columns_subject_box) == "Correo → #Correo#\nAdjunto → #Adjunto#\nNum factura → #Num_factura#"

    def test_a_known_column_lets_the_user_go_on(self, app, tmp_path):
        """Binds the subject and moves on when every field matches a column."""
        _file_ready(app, tmp_path, "Factura #num_factura#")
        with patch.object(app, "_show_frame") as show:
            app._columns_next()
        show.assert_called_once_with("certified")
        assert app._subject_template.fields == {"num_factura": "Num factura"}

    def test_an_unknown_column_stops_the_user(self, app, tmp_path):
        """Explains which field matches no column and stays on the step."""
        _file_ready(app, tmp_path, "#cliente#")
        with patch.object(app, "_show_frame") as show:
            app._columns_next()
        show.assert_not_called()
        assert "#cliente#" in app._columns_error.cget("text")

    def test_changing_the_subject_forgets_the_bound_one(self, app, tmp_path):
        """Matches the subject again after it is changed on its step."""
        _file_ready(app, tmp_path, "#num_factura#")
        with patch.object(app, "_show_frame"):
            app._columns_next()
        with patch.object(app, "_load_templates"):
            app._subject_next()
        assert app._subject_template is None


class TestGuiSubjectSummary:
    """Covers the subject shown in the summary."""

    def test_shows_the_subject_and_an_example(self, app, tmp_path):
        """Shows the subject as written and the final subject of the first row."""
        _file_ready(app, tmp_path, "Factura #num_factura#")
        with patch.object(app, "_show_frame"):
            app._columns_next()
        app.selected_template = MagicMock(id=10, name="Template")
        app.selected_sender = MagicMock(id=20, name="Sender", email="from@example.com")
        app._send_registry = MagicMock()
        app._send_registry.get_sent_keys.return_value = set()
        app._send_registry.get_uncertain_attempts.return_value = {}

        app._load_summary()
        _wait_until(app, lambda: app._summary_text.cget("text") != "")

        text = app._summary_text.cget("text")
        assert "Subject: Factura #num_factura#" in text
        assert "Subject example: Factura 1" in text
