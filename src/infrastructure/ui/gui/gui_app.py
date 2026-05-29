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
from src.domain.attachment_url import resolve_attachment_url
from src.infrastructure.http.http_attachment_checker import HttpAttachmentChecker


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

PAD = 16
WINDOW_W = 620
WINDOW_H = 560


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(t("app_title"))
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.resizable(False, False)

        self._show_ids = load_show_ids()
        self.client: MensagiaClient | None = None
        self.templates = []
        self.senders = []
        self.agendas = []
        self.extra_fields = []

        self.selected_template = None
        self.selected_sender = None
        self.selected_agenda = None
        self.selected_field = None

        self._build_language_bar()
        self._build_frames()
        self._show_frame("token")

    # ── Language bar ──────────────────────────────────────────────────────────

    def _build_language_bar(self):
        bar = ctk.CTkFrame(self, height=36, fg_color="#f0f0f0", corner_radius=0)
        bar.pack(fill="x", side="top")
        ctk.CTkLabel(bar, text=t("language_label"), font=ctk.CTkFont(size=12)).pack(side="left", padx=PAD, pady=6)
        self._lang_var = tk.StringVar(value=get_language())
        for code, name in language_names().items():
            ctk.CTkRadioButton(
                bar, text=name, variable=self._lang_var, value=code,
                font=ctk.CTkFont(size=12), command=self._on_language_change
            ).pack(side="left", padx=6, pady=6)

    def _on_language_change(self):
        set_language(self._lang_var.get())
        self._rebuild_ui()

    def _rebuild_ui(self):
        for w in self.winfo_children():
            w.destroy()
        self.__init__()

    # ── Frame container ────────────────────────────────────────────────────────

    def _build_frames(self):
        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        self._frames = {}
        for name in ("token", "subject", "template", "sender", "group", "field", "certified", "summary", "sending"):
            frame = ctk.CTkFrame(self._container, fg_color="transparent")
            frame.grid(row=0, column=0, sticky="nsew")
            self._frames[name] = frame
        self._container.grid_rowconfigure(0, weight=1)
        self._container.grid_columnconfigure(0, weight=1)

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
        self._frames[name].tkraise()

    # ── Step 0: Token ──────────────────────────────────────────────────────────

    def _build_token_frame(self):
        f = self._frames["token"]
        ctk.CTkLabel(f, text=t("token_label"), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(PAD, 4))
        self._token_entry = ctk.CTkEntry(f, width=460, show="*", placeholder_text="•••••••••••••••••")
        self._token_entry.pack(anchor="w")

        preloaded = load_api_token()
        if preloaded:
            self._token_entry.insert(0, preloaded)

        ctk.CTkLabel(f, text=t("base_url_label"), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(PAD, 4))
        self._base_url_entry = ctk.CTkEntry(f, width=460, placeholder_text=t("base_url_placeholder"))
        self._base_url_entry.pack(anchor="w")
        preloaded_base = load_attachment_base_url()
        if preloaded_base:
            self._base_url_entry.insert(0, preloaded_base)

        self._token_status = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=12), text_color="gray")
        self._token_status.pack(anchor="w", pady=(6, 0))

        btn_frame = ctk.CTkFrame(f, fg_color="transparent")
        btn_frame.pack(anchor="w", pady=(PAD, 0))
        ctk.CTkButton(btn_frame, text=t("btn_validate"), command=self._validate_token).pack(side="left", padx=(0, 8))
        self._token_next_btn = ctk.CTkButton(btn_frame, text=t("btn_next"), state="disabled", command=self._token_next)
        self._token_next_btn.pack(side="left")

    def _validate_token(self):
        token = self._token_entry.get().strip()
        if not token:
            return
        self._token_status.configure(text=t("loading"), text_color="gray")
        self.update_idletasks()

        def _check():
            client = MensagiaClient(token)
            valid = client.validate_token()
            if valid:
                self.client = client
                self._token_status.configure(text=t("token_ok"), text_color="green")
                self._token_next_btn.configure(state="normal")
            else:
                self._token_status.configure(text=t("token_invalid"), text_color="red")
                self._token_next_btn.configure(state="disabled")

        threading.Thread(target=_check, daemon=True).start()

    def _token_next(self):
        self._show_frame("subject")

    # ── Step 1: Subject ────────────────────────────────────────────────────────

    def _build_subject_frame(self):
        f = self._frames["subject"]
        ctk.CTkLabel(f, text=t("step_subject"), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(PAD, 4))
        ctk.CTkLabel(f, text=t("subject_label"), font=ctk.CTkFont(size=13)).pack(anchor="w")
        self._subject_entry = ctk.CTkEntry(f, width=460, placeholder_text=t("subject_placeholder"))
        self._subject_entry.pack(anchor="w", pady=(4, 0))
        self._subject_error = ctk.CTkLabel(f, text="", text_color="red", font=ctk.CTkFont(size=12))
        self._subject_error.pack(anchor="w")
        self._nav_buttons(f, back="token", next_cmd=self._subject_next)

    def _subject_next(self):
        subject = self._subject_entry.get().strip()
        if not subject:
            self._subject_error.configure(text="  ⚠")
            return
        self._subject_error.configure(text="")
        self._load_templates()

    # ── Step 2: Template ───────────────────────────────────────────────────────

    def _build_template_frame(self):
        f = self._frames["template"]
        ctk.CTkLabel(f, text=t("step_template"), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(PAD, 4))
        ctk.CTkLabel(f, text=t("template_label"), font=ctk.CTkFont(size=13)).pack(anchor="w")
        self._template_var = tk.StringVar()
        self._template_list = ctk.CTkScrollableFrame(f, height=260)
        self._template_list.pack(fill="x", pady=(4, 0))
        self._template_error = ctk.CTkLabel(f, text="", text_color="red", font=ctk.CTkFont(size=12))
        self._template_error.pack(anchor="w")
        self._nav_buttons(f, back="subject", next_cmd=self._template_next)

    def _load_templates(self):
        self._show_frame("template")
        self._template_error.configure(text=t("loading"))
        for w in self._template_list.winfo_children():
            w.destroy()

        def _fetch():
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
            except MensagiaAPIError as e:
                self._template_error.configure(text=t("error_api", error=str(e)))

        threading.Thread(target=_fetch, daemon=True).start()

    def _template_next(self):
        val = self._template_var.get()
        if not val:
            self._template_error.configure(text="  ⚠")
            return
        self.selected_template = next(t for t in self.templates if str(t.id) == val)
        self._template_error.configure(text="")
        self._load_senders()

    # ── Step 3: Sender ─────────────────────────────────────────────────────────

    def _build_sender_frame(self):
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
        self._show_frame("sender")
        self._sender_error.configure(text=t("loading"))
        for w in self._sender_list.winfo_children():
            w.destroy()

        def _fetch():
            try:
                self.senders = MensagiaEmailAddressRepository(self.client).get_all()
                if not self.senders:
                    self._sender_error.configure(text=t("error_no_senders"))
                    return
                self._sender_error.configure(text="")
                for s in self.senders:
                    label = s.email + (f"  ({s.name})" if s.name else "")
                    ctk.CTkRadioButton(
                        self._sender_list, text=label, variable=self._sender_var,
                        value=str(s.id), font=ctk.CTkFont(size=13)
                    ).pack(anchor="w", pady=2)
            except MensagiaAPIError as e:
                self._sender_error.configure(text=t("error_api", error=str(e)))

        threading.Thread(target=_fetch, daemon=True).start()

    def _sender_next(self):
        val = self._sender_var.get()
        if not val:
            self._sender_error.configure(text="  ⚠")
            return
        self.selected_sender = next(s for s in self.senders if str(s.id) == val)
        self._sender_error.configure(text="")
        self._load_groups()

    # ── Step 4: Group ──────────────────────────────────────────────────────────

    def _build_group_frame(self):
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
        self._show_frame("group")
        self._group_error.configure(text=t("loading"))
        for w in self._group_list.winfo_children():
            w.destroy()

        def _fetch():
            try:
                self.agendas = MensagiaAgendaRepository(self.client).get_all()
                if not self.agendas:
                    self._group_error.configure(text=t("error_no_groups"))
                    return
                self._group_error.configure(text="")
                for a in self.agendas:
                    label = (f"[{a.id}]  " if self._show_ids else "") + f"{a.name}  ({t('group_contacts', count=a.total_users)})"
                    ctk.CTkRadioButton(
                        self._group_list, text=label, variable=self._group_var,
                        value=str(a.id), font=ctk.CTkFont(size=13)
                    ).pack(anchor="w", pady=2)
            except MensagiaAPIError as e:
                self._group_error.configure(text=t("error_api", error=str(e)))

        threading.Thread(target=_fetch, daemon=True).start()

    def _group_next(self):
        val = self._group_var.get()
        if not val:
            self._group_error.configure(text="  ⚠")
            return
        self.selected_agenda = next(a for a in self.agendas if str(a.id) == val)
        self._group_error.configure(text="")
        self._load_fields()

    # ── Step 5: Extra field ────────────────────────────────────────────────────

    def _build_field_frame(self):
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
        self._show_frame("field")
        self._field_error.configure(text=t("loading"))
        for w in self._field_list.winfo_children():
            w.destroy()

        def _fetch():
            try:
                self.extra_fields = MensagiaExtraFieldRepository(self.client).get_all()
                if not self.extra_fields:
                    self._field_error.configure(text=t("error_no_fields"))
                    return
                self._field_error.configure(text="")
                for ef in self.extra_fields:
                    ctk.CTkRadioButton(
                        self._field_list, text=f"[{ef.id}]  {ef.name}" if self._show_ids else ef.name, variable=self._field_var,
                        value=str(ef.id), font=ctk.CTkFont(size=13)
                    ).pack(anchor="w", pady=2)
            except MensagiaAPIError as e:
                self._field_error.configure(text=t("error_api", error=str(e)))

        threading.Thread(target=_fetch, daemon=True).start()

    def _field_next(self):
        val = self._field_var.get()
        if not val:
            self._field_error.configure(text="  ⚠")
            return
        self.selected_field = next(ef for ef in self.extra_fields if str(ef.id) == val)
        self._field_error.configure(text="")
        self._show_frame("certified")

    # ── Step 6: Certified ──────────────────────────────────────────────────────

    def _build_certified_frame(self):
        f = self._frames["certified"]
        ctk.CTkLabel(f, text=t("step_certified"), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(PAD, 4))
        ctk.CTkLabel(f, text=t("certified_label"), font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(8, 4))
        self._certified_var = tk.IntVar(value=0)
        ctk.CTkRadioButton(f, text=t("certified_no"), variable=self._certified_var, value=0,
                           font=ctk.CTkFont(size=13)).pack(anchor="w", pady=2)
        ctk.CTkRadioButton(f, text=t("certified_yes"), variable=self._certified_var, value=1,
                           font=ctk.CTkFont(size=13)).pack(anchor="w", pady=2)
        self._nav_buttons(f, back="field", next_cmd=self._certified_next)

    def _certified_next(self):
        self._build_summary()
        self._show_frame("summary")

    # ── Step 7: Summary ────────────────────────────────────────────────────────

    def _build_summary_frame(self):
        f = self._frames["summary"]
        self._summary_title = ctk.CTkLabel(f, text=t("step_summary"), font=ctk.CTkFont(size=15, weight="bold"))
        self._summary_title.pack(anchor="w", pady=(PAD, 8))
        self._summary_text = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=13), justify="left")
        self._summary_text.pack(anchor="w")
        self._summary_contacts_label = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=13, weight="bold"))
        self._summary_contacts_label.pack(anchor="w", pady=(8, 0))
        self._summary_skipped_label = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=12), text_color="gray")
        self._summary_skipped_label.pack(anchor="w")

        btn_frame = ctk.CTkFrame(f, fg_color="transparent")
        btn_frame.pack(anchor="w", pady=(PAD, 0))
        ctk.CTkButton(btn_frame, text=t("btn_back"), command=lambda: self._show_frame("certified"),
                      fg_color="gray", hover_color="#555").pack(side="left", padx=(0, 8))
        self._dry_run_btn = ctk.CTkButton(btn_frame, text=t("btn_dry_run"),
                                          command=lambda: self._do_send(dry_run=True),
                                          fg_color="#888", hover_color="#666")
        self._dry_run_btn.pack(side="left", padx=(0, 8))
        self._send_btn = ctk.CTkButton(btn_frame, text=t("btn_send"),
                                       command=lambda: self._do_send(dry_run=False),
                                       fg_color="#e05", hover_color="#c03")
        self._send_btn.pack(side="left")

    def _build_summary(self):
        try:
            contacts = MensagiaContactRepository(self.client).get_by_group(
                self.selected_agenda.id, in_mail_blacklist=False
            )
        except MensagiaAPIError as e:
            messagebox.showerror("Error", t("error_api", error=str(e)))
            return

        eligible = [
            c for c in contacts
            if c.email and c.extra_fields.get(self.selected_field.name)
        ]

        lines = "\n".join([
            t("summary_from", value=self.selected_sender.email),
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
        f = self._frames["sending"]
        ctk.CTkLabel(f, text=t("sending"), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(PAD, 4))
        self._progress_bar = ctk.CTkProgressBar(f, width=460)
        self._progress_bar.pack(anchor="w", pady=(8, 4))
        self._progress_bar.set(0)
        self._progress_label = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=13))
        self._progress_label.pack(anchor="w")
        self._result_label = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=13), wraplength=460, justify="left")
        self._result_label.pack(anchor="w", pady=(PAD, 0))

    def _do_send(self, dry_run: bool = False):
        self._show_frame("sending")
        self._progress_bar.set(0)
        self._progress_label.configure(text="")
        self._result_label.configure(text="")

        def _run():
            try:
                contact_repo = MensagiaContactRepository(self.client)
                email_sender_adapter = MensagiaEmailSender(self.client)
                use_case = SendBulkEmailsUseCase(contact_repo, email_sender_adapter)
                attachment_base_url = self._base_url_entry.get().strip() or None
                attachment_checker = HttpAttachmentChecker()
                _dry_run = dry_run

                contacts = contact_repo.get_by_group(self.selected_agenda.id, in_mail_blacklist=False)
                eligible = [
                    c for c in contacts
                    if c.email and c.extra_fields.get(self.selected_field.name)
                ]
                total = len(eligible)

                from src.domain.scheduling import calculate_start_dates
                from src.domain.entities.email_message import EmailMessage
                from datetime import datetime

                start_dates = calculate_start_dates(total)
                sent, errors = [], []

                for i, (contact, start_date) in enumerate(zip(eligible, start_dates), 1):
                    self._progress_label.configure(text=t("send_progress", current=i, total=total))
                    self._progress_bar.set(i / total if total else 0)
                    self.update_idletasks()

                    try:
                        attachment_url = resolve_attachment_url(
                            contact.extra_fields[self.selected_field.name],
                            attachment_base_url,
                        )
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
                        if not _dry_run:
                            email_sender_adapter.send(message)
                        sent.append(contact)
                    except Exception as e:
                        errors.append((contact, str(e)))

                skipped = [c for c in contacts if c not in eligible]
                error_msgs = "\n".join(
                    t("send_error", email=c.email, error=err) for c, err in errors
                )
                key = "dry_run_complete" if _dry_run else "send_complete"
                result_text = t(key, sent=len(sent), skipped=len(skipped), errors=len(errors))
                if error_msgs:
                    result_text += "\n\n" + error_msgs
                self._result_label.configure(text=result_text)
                self._progress_bar.set(1)

            except MensagiaAPIError as e:
                self._result_label.configure(text=t("error_api", error=str(e)), text_color="red")

        threading.Thread(target=_run, daemon=True).start()

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _nav_buttons(self, frame, back: str, next_cmd):
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(anchor="w", pady=(PAD, 0))
        if back:
            ctk.CTkButton(btn_frame, text=t("btn_back"), command=lambda: self._show_frame(back),
                          fg_color="gray", hover_color="#555").pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_frame, text=t("btn_next"), command=next_cmd).pack(side="left")


def run():
    env_lang = load_language()
    set_language(env_lang if env_lang else detect_system_language())
    app = App()
    app.mainloop()
