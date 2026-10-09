from unittest.mock import MagicMock, patch

import openpyxl
import pytest

from src.domain.entities.agenda import Agenda
# Reuse the window fixture, the event-loop helper and the Tk availability skip
from tests.unit.infrastructure.ui.test_gui_group_selection import _wait_until, app, pytestmark  # noqa: F401


def write_csv(path, text: str) -> str:
    """Write a UTF-8 .csv file and return its path as text."""
    path.write_bytes(text.encode("utf-8"))
    return str(path)


def write_xlsx(path, sheets: dict) -> str:
    """Write an .xlsx file with one sheet per entry of *sheets* (name -> list of rows)."""
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        sheet = workbook.create_sheet(name)
        for row in rows:
            sheet.append(row)
    workbook.save(path)
    return str(path)


@pytest.fixture
def csv_file(tmp_path) -> str:
    """A valid CSV with a name, an email and an attachment column."""
    return write_csv(tmp_path / "envios.csv", "Nombre;Correo;Adjunto\nAna;a@x.com;a.pdf\nLuis;l@x.com;l.pdf\n")


class TestGuiSourceChoice:
    """Covers choosing where the recipients come from on the subject step."""

    def test_agenda_is_the_default_source(self, app):
        """Without a remembered choice, the agenda group is selected."""
        assert app._source_var.get() == "agenda"

    def test_remembered_source_is_restored(self, tmp_path):
        """The source used last time is selected again on start."""
        from src.infrastructure.ui.gui.gui_app import App
        with patch("src.infrastructure.ui.gui.gui_app.load_last_selections", return_value={"source": "file"}):
            window = App()
        window.withdraw()
        try:
            assert window._source_var.get() == "file"
        finally:
            window.destroy()

    def test_subject_next_keeps_the_chosen_source(self, app):
        """Moving on from the subject step remembers the chosen source for the next steps."""
        app._subject_entry.insert(0, "Subject")
        app._source_var.set("file")
        with patch.object(app, "_load_templates"):
            app._subject_next()
        assert app._source_kind == "file"

    def test_sender_next_goes_to_the_file_step(self, app):
        """With a file as source, the step after the sender is the file step."""
        app._source_kind = "file"
        app.senders = [MagicMock(id=1)]
        app._sender_var.set("1")
        with patch.object(app, "_show_file_step") as show_file, patch.object(app, "_load_groups") as load_groups:
            app._sender_next()
        show_file.assert_called_once()
        load_groups.assert_not_called()

    def test_sender_next_goes_to_the_groups_for_the_agenda(self, app):
        """With the agenda as source, the step after the sender is still the group step."""
        app._source_kind = "agenda"
        app.senders = [MagicMock(id=1)]
        app._sender_var.set("1")
        with patch.object(app, "_load_groups") as load_groups:
            app._sender_next()
        load_groups.assert_called_once()


class TestGuiFileStep:
    """Covers choosing the file and its sheet."""

    def test_loading_a_csv_shows_its_name_and_reads_its_columns(self, app, csv_file):
        """A valid CSV shows its file name, no error, no sheet selector, and its columns."""
        app._load_file(csv_file)
        assert app._file_name_label.cget("text") == "envios.csv"
        assert app._file_error.cget("text") == ""
        assert not app._sheet_row.winfo_manager()
        assert app._file_columns == ["Nombre", "Correo", "Adjunto"]

    def test_workbook_with_several_sheets_offers_them(self, app, tmp_path):
        """A workbook with several sheets shows the sheet selector, starting on the first one."""
        path = write_xlsx(tmp_path / "f.xlsx", {
            "Octubre": [["Correo", "Adjunto"], ["a@x.com", "a.pdf"]],
            "Noviembre": [["Email", "Fichero"], ["b@x.com", "b.pdf"]],
        })
        app._load_file(path)
        assert app._sheet_row.winfo_manager()
        assert app._sheet_menu.cget("values") == ["Octubre", "Noviembre"]
        assert app._file_sheet == "Octubre"
        assert app._file_columns == ["Correo", "Adjunto"]

    def test_changing_the_sheet_reads_its_columns(self, app, tmp_path):
        """Choosing another sheet reads the columns of that sheet."""
        path = write_xlsx(tmp_path / "f.xlsx", {
            "Octubre": [["Correo", "Adjunto"], ["a@x.com", "a.pdf"]],
            "Noviembre": [["Email", "Fichero"], ["b@x.com", "b.pdf"]],
        })
        app._load_file(path)
        app._on_sheet_change("Noviembre")
        assert (app._file_sheet, app._file_columns) == ("Noviembre", ["Email", "Fichero"])

    def test_unusable_file_shows_the_reason_and_blocks_next(self, app, tmp_path):
        """A file that cannot be used explains why and the step does not move on."""
        app._load_file(write_csv(tmp_path / "f.csv", "a@x.com;a.pdf\nb@x.com;b.pdf\n"))
        assert "no header" in app._file_error.cget("text")
        with patch.object(app, "_show_columns_step") as show_columns:
            app._file_next()
        show_columns.assert_not_called()

    def test_next_without_a_file_is_refused(self, app):
        """The step does not move on until a file is chosen."""
        with patch.object(app, "_show_columns_step") as show_columns:
            app._file_next()
        show_columns.assert_not_called()
        assert app._file_error.cget("text") != ""

    def test_next_with_a_valid_file_goes_to_the_columns(self, app, csv_file):
        """A valid file moves on to the column step."""
        app._load_file(csv_file)
        with patch.object(app, "_show_columns_step") as show_columns:
            app._file_next()
        show_columns.assert_called_once()

    def test_browse_opens_the_last_folder(self, app, csv_file, tmp_path):
        """The file dialog starts in the folder of the last file used."""
        app._last_sel = {"file_dir": str(tmp_path)}
        with patch("src.infrastructure.ui.gui.gui_app.filedialog.askopenfilename", return_value=csv_file) as ask:
            app._browse_file()
        assert ask.call_args.kwargs["initialdir"] == str(tmp_path)
        assert app._file_path == csv_file

    def test_cancelled_dialog_keeps_the_current_file(self, app, csv_file):
        """Closing the dialog without choosing keeps the file chosen before."""
        app._load_file(csv_file)
        with patch("src.infrastructure.ui.gui.gui_app.filedialog.askopenfilename", return_value=""):
            app._browse_file()
        assert app._file_path == csv_file


class TestGuiColumnsStep:
    """Covers choosing the email and attachment columns."""

    def test_menus_offer_the_file_columns(self, app, csv_file):
        """Both selectors list the columns of the file, with nothing chosen yet."""
        app._load_file(csv_file)
        app._show_columns_step()
        assert app._email_column_menu.cget("values") == ["Nombre", "Correo", "Adjunto"]
        assert app._attachment_column_menu.cget("values") == ["Nombre", "Correo", "Adjunto"]
        assert (app._email_column_var.get(), app._attachment_column_var.get()) == ("", "")

    def test_remembered_columns_are_preselected(self, app, csv_file):
        """Columns chosen last time are selected again when the new file has them."""
        app._last_sel = {"email_column": "Correo", "attachment_column": "Adjunto"}
        app._load_file(csv_file)
        app._show_columns_step()
        assert (app._email_column_var.get(), app._attachment_column_var.get()) == ("Correo", "Adjunto")

    def test_remembered_columns_missing_from_the_file_are_ignored(self, app, csv_file):
        """A remembered column that the new file lacks is left unselected."""
        app._last_sel = {"email_column": "Email", "attachment_column": "Adjunto"}
        app._load_file(csv_file)
        app._show_columns_step()
        assert (app._email_column_var.get(), app._attachment_column_var.get()) == ("", "Adjunto")

    def test_same_column_twice_is_refused(self, app, csv_file):
        """The same column cannot hold the email and the attachment."""
        app._load_file(csv_file)
        app._show_columns_step()
        app._email_column_var.set("Correo")
        app._attachment_column_var.set("Correo")
        with patch.object(app, "_show_frame") as show:
            app._columns_next()
        show.assert_not_called()
        assert "different column" in app._columns_error.cget("text")

    def test_missing_choice_is_refused(self, app, csv_file):
        """Both columns must be chosen."""
        app._load_file(csv_file)
        app._show_columns_step()
        app._email_column_var.set("Correo")
        with patch.object(app, "_show_frame") as show:
            app._columns_next()
        show.assert_not_called()

    def test_valid_choice_goes_to_the_certified_step(self, app, csv_file):
        """Two different columns move on to the certified step."""
        app._load_file(csv_file)
        app._show_columns_step()
        app._email_column_var.set("Correo")
        app._attachment_column_var.set("Adjunto")
        with patch.object(app, "_show_frame") as show:
            app._columns_next()
        show.assert_called_once_with("certified")
        assert (app._email_column, app._attachment_column) == ("Correo", "Adjunto")

    def test_certified_back_returns_to_the_columns(self, app):
        """Going back from the certified step returns to the columns for a file."""
        app._source_kind = "file"
        with patch.object(app, "_show_frame") as show:
            app._certified_back()
        show.assert_called_once_with("columns")

    def test_certified_back_returns_to_the_field_for_the_agenda(self, app):
        """Going back from the certified step returns to the extra field for a group."""
        app._source_kind = "agenda"
        with patch.object(app, "_show_frame") as show:
            app._certified_back()
        show.assert_called_once_with("field")


def _prepare_file_summary(window, path: str):
    """Fill in the wizard selections for a send to the rows of *path*."""
    window.selected_template = MagicMock(id=10, name="Template")
    window.selected_sender = MagicMock(id=20, name="Sender", email="from@example.com")
    window._subject_entry.insert(0, "Subject")
    window._source_kind = "file"
    window._load_file(path)
    window._email_column, window._attachment_column = "Correo", "Adjunto"
    window._send_registry = MagicMock()
    window._send_registry.get_sent_keys.return_value = set()
    window._send_registry.get_uncertain_attempts.return_value = {}


class TestGuiFileSummary:
    """Covers the summary of a send to the rows of a file."""

    def test_summary_names_the_file_and_columns_and_counts_rows(self, app, tmp_path):
        """The summary lists the file and both columns, and counts eligible and discarded rows."""
        path = write_csv(tmp_path / "envios.csv", "Correo;Adjunto\na@x.com;a.pdf\nmal;b.pdf\n")
        _prepare_file_summary(app, path)
        app._load_summary()
        _wait_until(app, lambda: app._summary_text.cget("text") != "")

        text = app._summary_text.cget("text")
        assert "File: envios.csv" in text
        assert "Email column: Correo" in text
        assert "Attachment column: Adjunto" in text
        assert app._summary_contacts_label.cget("text") == "Eligible rows: 1"
        assert app._summary_skipped_label.cget("text") == "Discarded rows: 1"
        assert str(app._send_btn.cget("state")) == "normal"

    def test_file_that_became_unusable_is_reported(self, app, tmp_path, csv_file):
        """A file changed after choosing the columns shows the reason and blocks both actions."""
        _prepare_file_summary(app, csv_file)
        write_csv(tmp_path / "envios.csv", "Nombre;Email;Adjunto\nAna;a@x.com;a.pdf\n")
        app._load_summary()
        _wait_until(app, lambda: app._summary_error.cget("text") != "")

        assert "Correo" in app._summary_error.cget("text")
        assert str(app._send_btn.cget("state")) == "disabled"
        assert str(app._dry_run_btn.cget("state")) == "disabled"

    def test_no_eligible_row_is_explained(self, app, tmp_path):
        """A file with no sendable row says so and only allows a simulation."""
        _prepare_file_summary(app, write_csv(tmp_path / "f.csv", "Correo;Adjunto\nmal;a.pdf\n"))
        app._load_summary()
        _wait_until(app, lambda: app._summary_error.cget("text") != "")

        assert "No row of the file" in app._summary_error.cget("text")
        assert str(app._send_btn.cget("state")) == "disabled"
        assert str(app._dry_run_btn.cget("state")) == "normal"

    def test_relative_and_absolute_values_of_the_same_file_are_one_row(self, app, tmp_path):
        """With the base URL of the first step, a relative path and its full URL count as a single row."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto\na@x.com;a.pdf\na@x.com;https://cdn.x.com/docs/a.pdf\n")
        app._base_url_entry.delete(0, "end")
        app._base_url_entry.insert(0, "https://cdn.x.com/docs/")
        _prepare_file_summary(app, path)
        app._load_summary()
        _wait_until(app, lambda: app._summary_contacts_label.cget("text") != "Loading...")

        assert app._summary_contacts_label.cget("text") == "Eligible rows: 1"
        assert app._summary_skipped_label.cget("text") == "Discarded rows: 1"


class TestGuiFileSelections:
    """Covers the choices remembered after a send."""

    def test_file_send_remembers_source_folder_and_columns(self, app, csv_file, tmp_path):
        """A file send remembers the source, the file's folder and the column names, but not the file."""
        app._last_sel = {"agenda_id": "7", "field_id": "8"}
        app.selected_template = MagicMock(id=10)
        app.selected_sender = MagicMock(id=20)
        app._source_kind = "file"
        app._load_file(csv_file)
        app._email_column, app._attachment_column = "Correo", "Adjunto"

        selections = app._selections()

        assert selections["source"] == "file"
        assert selections["file_dir"] == str(tmp_path)
        assert (selections["email_column"], selections["attachment_column"]) == ("Correo", "Adjunto")
        assert "file" not in selections and "sheet" not in selections
        # The agenda choices of an earlier send are kept for the next agenda send
        assert (selections["agenda_id"], selections["field_id"]) == ("7", "8")

    def test_agenda_send_keeps_the_file_choices(self, app):
        """An agenda send keeps the file folder and columns remembered from an earlier file send."""
        app._last_sel = {"file_dir": "C:/datos", "email_column": "Correo"}
        app.selected_template = MagicMock(id=10)
        app.selected_sender = MagicMock(id=20)
        app.selected_agenda = Agenda(id=1, name="G", total_users=1)
        app.selected_field = MagicMock(id=30)
        app._source_kind = "agenda"

        selections = app._selections()

        assert selections["source"] == "agenda"
        assert (selections["agenda_id"], selections["field_id"]) == ("1", "30")
        assert (selections["file_dir"], selections["email_column"]) == ("C:/datos", "Correo")
