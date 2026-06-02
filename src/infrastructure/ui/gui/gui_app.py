import pathlib
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

from src.infrastructure.api.mensagia_client import MensagiaClient, MensagiaAPIError
from src.infrastructure.api.mensagia_agenda_repository import MensagiaAgendaRepository
from src.infrastructure.api.mensagia_contact_repository import MensagiaContactRepository
from src.infrastructure.api.mensagia_email_address_repository import MensagiaEmailAddressRepository
from src.infrastructure.api.mensagia_email_template_repository import MensagiaEmailTemplateRepository
from src.infrastructure.api.mensagia_extra_field_repository import MensagiaExtraFieldRepository
from src.infrastructure.api.mensagia_email_sender import MensagiaEmailSender
from src.application.use_cases.send_bulk_emails import SendBulkEmailsUseCase
from src.infrastructure.ui.i18n import t, set_language, language_names, detect_system_language, get_language
from src.infrastructure.config.settings import load_api_token, load_language, load_attachment_base_url, load_show_ids
from src.infrastructure.config.last_selections import load_last_selections, save_last_selections
from src.domain.attachment_url import resolve_attachment_url
from src.infrastructure.http.http_attachment_checker import HttpAttachmentChecker


# Apply the light theme globally before any widget is created;
# this cannot be changed per-widget in customtkinter
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Layout constants used throughout the UI for consistent spacing
PAD = 16
WINDOW_W = 620
WINDOW_H = 560


def _resource(relative: str) -> pathlib.Path:
    """Resolve a path to a bundled resource file.

    Handles both development (plain Python) and production (PyInstaller
    bundle) execution contexts. PyInstaller extracts resources to a
    temporary _MEIPASS directory at runtime, so paths must be relative
    to that directory rather than the source tree.

    Args:
        relative: Path relative to the project root (development) or to
            the _MEIPASS extraction directory (bundle).

    Returns:
        Absolute Path object pointing to the resource.
    """
    import sys
    # PyInstaller sets sys._MEIPASS to the temp extraction directory
    if hasattr(sys, "_MEIPASS"):
        return pathlib.Path(sys._MEIPASS) / relative
    # In development the resource lives at the repository root
    return pathlib.Path(__file__).parents[4] / relative


_ICON = _resource("assets/icon.ico")


class App(ctk.CTk):
    """Main GUI application window.

    Implements a multi-step wizard that guides the user through the bulk
    send configuration. Each step is a separate CTkFrame stacked in a
    grid container; the wizard advances by calling _show_frame() to raise
    the appropriate frame. All Mensagia API calls are executed in
    background daemon threads to keep the UI responsive.

    Instance attributes:
        client: Authenticated MensagiaClient created after token validation.
            None until the user has validated a token.
        templates: List of EmailTemplate objects loaded in step 2.
        senders: List of EmailAddress objects loaded in step 3.
        agendas: List of Agenda objects loaded in step 4.
        extra_fields: List of ExtraField objects loaded in step 5.
        selected_template: Template chosen by the user in step 2.
        selected_sender: Sender address chosen by the user in step 3.
        selected_agenda: Agenda group chosen by the user in step 4.
        selected_field: Extra field chosen by the user in step 5.
    """

    def __init__(self):
        """Initialise the window and build the wizard UI."""
        super().__init__()
        self.title(t("app_title"))
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.resizable(False, False)

        # Set the window icon after the event loop starts to avoid a known
        # tkinter race condition on some platforms
        if _ICON.exists():
            self.after(0, lambda: self.iconbitmap(str(_ICON)))

        # Load configuration from .env / environment
        self._show_ids = load_show_ids()
        self._last_sel = load_last_selections()

        # Runtime state — populated as the user progresses through the wizard
        self.client: MensagiaClient | None = None
        self.templates = []
        self.senders = []
        self.agendas = []
        self.extra_fields = []
        self.selected_template = None
        self.selected_sender = None
        self.selected_agenda = None
        self.selected_field = None

        # Build all wizard frames and start on the token step
        self._build_frames()
        self._show_frame("token")

    # ── Language selector (token frame only) ──────────────────────────────────

    def _on_language_change(self):
        """Handle a language radio button click.

        Updates the active language and rebuilds the entire UI from scratch
        so every translated string is refreshed immediately.
        """
        set_language(self._lang_var.get())
        self._rebuild_ui()

    def _rebuild_ui(self):
        """Destroy all widgets and reconstruct the UI in the new language.

        Resets all wizard state so the user starts fresh at the token step
        whenever the language is changed. This is simpler and more reliable
        than updating every label in place.
        """
        # Remove all existing widgets from the window
        for w in self.winfo_children():
            w.destroy()

        # Update the window title in the new language
        self.title(t("app_title"))

        # Reset all runtime state so the wizard starts from scratch
        self._show_ids = load_show_ids()
        self._last_sel = load_last_selections()
        self.client = None
        self.templates = []
        self.senders = []
        self.agendas = []
        self.extra_fields = []
        self.selected_template = None
        self.selected_sender = None
        self.selected_agenda = None
        self.selected_field = None

        self._build_frames()
        self._show_frame("token")

    # ── Frame container ────────────────────────────────────────────────────────

    def _build_frames(self):
        """Create the stacked frame container and build all wizard step frames.

        All step frames are placed at row=0, column=0 in a grid so they
        overlap; _show_frame() uses tkraise() to bring the active step
        to the front without destroying the others.
        """
        # Transparent outer container that fills the window
        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        self._frames = {}

        # Create an empty frame for each wizard step
        for name in ("token", "subject", "template", "sender", "group", "field", "certified", "summary", "sending"):
            frame = ctk.CTkFrame(self._container, fg_color="transparent")
            frame.grid(row=0, column=0, sticky="nsew")
            self._frames[name] = frame

        # Make the single grid cell expand to fill all available space
        self._container.grid_rowconfigure(0, weight=1)
        self._container.grid_columnconfigure(0, weight=1)

        # Populate each frame with its widgets
        self._build_token_frame()
        self._build_subject_frame()
        self._build_template_frame()
        self._build_sender_frame()
        self._build_group_frame()
        self._build_field_frame()
        self._build_certified_frame()
        self._build_summary_frame()
        self._build_sending_frame()

    def _show_frame(self, name: str):
        """Bring the named wizard step frame to the front.

        Args:
            name: Key of the frame to show (e.g. 'token', 'subject').
        """
        self._frames[name].tkraise()

    # ── Step 0: Token ──────────────────────────────────────────────────────────

    def _build_token_frame(self):
        """Build the token entry step (step 0) with the language selector.

        The language selector is placed here rather than in a separate screen
        because it must be accessible before the user commits to a language;
        it is only shown on this first step so it does not clutter later steps.
        Pre-fills the token and base URL fields from the .env file when
        available so non-technical users who have a .env file skip typing.
        """
        f = self._frames["token"]

        # Language selector row — radio buttons for all supported languages
        lang_row = ctk.CTkFrame(f, fg_color="transparent")
        lang_row.pack(anchor="w", pady=(0, PAD))
        ctk.CTkLabel(lang_row, text=t("language_label"), font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 6))
        self._lang_var = tk.StringVar(value=get_language())
        for code, name in language_names().items():
            ctk.CTkRadioButton(
                lang_row, text=name, variable=self._lang_var, value=code,
                font=ctk.CTkFont(size=12), command=self._on_language_change
            ).pack(side="left", padx=6)

        # API token input — masked with asterisks for security
        ctk.CTkLabel(f, text=t("token_label"), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(0, 4))
        self._token_entry = ctk.CTkEntry(f, width=460, show="*", placeholder_text="•••••••••••••••••")
        self._token_entry.pack(anchor="w")

        # Pre-fill from .env so users with a configured token can proceed directly
        preloaded = load_api_token()
        if preloaded:
            self._token_entry.insert(0, preloaded)

        # Optional base URL for relative attachment paths
        ctk.CTkLabel(f, text=t("base_url_label"), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(PAD, 4))
        self._base_url_entry = ctk.CTkEntry(f, width=460, placeholder_text=t("base_url_placeholder"))
        self._base_url_entry.pack(anchor="w")
        preloaded_base = load_attachment_base_url()
        if preloaded_base:
            self._base_url_entry.insert(0, preloaded_base)

        # Status label shows validation feedback below the inputs
        self._token_status = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=12), text_color="gray")
        self._token_status.pack(anchor="w", pady=(6, 0))

        # Action buttons: validate first, then proceed once validation succeeds
        btn_frame = ctk.CTkFrame(f, fg_color="transparent")
        btn_frame.pack(anchor="w", pady=(PAD, 0))
        ctk.CTkButton(btn_frame, text=t("btn_validate"), command=self._validate_token).pack(side="left", padx=(0, 8))
        self._token_next_btn = ctk.CTkButton(btn_frame, text=t("btn_next"), state="disabled", command=self._token_next)
        self._token_next_btn.pack(side="left")

    def _validate_token(self):
        """Validate the entered API token against the Mensagia API.

        Runs the validation in a background thread so the UI stays
        responsive during the HTTP request. Enables the 'Next' button
        only when the token is confirmed valid.
        """
        token = self._token_entry.get().strip()
        if not token:
            return

        # Show a loading indicator while the background thread runs
        self._token_status.configure(text=t("loading"), text_color="gray")
        self.update_idletasks()

        def _check():
            """Background thread: validate the token and update the UI."""
            client = MensagiaClient(token)
            valid = client.validate_token()
            if valid:
                # Store the authenticated client for use in later steps
                self.client = client
                self._token_status.configure(text=t("token_ok"), text_color="green")
                self._token_next_btn.configure(state="normal")
            else:
                self._token_status.configure(text=t("token_invalid"), text_color="red")
                self._token_next_btn.configure(state="disabled")

        threading.Thread(target=_check, daemon=True).start()

    def _token_next(self):
        """Advance from the token step to the subject step."""
        self._show_frame("subject")

    # ── Step 1: Subject ────────────────────────────────────────────────────────

    def _build_subject_frame(self):
        """Build the email subject input step (step 1)."""
        f = self._frames["subject"]
        ctk.CTkLabel(f, text=t("step_subject"), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(PAD, 4))
        ctk.CTkLabel(f, text=t("subject_label"), font=ctk.CTkFont(size=13)).pack(anchor="w")
        self._subject_entry = ctk.CTkEntry(f, width=460, placeholder_text=t("subject_placeholder"))
        self._subject_entry.pack(anchor="w", pady=(4, 0))
        self._subject_error = ctk.CTkLabel(f, text="", text_color="red", font=ctk.CTkFont(size=12))
        self._subject_error.pack(anchor="w")
        self._nav_buttons(f, back="token", next_cmd=self._subject_next)

    def _subject_next(self):
        """Validate the subject and trigger template loading.

        Shows an error indicator if the subject is empty. Otherwise clears
        the error and initiates the API call to fetch templates.
        """
        subject = self._subject_entry.get().strip()
        if not subject:
            self._subject_error.configure(text="  ⚠")
            return
        self._subject_error.configure(text="")
        self._load_templates()

    # ── Step 2: Template ───────────────────────────────────────────────────────

    def _build_template_frame(self):
        """Build the email template selection step (step 2)."""
        f = self._frames["template"]
        ctk.CTkLabel(f, text=t("step_template"), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(PAD, 4))
        ctk.CTkLabel(f, text=t("template_label"), font=ctk.CTkFont(size=13)).pack(anchor="w")
        self._template_var = tk.StringVar()
        # Scrollable frame to handle accounts with many templates
        self._template_list = ctk.CTkScrollableFrame(f, height=260)
        self._template_list.pack(fill="x", pady=(4, 0))
        self._template_error = ctk.CTkLabel(f, text="", text_color="red", font=ctk.CTkFont(size=12))
        self._template_error.pack(anchor="w")
        self._nav_buttons(f, back="subject", next_cmd=self._template_next)

    def _load_templates(self):
        """Navigate to the template step and fetch templates from the API.

        Clears any previous radio buttons and runs the API call in a
        background thread. Restores the previously saved selection if the
        corresponding template still exists in the account.
        """
        self._show_frame("template")
        self._template_error.configure(text=t("loading"))
        # Clear existing radio buttons before fetching new data
        for w in self._template_list.winfo_children():
            w.destroy()

        def _fetch():
            """Background thread: fetch templates and populate the list."""
            try:
                self.templates = MensagiaEmailTemplateRepository(self.client).get_all()
                if not self.templates:
                    self._template_error.configure(text=t("error_no_templates"))
                    return
                self._template_error.configure(text="")
                for tmpl in self.templates:
                    label = f"[{tmpl.id}]  {tmpl.name}" if self._show_ids else tmpl.name
                    ctk.CTkRadioButton(
                        self._template_list, text=label, variable=self._template_var,
                        value=str(tmpl.id), font=ctk.CTkFont(size=13)
                    ).pack(anchor="w", pady=2)
                # Restore the saved selection if it still exists in the account
                saved = self._last_sel.get("template_id")
                if saved and any(str(t.id) == saved for t in self.templates):
                    self._template_var.set(saved)
            except MensagiaAPIError as e:
                self._template_error.configure(text=t("error_api", error=str(e)))

        threading.Thread(target=_fetch, daemon=True).start()

    def _template_next(self):
        """Validate that a template is selected and advance to the sender step."""
        val = self._template_var.get()
        if not val:
            self._template_error.configure(text="  ⚠")
            return
        # Resolve the selected ID back to the full domain object
        self.selected_template = next(t for t in self.templates if str(t.id) == val)
        self._template_error.configure(text="")
        self._load_senders()

    # ── Step 3: Sender ─────────────────────────────────────────────────────────

    def _build_sender_frame(self):
        """Build the sender address selection step (step 3)."""
        f = self._frames["sender"]
        ctk.CTkLabel(f, text=t("step_sender"), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(PAD, 4))
        ctk.CTkLabel(f, text=t("sender_label"), font=ctk.CTkFont(size=13)).pack(anchor="w")
        self._sender_var = tk.StringVar()
        self._sender_list = ctk.CTkScrollableFrame(f, height=260)
        self._sender_list.pack(fill="x", pady=(4, 0))
        self._sender_error = ctk.CTkLabel(f, text="", text_color="red", font=ctk.CTkFont(size=12))
        self._sender_error.pack(anchor="w")
        self._nav_buttons(f, back="template", next_cmd=self._sender_next)

    def _load_senders(self):
        """Navigate to the sender step and fetch verified sender addresses from the API."""
        self._show_frame("sender")
        self._sender_error.configure(text=t("loading"))
        for w in self._sender_list.winfo_children():
            w.destroy()

        def _fetch():
            """Background thread: fetch sender addresses and populate the list."""
            try:
                self.senders = MensagiaEmailAddressRepository(self.client).get_all()
                if not self.senders:
                    self._sender_error.configure(text=t("error_no_senders"))
                    return
                self._sender_error.configure(text="")
                for s in self.senders:
                    # Show the optional display name in parentheses when available
                    label = s.email + (f"  ({s.name})" if s.name else "")
                    ctk.CTkRadioButton(
                        self._sender_list, text=label, variable=self._sender_var,
                        value=str(s.id), font=ctk.CTkFont(size=13)
                    ).pack(anchor="w", pady=2)
                saved = self._last_sel.get("sender_id")
                if saved and any(str(s.id) == saved for s in self.senders):
                    self._sender_var.set(saved)
            except MensagiaAPIError as e:
                self._sender_error.configure(text=t("error_api", error=str(e)))

        threading.Thread(target=_fetch, daemon=True).start()

    def _sender_next(self):
        """Validate that a sender is selected and advance to the group step."""
        val = self._sender_var.get()
        if not val:
            self._sender_error.configure(text="  ⚠")
            return
        self.selected_sender = next(s for s in self.senders if str(s.id) == val)
        self._sender_error.configure(text="")
        self._load_groups()

    # ── Step 4: Group ──────────────────────────────────────────────────────────

    def _build_group_frame(self):
        """Build the agenda group selection step (step 4)."""
        f = self._frames["group"]
        ctk.CTkLabel(f, text=t("step_group"), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(PAD, 4))
        ctk.CTkLabel(f, text=t("group_label"), font=ctk.CTkFont(size=13)).pack(anchor="w")
        self._group_var = tk.StringVar()
        self._group_list = ctk.CTkScrollableFrame(f, height=260)
        self._group_list.pack(fill="x", pady=(4, 0))
        self._group_error = ctk.CTkLabel(f, text="", text_color="red", font=ctk.CTkFont(size=12))
        self._group_error.pack(anchor="w")
        self._nav_buttons(f, back="sender", next_cmd=self._group_next)

    def _load_groups(self):
        """Navigate to the group step and fetch agenda groups from the API."""
        self._show_frame("group")
        self._group_error.configure(text=t("loading"))
        for w in self._group_list.winfo_children():
            w.destroy()

        def _fetch():
            """Background thread: fetch agendas and populate the list."""
            try:
                self.agendas = MensagiaAgendaRepository(self.client).get_all()
                if not self.agendas:
                    self._group_error.configure(text=t("error_no_groups"))
                    return
                self._group_error.configure(text="")
                for a in self.agendas:
                    # Show contact count so the user can identify the right group
                    label = (f"[{a.id}]  " if self._show_ids else "") + f"{a.name}  ({t('group_contacts', count=a.total_users)})"
                    ctk.CTkRadioButton(
                        self._group_list, text=label, variable=self._group_var,
                        value=str(a.id), font=ctk.CTkFont(size=13)
                    ).pack(anchor="w", pady=2)
                saved = self._last_sel.get("agenda_id")
                if saved and any(str(a.id) == saved for a in self.agendas):
                    self._group_var.set(saved)
            except MensagiaAPIError as e:
                self._group_error.configure(text=t("error_api", error=str(e)))

        threading.Thread(target=_fetch, daemon=True).start()

    def _group_next(self):
        """Validate that a group is selected and advance to the extra field step."""
        val = self._group_var.get()
        if not val:
            self._group_error.configure(text="  ⚠")
            return
        self.selected_agenda = next(a for a in self.agendas if str(a.id) == val)
        self._group_error.configure(text="")
        self._load_fields()

    # ── Step 5: Extra field ────────────────────────────────────────────────────

    def _build_field_frame(self):
        """Build the extra field selection step (step 5)."""
        f = self._frames["field"]
        ctk.CTkLabel(f, text=t("step_field"), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(PAD, 4))
        ctk.CTkLabel(f, text=t("field_label"), font=ctk.CTkFont(size=13)).pack(anchor="w")
        self._field_var = tk.StringVar()
        self._field_list = ctk.CTkScrollableFrame(f, height=260)
        self._field_list.pack(fill="x", pady=(4, 0))
        self._field_error = ctk.CTkLabel(f, text="", text_color="red", font=ctk.CTkFont(size=12))
        self._field_error.pack(anchor="w")
        self._nav_buttons(f, back="group", next_cmd=self._field_next)

    def _load_fields(self):
        """Navigate to the field step and fetch extra field definitions from the API."""
        self._show_frame("field")
        self._field_error.configure(text=t("loading"))
        for w in self._field_list.winfo_children():
            w.destroy()

        def _fetch():
            """Background thread: fetch extra fields and populate the list."""
            try:
                self.extra_fields = MensagiaExtraFieldRepository(self.client).get_all()
                if not self.extra_fields:
                    self._field_error.configure(text=t("error_no_fields"))
                    return
                self._field_error.configure(text="")
                for ef in self.extra_fields:
                    ctk.CTkRadioButton(
                        self._field_list, text=f"[{ef.id}]  {ef.name}" if self._show_ids else ef.name,
                        variable=self._field_var, value=str(ef.id), font=ctk.CTkFont(size=13)
                    ).pack(anchor="w", pady=2)
                saved = self._last_sel.get("field_id")
                if saved and any(str(ef.id) == saved for ef in self.extra_fields):
                    self._field_var.set(saved)
            except MensagiaAPIError as e:
                self._field_error.configure(text=t("error_api", error=str(e)))

        threading.Thread(target=_fetch, daemon=True).start()

    def _field_next(self):
        """Validate that an extra field is selected and advance to the certified step."""
        val = self._field_var.get()
        if not val:
            self._field_error.configure(text="  ⚠")
            return
        self.selected_field = next(ef for ef in self.extra_fields if str(ef.id) == val)
        self._field_error.configure(text="")
        self._show_frame("certified")

    # ── Step 6: Certified ──────────────────────────────────────────────────────

    def _build_certified_frame(self):
        """Build the certified email option step (step 6).

        Restores the previous session's certified choice from last_selections
        so the user does not have to reconfigure it every time.
        """
        f = self._frames["certified"]
        ctk.CTkLabel(f, text=t("step_certified"), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(PAD, 4))
        ctk.CTkLabel(f, text=t("certified_label"), font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(8, 4))
        # Restore last saved value; default to 0 (not certified) on first run
        self._certified_var = tk.IntVar(value=self._last_sel.get("certified", 0))
        ctk.CTkRadioButton(f, text=t("certified_no"), variable=self._certified_var, value=0,
                           font=ctk.CTkFont(size=13)).pack(anchor="w", pady=2)
        ctk.CTkRadioButton(f, text=t("certified_yes"), variable=self._certified_var, value=1,
                           font=ctk.CTkFont(size=13)).pack(anchor="w", pady=2)
        self._nav_buttons(f, back="field", next_cmd=self._certified_next)

    def _certified_next(self):
        """Build the summary and advance to the summary step."""
        self._build_summary()
        self._show_frame("summary")

    # ── Step 7: Summary ────────────────────────────────────────────────────────

    def _build_summary_frame(self):
        """Build the pre-send summary step (step 7).

        Creates placeholder widgets that are populated with real data by
        _build_summary() each time the user reaches this step.
        """
        f = self._frames["summary"]
        self._summary_title = ctk.CTkLabel(f, text=t("step_summary"), font=ctk.CTkFont(size=15, weight="bold"))
        self._summary_title.pack(anchor="w", pady=(PAD, 8))
        self._summary_text = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=13), justify="left")
        self._summary_text.pack(anchor="w")
        self._summary_contacts_label = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=13, weight="bold"))
        self._summary_contacts_label.pack(anchor="w", pady=(8, 0))
        self._summary_skipped_label = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=12), text_color="gray")
        self._summary_skipped_label.pack(anchor="w")

        # Navigation row: back, dry-run, and the destructive send button
        btn_frame = ctk.CTkFrame(f, fg_color="transparent")
        btn_frame.pack(anchor="w", pady=(PAD, 0))
        ctk.CTkButton(btn_frame, text=t("btn_back"), command=lambda: self._show_frame("certified"),
                      fg_color="gray", hover_color="#555").pack(side="left", padx=(0, 8))
        self._dry_run_btn = ctk.CTkButton(btn_frame, text=t("btn_dry_run"),
                                          command=lambda: self._do_send(dry_run=True),
                                          fg_color="#888", hover_color="#666")
        self._dry_run_btn.pack(side="left", padx=(0, 8))
        # The real send button is styled red to signal it is a destructive action
        self._send_btn = ctk.CTkButton(btn_frame, text=t("btn_send"),
                                       command=lambda: self._do_send(dry_run=False),
                                       fg_color="#e05", hover_color="#c03")
        self._send_btn.pack(side="left")

    def _build_summary(self):
        """Fetch the eligible contact count and populate the summary step widgets.

        Queries the API synchronously here (on the main thread) because the
        result must be ready before _show_frame("summary") is called. The
        operation is fast because we only query one group's contacts.
        """
        try:
            contacts = MensagiaContactRepository(self.client).get_by_group(
                self.selected_agenda.id, in_mail_blacklist=False
            )
        except MensagiaAPIError as e:
            messagebox.showerror("Error", t("error_api", error=str(e)))
            return

        # Replicate the same eligibility filter as the use case
        eligible = [
            c for c in contacts
            if c.email and c.extra_fields.get(self.selected_field.name)
        ]

        # Build the multi-line summary text with all selected options
        lines = "\n".join([
            t("summary_from", value=f"{self.selected_sender.name} <{self.selected_sender.email}>" if self.selected_sender.name else self.selected_sender.email),
            t("summary_subject", value=self._subject_entry.get().strip()),
            t("summary_template", value=self.selected_template.name),
            t("summary_group", value=self.selected_agenda.name),
            t("summary_field", value=self.selected_field.name),
            t("summary_certified", value=t("yes") if self._certified_var.get() else t("no")),
        ])
        self._summary_text.configure(text=lines)
        self._summary_contacts_label.configure(text=t("summary_contacts", count=len(eligible)))
        self._summary_skipped_label.configure(text=t("summary_skipped", count=len(contacts) - len(eligible)))

    # ── Step 8: Sending ────────────────────────────────────────────────────────

    def _build_sending_frame(self):
        """Build the progress and results step (step 8).

        Creates the progress bar and result label that are updated live
        during the send operation by _do_send().
        """
        f = self._frames["sending"]
        ctk.CTkLabel(f, text=t("sending"), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(PAD, 4))
        self._progress_bar = ctk.CTkProgressBar(f, width=460)
        self._progress_bar.pack(anchor="w", pady=(8, 4))
        self._progress_bar.set(0)
        self._progress_label = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=13))
        self._progress_label.pack(anchor="w")
        self._result_label = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=13), wraplength=460, justify="left")
        self._result_label.pack(anchor="w", pady=(PAD, 0))
        # Container for post-send action buttons; populated dynamically by _do_send
        self._sending_actions = ctk.CTkFrame(f, fg_color="transparent")
        self._sending_actions.pack(anchor="w", pady=(PAD, 0))

    def _reset_for_new_send(self):
        """Clear all selections and go back to the subject step for a new campaign.

        Clears the StringVars so the radio buttons in list steps are
        unselected, then navigates to the subject step. The token step is
        skipped because the same client (and therefore the same token) is
        reused.
        """
        # Clear all selected domain objects
        self.selected_template = None
        self.selected_sender = None
        self.selected_agenda = None
        self.selected_field = None

        # Deselect all radio buttons in the list steps
        self._template_var.set("")
        self._sender_var.set("")
        self._group_var.set("")
        self._field_var.set("")

        self._show_frame("subject")

    def _do_send(self, dry_run: bool = False):
        """Execute the bulk send (or dry-run) in a background thread.

        Navigates to the sending step immediately, then starts a daemon
        thread that processes contacts one by one, updating the progress
        bar and label after each one. After completion it saves the last
        selections and shows the appropriate post-send action buttons.

        Args:
            dry_run: When True, performs all validation but skips the
                actual API call so no emails are sent.
        """
        # Show the sending frame immediately so the progress bar is visible
        self._show_frame("sending")
        self._progress_bar.set(0)
        self._progress_label.configure(text="")
        self._result_label.configure(text="")

        # Remove any action buttons left over from a previous send
        for w in self._sending_actions.winfo_children():
            w.destroy()

        def _run():
            """Background thread: send emails and update the UI progressively."""
            try:
                contact_repo = MensagiaContactRepository(self.client)
                email_sender_adapter = MensagiaEmailSender(self.client)
                attachment_base_url = self._base_url_entry.get().strip() or None
                attachment_checker = HttpAttachmentChecker()
                _dry_run = dry_run

                # Determine the eligible contacts (replicate use-case eligibility logic)
                contacts = contact_repo.get_by_group(self.selected_agenda.id, in_mail_blacklist=False)
                eligible = [
                    c for c in contacts
                    if c.email and c.extra_fields.get(self.selected_field.name)
                ]
                total = len(eligible)

                from src.domain.scheduling import calculate_start_dates
                from src.domain.entities.email_message import EmailMessage
                from datetime import datetime

                # Compute staggered send dates upfront so the timing is consistent
                start_dates = calculate_start_dates(total)
                sent, errors = [], []

                # Process each eligible contact, updating progress after each one
                for i, (contact, start_date) in enumerate(zip(eligible, start_dates), 1):
                    self._progress_label.configure(text=t("send_progress", current=i, total=total))
                    self._progress_bar.set(i / total if total else 0)
                    # Force a UI redraw so the progress is visible immediately
                    self.update_idletasks()

                    try:
                        # Resolve relative attachment paths to full URLs
                        attachment_url = resolve_attachment_url(
                            contact.extra_fields[self.selected_field.name],
                            attachment_base_url,
                        )

                        # Verify the attachment is reachable before spending an API call
                        if not attachment_checker.is_accessible(attachment_url):
                            raise ValueError(f"attachment not accessible: {attachment_url}")

                        message = EmailMessage(
                            from_email=self.selected_sender.email,
                            to_email=contact.email,
                            subject=self._subject_entry.get().strip(),
                            template_id=self.selected_template.id,
                            start_date=start_date,
                            attachments=[attachment_url],
                            certified=self._certified_var.get(),
                        )

                        # Skip the actual API call in dry-run mode
                        if not _dry_run:
                            email_sender_adapter.send(message)
                        sent.append(contact)
                    except Exception as e:
                        errors.append((contact, str(e)))

                # Compute skipped contacts (those not in the eligible list)
                skipped = [c for c in contacts if c not in eligible]

                # Build the result text, appending per-contact error details if any
                error_msgs = "\n".join(
                    t("send_error", email=c.email, error=err) for c, err in errors
                )
                key = "dry_run_complete" if _dry_run else "send_complete"
                result_text = t(key, sent=len(sent), skipped=len(skipped), errors=len(errors))
                if error_msgs:
                    result_text += "\n\n" + error_msgs

                self._result_label.configure(text=result_text)
                self._progress_bar.set(1)

                # Persist the selections so they are pre-selected on the next run
                save_last_selections({
                    "template_id": str(self.selected_template.id),
                    "sender_id": str(self.selected_sender.id),
                    "agenda_id": str(self.selected_agenda.id),
                    "field_id": str(self.selected_field.id),
                    "certified": self._certified_var.get(),
                })

                # Show contextual post-send buttons depending on dry-run vs real send
                if _dry_run:
                    # After a dry-run, offer to proceed with the real send or go back
                    ctk.CTkButton(
                        self._sending_actions, text=t("btn_send"),
                        command=lambda: self._do_send(dry_run=False),
                        fg_color="#e05", hover_color="#c03"
                    ).pack(side="left", padx=(0, 8))
                    ctk.CTkButton(
                        self._sending_actions, text=t("btn_back_to_summary"),
                        command=lambda: self._show_frame("summary"),
                        fg_color="gray", hover_color="#555"
                    ).pack(side="left")
                else:
                    # After a real send, only offer to start a new campaign
                    ctk.CTkButton(
                        self._sending_actions, text=t("btn_new_send"),
                        command=self._reset_for_new_send
                    ).pack(side="left")

            except MensagiaAPIError as e:
                self._result_label.configure(text=t("error_api", error=str(e)), text_color="red")

        threading.Thread(target=_run, daemon=True).start()

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _nav_buttons(self, frame, back: str, next_cmd):
        """Add Back and Next navigation buttons to the bottom of a wizard step.

        Args:
            frame: The CTkFrame to attach the buttons to.
            back: Name of the frame to navigate to when Back is clicked.
                Pass an empty string to omit the Back button.
            next_cmd: Callable invoked when the Next button is clicked.
        """
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(anchor="w", pady=(PAD, 0))
        if back:
            ctk.CTkButton(btn_frame, text=t("btn_back"), command=lambda: self._show_frame(back),
                          fg_color="gray", hover_color="#555").pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_frame, text=t("btn_next"), command=next_cmd).pack(side="left")


def run():
    """Entry point for the graphical (GUI) interface of the application.

    Sets the language from the environment or OS locale before constructing
    the App window, then starts the tkinter event loop.
    """
    # Determine the language before any UI is built so the first frame is
    # rendered in the correct language
    env_lang = load_language()
    set_language(env_lang if env_lang else detect_system_language())

    app = App()
    app.mainloop()
