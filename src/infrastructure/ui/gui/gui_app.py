import pathlib
import queue
import threading
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk

from src.infrastructure.api.mensagia_client import MensagiaClient, MensagiaAPIError
from src.infrastructure.api.mensagia_agenda_repository import MensagiaAgendaRepository
from src.infrastructure.api.mensagia_contact_repository import MensagiaContactRepository
from src.infrastructure.api.mensagia_email_address_repository import MensagiaEmailAddressRepository
from src.infrastructure.api.mensagia_email_template_repository import MensagiaEmailTemplateRepository
from src.infrastructure.api.mensagia_extra_field_repository import MensagiaExtraFieldRepository
from src.infrastructure.api.mensagia_email_sender import MensagiaEmailSender
from src.infrastructure.recipients.agenda_recipient_source import AgendaRecipientSource
from src.application.use_cases.send_bulk_emails import SendBulkEmailsUseCase
from src.infrastructure.ui.i18n import t, set_language, language_names, detect_system_language, get_language
from src.infrastructure.config.settings import load_api_token, load_language, load_attachment_base_url, load_show_ids
from src.infrastructure.config.last_selections import load_last_selections, save_last_selections
from src.infrastructure.http.http_attachment_checker import HttpAttachmentChecker
from src.infrastructure.logging.send_logger import SendLogger
from src.domain.entities.campaign import Campaign
from src.infrastructure.persistence.json_send_registry import JsonSendRegistry
from src.infrastructure.ui.uncertain_sends import resume_uncertain_lines, result_uncertain_lines
from src.infrastructure.ui.start_time import StartInputError, default_start_fields, read_fixed_start, summary_start_lines
from src.domain.scheduling import StartMode


# Apply the light theme globally before any widget is created;
# this cannot be changed per-widget in customtkinter
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Layout constants used throughout the UI for consistent spacing
PAD = 16
WINDOW_W = 620
WINDOW_H = 560

# How often the main thread drains the UI updates queued by worker threads
UI_POLL_MS = 50

# Maximum number of digits of each start field: day, month, year, hour, minute
_START_FIELD_DIGITS = (2, 2, 4, 2, 2)

# Text colour of the start fields while disabled (light and dark themes)
_DISABLED_TEXT = ("gray60", "gray45")


def _now() -> datetime:
    """Return the current date and time.

    Kept in a function of its own so tests can freeze the clock used to
    propose and validate the start of a send.

    Returns:
        The current local date and time.
    """
    return datetime.now()


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
        _can_send: True when the summary allows a real send; False when
            only a simulation is possible because nothing can be sent.
        _start_mode: Start mode accepted on the subject step.
        _start_at: Start date and time accepted in the fixed mode, or None.
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
        # Tracks already-sent contacts per campaign; stateless (file-backed),
        # so a single instance is reused across the whole app session
        self._send_registry = JsonSendRegistry()
        # Whether the summary allows a real send, not just a simulation
        self._can_send = False

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
        # Start chosen on the subject step; the fields are only read on Next
        self._start_mode = StartMode.NOW
        self._start_at = None

        # Updates handed over by background threads, applied by _pump_ui
        self._ui_queue = queue.Queue()

        # Build all wizard frames and start on the token step
        self._build_frames()
        self._show_frame("token")

        # Start draining the queue only once the UI exists to be updated
        self._pump_ui()

    def _pump_ui(self):
        """Apply the UI updates queued by background threads.

        tkinter widgets may only be touched by the thread running the event
        loop, and after() is not safe to call from another thread either, so
        worker threads push a callable here instead and this method, which
        always runs on the main thread, invokes it.

        A failing update still propagates to tkinter, which reports it, but
        the next poll is always scheduled: otherwise a single error would
        stop every later update and freeze the interface for good.
        """
        try:
            while True:
                try:
                    update = self._ui_queue.get_nowait()
                except queue.Empty:
                    break
                update()
        finally:
            self.after(UI_POLL_MS, self._pump_ui)

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
        self._start_mode = StartMode.NOW
        self._start_at = None

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

        # Start mode selector. The radio buttons hold StartMode values, so a
        # later mode only needs one more button here
        ctk.CTkLabel(f, text=t("start_label"), font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(8, 4))
        self._start_mode_var = tk.StringVar(value=StartMode.NOW.value)
        for mode, key in ((StartMode.NOW, "start_now"), (StartMode.FIXED, "start_fixed")):
            ctk.CTkRadioButton(f, text=t(key), variable=self._start_mode_var, value=mode.value,
                               command=self._update_start_fields,
                               font=ctk.CTkFont(size=13)).pack(anchor="w", pady=2)

        # One small field per part, in a fixed day/month/year order whatever
        # the language, so no date format has to be guessed
        fields = ctk.CTkFrame(f, fg_color="transparent")
        fields.pack(anchor="w", padx=(28, 0), pady=(4, 0))
        self._start_fields = []
        self._start_labels = []
        rows = ((t("start_date_label"), ((0, 40), (1, 40), (2, 60)), "/"),
                (t("start_time_label"), ((3, 40), (4, 40)), ":"))
        for row, (label, parts, separator) in enumerate(rows):
            row_label = ctk.CTkLabel(fields, text=label, font=ctk.CTkFont(size=13))
            row_label.grid(row=row, column=0, sticky="w", padx=(0, 8), pady=2)
            self._start_labels.append(row_label)
            for i, (index, width) in enumerate(parts):
                if i:
                    separator_label = ctk.CTkLabel(fields, text=separator)
                    separator_label.grid(row=row, column=2 * i, padx=2)
                    self._start_labels.append(separator_label)
                entry = ctk.CTkEntry(fields, width=width, justify="center")
                entry.grid(row=row, column=2 * i + 1, pady=2)
                entry.bind("<KeyRelease>", lambda event, index=index: self._advance_start_field(index, event))
                self._start_fields.append(entry)

        # A disabled CTkEntry looks exactly like an enabled one, so the text
        # is greyed out by hand; keep the theme colours to restore them
        self._start_enabled_colors = (self._start_fields[0].cget("text_color"), self._start_labels[0].cget("text_color"))

        self._start_error = ctk.CTkLabel(f, text="", text_color="red", font=ctk.CTkFont(size=12),
                                         wraplength=460, justify="left")
        self._start_error.pack(anchor="w")
        self._restore_start_selection()
        self._nav_buttons(f, back="token", next_cmd=self._subject_next)

    def _restore_start_selection(self):
        """Select the remembered start mode and propose a date and time.

        The proposal is today's date with the time used last, or the first
        slot of the "now" mode when no time is remembered.
        """
        # An unknown remembered mode (e.g. from a newer version) is ignored
        saved = self._last_sel.get("start_mode")
        known = {mode.value for mode in StartMode}
        self._start_mode_var.set(saved if saved in known else StartMode.NOW.value)

        # Disabled entries ignore insertions, so enable them while filling
        day, clock = default_start_fields(_now(), self._last_sel.get("start_time"))
        values = day.split("/") + clock.split(":")
        for entry, value in zip(self._start_fields, values):
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.insert(0, value)
        self._update_start_fields()

    def _update_start_fields(self):
        """Enable the date and time fields only for the fixed start mode.

        They stay visible in the "now" mode so the page keeps its layout
        when the mode changes.
        """
        enabled = self._start_mode_var.get() == StartMode.FIXED.value
        entry_color, label_color = self._start_enabled_colors if enabled else (_DISABLED_TEXT, _DISABLED_TEXT)
        for entry in self._start_fields:
            entry.configure(state="normal" if enabled else "disabled", text_color=entry_color)
        for label in self._start_labels:
            label.configure(text_color=label_color)
        self._start_error.configure(text="")

    def _advance_start_field(self, index: int, event):
        """Move the cursor to the next start field once the current one is complete.

        Only a typed digit moves on: Tab, arrows or deletions must leave the
        cursor where the user put it.

        Args:
            index: Position of the field that received the key.
            event: The key event, whose char is the typed character.
        """
        entry = self._start_fields[index]
        if not event.char.isdigit() or len(entry.get()) < _START_FIELD_DIGITS[index]:
            return
        if index + 1 < len(self._start_fields):
            following = self._start_fields[index + 1]
            following.focus_set()
            following.select_range(0, "end")
            following.icursor("end")

    def _start_selections(self) -> dict:
        """Return the start choices to remember for the next session.

        In the "now" mode the time chosen in an earlier fixed start is
        kept, so switching back to the fixed mode proposes it again.

        Returns:
            The 'start_mode' and 'start_time' ('hh:mm') entries to save.
        """
        if self._start_at is not None:
            start_time = self._start_at.strftime("%H:%M")
        else:
            start_time = self._last_sel.get("start_time")
        return {"start_mode": self._start_mode.value, "start_time": start_time}

    def _subject_next(self):
        """Validate the subject and the start, then trigger template loading.

        Shows an error indicator if the subject is empty, and an explanation
        if the fixed start cannot be used. Otherwise clears the errors and
        initiates the API call to fetch templates.
        """
        subject = self._subject_entry.get().strip()
        if not subject:
            self._subject_error.configure(text="  ⚠")
            return
        self._subject_error.configure(text="")

        # The fixed start is checked against the current time now, so a
        # mistake is reported on this page. If it gets too close while the
        # user goes through the other steps, the send postpones it
        mode = StartMode(self._start_mode_var.get())
        start_at = None
        if mode == StartMode.FIXED:
            day, month, year, hour, minute = (entry.get().strip() for entry in self._start_fields)
            try:
                start_at = read_fixed_start(f"{day}/{month}/{year}", f"{hour}:{minute}", _now())
            except StartInputError as e:
                self._start_error.configure(text=str(e))
                return
        self._start_error.configure(text="")
        self._start_mode, self._start_at = mode, start_at
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
        """Build the agenda group selection step (step 4).

        Includes a search box because only one page of groups is ever
        loaded: when the wanted group is not among the ones listed,
        searching by name is the only way to reach it.
        """
        f = self._frames["group"]
        ctk.CTkLabel(f, text=t("step_group"), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(PAD, 4))
        ctk.CTkLabel(f, text=t("group_label"), font=ctk.CTkFont(size=13)).pack(anchor="w")

        # Search row; the entry also submits on Enter so the mouse is optional
        search_row = ctk.CTkFrame(f, fg_color="transparent")
        search_row.pack(fill="x", pady=(6, 0))
        self._group_search = ctk.CTkEntry(search_row, placeholder_text=t("group_search_placeholder"), width=320)
        self._group_search.pack(side="left", padx=(0, 8))
        self._group_search.bind("<Return>", lambda _event: self._search_groups())
        ctk.CTkButton(search_row, text=t("btn_search"), width=90,
                      command=self._search_groups).pack(side="left")

        self._group_var = tk.StringVar()
        self._group_list = ctk.CTkScrollableFrame(f, height=230)
        self._group_list.pack(fill="x", pady=(8, 0))
        self._group_count = ctk.CTkLabel(f, text="", text_color="gray", font=ctk.CTkFont(size=12))
        self._group_count.pack(anchor="w")
        self._group_error = ctk.CTkLabel(f, text="", text_color="red", font=ctk.CTkFont(size=12))
        self._group_error.pack(anchor="w")
        self._nav_buttons(f, back="sender", next_cmd=self._group_next)

    def _load_groups(self):
        """Navigate to the group step and show the first page of agenda groups."""
        self._show_frame("group")
        # Always enter the step unfiltered, so a search left over from an
        # earlier campaign does not appear to hide most of the account
        self._group_search.delete(0, "end")
        self._search_groups()

    def _search_groups(self):
        """Fetch a single page of agenda groups honouring the current search text.

        Only one page is requested per search. Fetching every group meant one
        API call per hundred groups, each separated by the rate-limit pause,
        and then one widget per group, which together made accounts with
        thousands of groups unusable.
        """
        name = self._group_search.get().strip()
        self._group_error.configure(text=t("loading"))
        self._group_count.configure(text="")
        # Clear the selection as well: the previously selected group may not
        # be among the results that are about to replace the listing
        self._group_var.set("")
        for w in self._group_list.winfo_children():
            w.destroy()

        def _fetch():
            """Background thread: fetch one page of agendas, then hand it to the UI."""
            try:
                page = MensagiaAgendaRepository(self.client).search(name=name)
            except MensagiaAPIError as e:
                message = t("error_api", error=str(e))
                self._ui_queue.put(lambda: self._group_error.configure(text=message))
                return
            self._ui_queue.put(lambda: self._render_groups(page, name))

        threading.Thread(target=_fetch, daemon=True).start()

    def _render_groups(self, page, name: str):
        """Draw a page of agenda groups in the listing.

        Always invoked on the main thread through after(), because tkinter
        widgets may only be touched from the thread running the event loop.

        Args:
            page: AgendaPage returned by the repository.
            name: Search text that produced the page, used to tell an empty
                account apart from a search that matched nothing.
        """
        self.agendas = page.agendas

        if not page.agendas:
            self._group_error.configure(text=t("group_no_results") if name else t("error_no_groups"))
            return

        self._group_error.configure(text="")
        self._group_count.configure(
            text=t("group_showing", shown=len(page.agendas), total=page.total)
        )

        for a in page.agendas:
            # Show contact count so the user can identify the right group
            label = (f"[{a.id}]  " if self._show_ids else "") + f"{a.name}  ({t('group_contacts', count=a.total_users)})"
            # Empty groups stay visible but unselectable: choosing one leads
            # to a campaign with no recipients at all
            if not a.has_contacts:
                label += f"  -  {t('group_no_contacts')}"
            ctk.CTkRadioButton(
                self._group_list, text=label, variable=self._group_var,
                value=str(a.id), font=ctk.CTkFont(size=13),
                state="normal" if a.has_contacts else "disabled",
            ).pack(anchor="w", pady=2)

        # Restore the previous campaign's group, but only if it is both in
        # this page and still selectable
        saved = self._last_sel.get("agenda_id")
        if saved and any(str(a.id) == saved and a.has_contacts for a in page.agendas):
            self._group_var.set(saved)

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
        """Advance to the summary step and fill it in the background."""
        self._show_frame("summary")
        self._load_summary()

    def _load_summary(self):
        """Show the summary step in a loading state and populate it off the main thread.

        The contact query used to run on the main thread, which froze the
        window while it lasted. Running it in a background thread keeps the
        Back button usable, so a group that turns out to be unusable is never
        a dead end for the interface.
        """
        self._summary_text.configure(text="")
        self._summary_contacts_label.configure(text=t("loading"))
        self._summary_skipped_label.configure(text="")
        self._summary_error.configure(text="")

        # Keep both send actions out of reach until we know there is something
        # to send; an empty campaign is precisely the case that used to hang
        self._dry_run_btn.configure(state="disabled")
        self._send_btn.configure(state="disabled")
        self._can_send = False

        threading.Thread(target=self._fetch_summary, daemon=True).start()

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
        self._summary_error = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=12), text_color="red",
                                           wraplength=460, justify="left")
        self._summary_error.pack(anchor="w", pady=(8, 0))

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

    def _recipient_source(self):
        """Build the source of the recipients chosen in the wizard.

        Returns:
            The RecipientSource of the selected group and attachment field.
        """
        return AgendaRecipientSource(MensagiaContactRepository(self.client),
                                     self.selected_agenda.id, self.selected_field.name)

    def _fetch_summary(self):
        """Background thread: read the chosen recipients for the summary.

        Errors are reported inline rather than in a modal dialog so the user
        can simply go back and pick another group.
        """
        try:
            recipients = self._recipient_source().get_recipients()
        except MensagiaAPIError as e:
            message = t("error_api", error=str(e))
            self._ui_queue.put(lambda: self._show_summary_error(message))
            return
        self._ui_queue.put(lambda: self._build_summary(recipients))

    def _show_summary_error(self, message: str):
        """Report a summary failure, leaving the send actions disabled.

        Args:
            message: Text explaining why the summary could not be produced.
        """
        self._summary_contacts_label.configure(text="")
        self._summary_error.configure(text=message)

    def _build_summary(self, recipients: list):
        """Populate the summary step widgets from the chosen recipients.

        Always invoked on the main thread through after(), because tkinter
        widgets may only be touched from the thread running the event loop.

        Args:
            recipients: Every recipient of the chosen source, sendable or not.
        """
        # The source tells which recipients cannot be sent (no email, no attachment...)
        eligible = [r for r in recipients if r.skip_reason is None]
        source = self._recipient_source()
        subject = self._subject_entry.get().strip()

        # Detect contacts already sent this exact campaign in a previous,
        # interrupted run, and attempts it left unconfirmed (possible
        # duplicates), and let the user decide whether to skip the sent
        # ones or start the whole campaign over again
        campaign = Campaign(source.identity, self.selected_template.id, source.attachment_field,
                            subject, self._start_mode)
        sent_keys = self._send_registry.get_sent_keys(campaign)
        already_sent_count = len([r for r in eligible if r.key in sent_keys])
        uncertain = self._send_registry.get_uncertain_attempts(campaign)
        if already_sent_count or uncertain:
            parts = []
            if already_sent_count:
                parts.append(t("resume_detected", sent=already_sent_count))
            if uncertain:
                parts.append(t("resume_uncertain") + "\n" + "\n".join(resume_uncertain_lines(uncertain, recipients)))
            parts.append(t("resume_continue_prompt"))
            continue_pending = messagebox.askyesno(t("resume_title"), "\n\n".join(parts))
            if not continue_pending:
                self._send_registry.clear(campaign)
                already_sent_count = 0

        # Number of contacts that will actually be sent to in this run
        to_send_count = len(eligible) - already_sent_count

        # Build the multi-line summary text with all selected options
        lines = "\n".join([
            t("summary_from", value=f"{self.selected_sender.name} <{self.selected_sender.email}>" if self.selected_sender.name else self.selected_sender.email),
            t("summary_subject", value=subject),
            t("summary_template", value=self.selected_template.name),
            t("summary_group", value=self.selected_agenda.name),
            t("summary_field", value=self.selected_field.name),
            t("summary_certified", value=t("yes") if self._certified_var.get() else t("no")),
            *summary_start_lines(self._start_mode, self._start_at),
        ])
        self._summary_text.configure(text=lines)
        self._summary_contacts_label.configure(text=t("summary_contacts", count=to_send_count))
        self._summary_skipped_label.configure(text=t("summary_skipped", count=len(recipients) - len(eligible)))

        # Without a single contact there is nothing to send nor to explain in a
        # simulation log, so both actions stay disabled
        if not recipients:
            self._summary_error.configure(text=t("no_eligible_contacts"))
            return

        # A group can hold contacts and still have none that can be written to,
        # when they lack an email address or the selected extra field. Say so,
        # and point to the simulation: its log gives the reason for each one
        if not eligible:
            self._summary_error.configure(text=t("no_eligible_contacts") + "\n" + t("no_eligible_simulate_hint"))

        # Simulating is always possible from here on, but a real send only
        # when this run has an email to send (not the case either when every
        # eligible contact already received this campaign in a previous run)
        self._can_send = to_send_count > 0
        self._dry_run_btn.configure(state="normal")
        if self._can_send:
            self._send_btn.configure(state="normal")

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
        # Remember the theme's own colour so a later successful run can undo
        # the red applied when a send fails
        self._result_color = self._result_label.cget("text_color")
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

        # Propose a fresh date and time: the previous ones may have passed
        self._restore_start_selection()

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
        self._result_label.configure(text="", text_color=self._result_color)

        # Remove any action buttons left over from a previous send
        for w in self._sending_actions.winfo_children():
            w.destroy()

        def _on_progress(current: int, total: int):
            """Update the progress bar and label; called by the use case per contact."""
            self._progress_label.configure(text=t("send_progress", current=current, total=total))
            self._progress_bar.set(current / total if total else 0)
            # Force a UI redraw so the progress is visible immediately
            self.update_idletasks()

        def _run():
            """Background thread: delegate to SendBulkEmailsUseCase and update the UI progressively."""
            try:
                use_case = SendBulkEmailsUseCase(MensagiaEmailSender(self.client))
                _dry_run = dry_run

                # Simulations are logged too, in a file named so it is never
                # mistaken for the log of a real send
                send_logger = SendLogger(simulation=_dry_run)

                result = use_case.execute(
                    from_email=self.selected_sender.email,
                    recipient_source=self._recipient_source(),
                    subject=self._subject_entry.get().strip(),
                    template_id=self.selected_template.id,
                    certified=self._certified_var.get(),
                    attachment_base_url=self._base_url_entry.get().strip() or None,
                    attachment_checker=HttpAttachmentChecker(),
                    dry_run=_dry_run,
                    logger=send_logger,
                    progress_callback=_on_progress,
                    send_registry=self._send_registry,
                    start_mode=self._start_mode,
                    start_at=self._start_at,
                )

                # Build the result text, appending per-contact error details if any
                error_msgs = "\n".join(
                    t("send_error", email=item["recipient"].email, error=item["error"])
                    for item in result.errors
                )
                key = "dry_run_complete" if _dry_run else "send_complete"
                result_text = t(key, sent=len(result.sent), skipped=len(result.skipped), errors=len(result.errors))
                if error_msgs:
                    result_text += "\n\n" + error_msgs

                # Warn about sends that may have been scheduled without
                # confirmation, with the recipient and slot to check in the portal
                uncertain_msgs = result_uncertain_lines(result.uncertain)
                if uncertain_msgs:
                    result_text += "\n\n" + "\n\n".join(uncertain_msgs)
                result_text += f"\n\n{t('log_saved', path=str(send_logger.log_path))}"

                self._result_label.configure(text=result_text)
                self._progress_bar.set(1)

                # Persist the selections so they are pre-selected on the next run,
                # and keep them for a new send in this same session
                selections = {
                    "template_id": str(self.selected_template.id),
                    "sender_id": str(self.selected_sender.id),
                    "agenda_id": str(self.selected_agenda.id),
                    "field_id": str(self.selected_field.id),
                    "certified": self._certified_var.get(),
                    **self._start_selections(),
                }
                save_last_selections(selections)
                self._last_sel = selections

                self._show_send_actions(_dry_run, would_send=len(result.sent))

            except MensagiaAPIError as e:
                message = t("error_api", error=str(e))
                self._ui_queue.put(lambda: self._fail_send(message))
            except Exception as e:
                # Any other failure would otherwise kill the thread silently and
                # leave the user staring at an idle progress bar with no way out
                message = str(e)
                self._ui_queue.put(lambda: self._fail_send(message))

        threading.Thread(target=_run, daemon=True).start()

    def _show_send_actions(self, dry_run: bool, would_send: int):
        """Offer the buttons that follow a finished send or simulation.

        After a simulation the user can go back to the summary or, when the
        simulation found emails to send, go ahead with the real send. After
        a real send only a new campaign makes sense.

        Args:
            dry_run: True when the finished run was a simulation.
            would_send: Number of emails the run sent, or would send in a
                simulation.
        """
        if dry_run:
            # The real send is offered only when the summary enabled it (a
            # simulation is also allowed when there is nothing to send) and
            # the simulation found at least one email to send: when every
            # eligible contact failed, for instance because no attachment
            # can be downloaded, a real send would fail the same way. The
            # summary keeps its Send button, since the attachments may have
            # been fixed in the meantime
            if self._can_send and would_send:
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
            ctk.CTkButton(
                self._sending_actions, text=t("btn_new_send"),
                command=self._reset_for_new_send
            ).pack(side="left")

    def _fail_send(self, message: str):
        """Report a failed send and give the user a way out of the sending step.

        The sending step has no navigation of its own; its buttons are added
        once a run finishes. Without this, a failure left the step with an
        error message and nothing to click.

        Args:
            message: Text to show in place of the send result.
        """
        self._result_label.configure(text=message, text_color="red")
        for w in self._sending_actions.winfo_children():
            w.destroy()
        ctk.CTkButton(
            self._sending_actions, text=t("btn_back_to_summary"),
            command=lambda: self._show_frame("summary"),
            fg_color="gray", hover_color="#555"
        ).pack(side="left")

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
