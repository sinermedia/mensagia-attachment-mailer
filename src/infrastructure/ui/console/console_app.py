import getpass
import sys
from datetime import datetime, time
from src.infrastructure.api.mensagia_client import MensagiaClient, MensagiaAPIError
from src.infrastructure.api.mensagia_agenda_repository import MensagiaAgendaRepository
from src.infrastructure.api.mensagia_contact_repository import MensagiaContactRepository
from src.infrastructure.api.mensagia_email_address_repository import MensagiaEmailAddressRepository
from src.infrastructure.api.mensagia_email_template_repository import MensagiaEmailTemplateRepository
from src.infrastructure.api.mensagia_extra_field_repository import MensagiaExtraFieldRepository
from src.infrastructure.api.mensagia_email_sender import MensagiaEmailSender
from src.infrastructure.recipients.agenda_recipient_source import AgendaRecipientSource
from src.infrastructure.recipients.file_recipient_source import FileRecipientSource
from src.infrastructure.files.table_file import TableFileError, list_sheets, read_table
from src.infrastructure.ui.recipient_file import clean_path, file_error_message, file_summary_lines
from src.application.use_cases.send_bulk_emails import SendBulkEmailsUseCase
from src.infrastructure.ui.i18n import t, set_language, language_names, detect_system_language
from src.infrastructure.config.settings import load_api_token, load_language, load_attachment_base_url, load_show_ids
from src.domain.attachment_url import resolve_attachment_url
from src.infrastructure.http.http_attachment_checker import HttpAttachmentChecker
from src.infrastructure.logging.send_logger import SendLogger
from src.domain.entities.campaign import Campaign
from src.infrastructure.persistence.json_send_registry import JsonSendRegistry
from src.infrastructure.ui.uncertain_sends import resume_uncertain_lines, result_uncertain_lines
from src.infrastructure.ui.start_time import (
    StartInputError, default_start_fields, read_contact_start_time, read_fixed_start, summary_start_lines,
)
from src.infrastructure.ui.send_summary import date_format_label, day_lines, repeated_lines, skipped_lines
from src.domain.date_input import DateFormat, parse_date, parse_time
from src.domain.scheduling import StartMode, preview_days, split_by_send_date
from src.domain.file_rows import rows_on_several_dates


def _choose_language():
    """Set the active UI language for this console session.

    If a language is configured via the MENSAGIA_LANGUAGE env variable it
    is applied immediately. Otherwise the user is presented with a numbered
    list and asked to choose. Falls back to OS locale detection if the input
    is not a valid number.
    """
    # Environment variable takes priority — no prompt needed
    env_lang = load_language()
    if env_lang:
        set_language(env_lang)
        return

    # Display numbered language options and read the user's choice
    names = language_names()
    print("\n  Language / Idioma / Llengua:")
    options = list(names.items())
    for i, (code, name) in enumerate(options, 1):
        print(f"  {i}. {name}")
    choice = input("  > ").strip()

    if choice.isdigit() and 1 <= int(choice) <= len(options):
        code = options[int(choice) - 1][0]
        set_language(code)
    else:
        # Invalid input — fall back to OS locale detection
        set_language(detect_system_language())


def _resolve_attachment_base_url(eligible: list) -> str | None:
    """Determine the base URL to use for resolving relative attachment paths.

    If all recipients already have absolute attachment URLs no base URL is
    needed. When at least one recipient has a relative value, the function
    tries to load it from the environment; if it is not configured there
    it prompts the user to enter one interactively.

    Args:
        eligible: List of Recipient objects that will receive an email.

    Returns:
        The base URL string, or None if all attachment values are already
        absolute URLs.
    """
    # Check whether any recipient has a relative (non-absolute) attachment value
    needs_base = any(not r.attachment.startswith(("http://", "https://")) for r in eligible)

    if not needs_base:
        # All values are absolute — a base URL is not required
        return load_attachment_base_url()

    # At least one relative value exists — try environment first
    base_url = load_attachment_base_url()
    if base_url:
        return base_url

    # Not in environment — prompt the user until a non-empty value is entered
    print(f"\n  {t('enter_base_url')}")
    while True:
        url = input("  > ").strip()
        if url:
            return url


def _select_from_list(prompt: str, items: list, display_fn) -> object:
    """Present a numbered list of items and return the one the user selects.

    Keeps prompting until the user enters a valid number within the range
    of available options.

    Args:
        prompt: Header text printed above the list.
        items: The list of objects to choose from.
        display_fn: Callable that takes one item and returns its display string.

    Returns:
        The selected item from *items*.
    """
    print(f"\n{prompt}")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {display_fn(item)}")

    # Keep asking until a valid numeric choice is provided
    while True:
        choice = input("  > ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(items):
            return items[int(choice) - 1]
        print(f"  (1-{len(items)})")


def _ask_with_default(prompt: str, default: str, parse, error_key: str) -> str:
    """Ask for a value, proposing a default that Enter accepts.

    Keeps asking until *parse* accepts the answer, explaining the error
    each time.

    Args:
        prompt: Question shown to the user.
        default: Value proposed between brackets and used on Enter.
        parse: Callable that raises ValueError for an unreadable answer.
        error_key: Translation key of the message shown on an error.

    Returns:
        The accepted answer, as typed (or the default).
    """
    while True:
        answer = input(f"  {prompt} [{default}]: ").strip() or default
        try:
            parse(answer)
            return answer
        except ValueError:
            print(f"  {t(error_key)}")


def _choose_start(now: datetime) -> tuple[StartMode, datetime | None, time | None]:
    """Ask when the emails must go out.

    With a fixed start, the date and the time are asked separately and
    each is asked again until it can be read. If the combination is too
    soon or too far ahead, both are asked again, proposing the values
    just typed so only the wrong part has to be changed. On each contact's
    date only the time is asked, since the day comes from each contact.

    Args:
        now: Current date and time, used for the proposals and the limits.

    Returns:
        The chosen start mode, the date and time of a fixed start (None
        otherwise) and the time of a send by contact date (None otherwise).
    """
    labels = {
        StartMode.NOW: t("start_now"),
        StartMode.FIXED: t("start_fixed"),
        StartMode.CONTACT_DATE: t("start_contact_date"),
    }
    mode = _select_from_list(t("start_label"), list(labels), labels.get)
    if mode == StartMode.NOW:
        return mode, None, None

    date_text, time_text = default_start_fields(now, None)
    if mode == StartMode.CONTACT_DATE:
        time_text = _ask_with_default(t("start_time_prompt"), time_text, parse_time, "start_error_invalid_time")
        return mode, None, read_contact_start_time(time_text)

    while True:
        date_text = _ask_with_default(t("start_date_prompt"), date_text, parse_date, "start_error_invalid_date")
        time_text = _ask_with_default(t("start_time_prompt"), time_text, parse_time, "start_error_invalid_time")
        try:
            return mode, read_fixed_start(date_text, time_text, now), None
        except StartInputError as e:
            print(f"  {e}")


def _select_agenda(client, show_ids: bool):
    """Let the user pick an agenda from a paged, searchable listing.

    Kept separate from _select_from_list because agendas are the only list
    that can hold thousands of entries: instead of loading them all, one
    page is fetched at a time and the prompt doubles as a search box.
    Anything that is not a valid position number is treated as a name to
    search for, which also covers the case of a group that is not in the
    first page. A group whose name is a digit within the listed range will
    therefore select that position rather than start a search; this is
    accepted as a rare and harmless ambiguity.

    Args:
        client: Authenticated MensagiaClient used to query the API.
        show_ids: Whether to prefix each entry with the agenda id.

    Returns:
        The Agenda the user selected. Agendas without contacts can be seen
        but not selected, since they would produce a campaign with no
        recipients.

    Raises:
        MensagiaAPIError: If any of the API calls fails.
    """
    repository = MensagiaAgendaRepository(client)
    page = repository.search()

    while True:
        print(f"\n{t('group_label')}")
        if not page.agendas:
            print(f"  {t('group_no_results')}")
        for i, agenda in enumerate(page.agendas, 1):
            prefix = f"[{agenda.id}] " if show_ids else ""
            # Mark empty agendas explicitly so the refusal below is not a surprise
            state = f" - {t('group_no_contacts')}" if not agenda.has_contacts else ""
            print(f"  {i}. {prefix}{agenda.name} ({t('group_contacts', count=agenda.total_users)}){state}")
        print(f"  {t('group_showing', shown=len(page.agendas), total=page.total)}")
        print(f"  {t('group_console_hint')}")

        choice = input("  > ").strip()

        # An empty line is not a search for everything: just redraw the listing
        if not choice:
            continue

        # Only a position number within the current listing selects an agenda;
        # everything else is a name to search for
        if choice.isdigit() and 1 <= int(choice) <= len(page.agendas):
            selected = page.agendas[int(choice) - 1]
            if not selected.has_contacts:
                print(f"  {t('group_empty_not_selectable')}")
                continue
            return selected

        page = repository.search(name=choice)


def _choose_source() -> str:
    """Ask where the recipients come from.

    Returns:
        'agenda' for a group of the Mensagia agenda, 'file' for an Excel or
        CSV file.
    """
    labels = {"agenda": t("source_agenda"), "file": t("source_file")}
    return _select_from_list(t("source_label"), ["agenda", "file"], labels.get)


def _select_date_format() -> DateFormat:
    """Ask the format of the send dates written as text.

    Returns:
        The chosen format.
    """
    return _select_from_list(t("date_format_label"), list(DateFormat), date_format_label)


def _select_date_field(extra_fields: list, attachment_field, show_ids: bool) -> tuple:
    """Let the user pick the custom field holding each contact's send day, and its format.

    The attachment field is not offered, since one field cannot hold both.

    Args:
        extra_fields: Every custom field of the account.
        attachment_field: The field already chosen for the attachment.
        show_ids: Whether to prefix each field with its id.

    Returns:
        The chosen ExtraField and DateFormat.
    """
    others = [f for f in extra_fields if f.name != attachment_field.name]
    if not others:
        print(f"  {t('error_no_date_fields')}")
        sys.exit(1)
    field = _select_from_list(t("date_field_label"), others, lambda x: f"[{x.id}] {x.name}" if show_ids else x.name)
    return field, _select_date_format()


def _select_file(with_date: bool = False) -> FileRecipientSource:
    """Let the user pick the recipients file, its sheet and its columns.

    The path is typed or pasted; the quotes added by Windows' "Copy as
    path" are removed. The sheet is only asked for when the workbook has
    more than one. Whenever the file cannot be used, the reason is shown
    and a path is asked for again, since the fix is usually in the file.

    Args:
        with_date: True in the contact date start mode, to also ask for the
            column holding the send day and the format of its dates.

    Returns:
        The source reading the chosen file, sheet and columns.
    """
    # A send by contact date needs a third column, for the send day
    needed = 3 if with_date else 2
    while True:
        path = clean_path(input(f"  {t('file_prompt')} "))
        if not path:
            continue
        try:
            sheets = list_sheets(path)
            sheet = _select_from_list(t("sheet_label"), sheets, str) if len(sheets) > 1 else (sheets or [None])[0]
            table = read_table(path, sheet)
        except TableFileError as e:
            print(f"  {file_error_message(e)}")
            continue
        if with_date and len(table.columns) < needed:
            print(f"  {t('file_error_no_date_column')}")
            continue
        break

    # The same column cannot hold two things, so the columns already chosen
    # are not offered again
    email_column = _select_from_list(t("email_column_label"), table.columns, str)
    others = [c for c in table.columns if c != email_column]
    attachment_column = _select_from_list(t("attachment_column_label"), others, str)
    if not with_date:
        return FileRecipientSource(path, sheet, email_column, attachment_column)

    others = [c for c in others if c != attachment_column]
    date_column = _select_from_list(t("date_column_label"), others, str)
    print(f"  {t('date_format_hint')}")
    return FileRecipientSource(path, sheet, email_column, attachment_column,
                               date_column=date_column, date_format=_select_date_format())


def _confirm_action() -> str | None:
    """Ask the user whether to send, simulate, or cancel the operation.

    Accepts the translated 'yes' word, common affirmative shortcuts, the
    'sim' word (simulate/dry-run) in all supported languages, and the
    translated 'no' word plus common negative shortcuts. Keeps prompting
    until a recognised answer is given.

    Returns:
        'send' if the user confirms a real send,
        'dry_run' if the user requests a simulation,
        None if the user cancels.
    """
    sim = t("sim").lower()
    while True:
        answer = input(f"\n  {t('confirm_send')} [{t('yes')}/{t('sim')}/{t('no')}]: ").strip().lower()
        if answer in (t("yes").lower(), "s", "si", "sí", "yes", "y", "1", "bai"):
            return "send"
        if answer in (sim, "sim", "simular", "simulatu", "simulate"):
            return "dry_run"
        if answer in (t("no").lower(), "no", "n", "0", "ez"):
            return None


def _choose_action(can_send: bool) -> str | None:
    """Ask the user what to do with the campaign shown in the summary.

    When at least one contact can be sent to, the usual send / simulate /
    cancel question is asked. Otherwise a real send would do nothing, so
    only a simulation is offered: its log explains why each contact was
    left out.

    Args:
        can_send: True when this run has at least one email to send.

    Returns:
        'send' if the user confirms a real send,
        'dry_run' if the user requests a simulation,
        None if the user cancels.
    """
    if can_send:
        return _confirm_action()
    return "dry_run" if _yes_no(f"\n  {t('confirm_dry_run_only')}") else None


def _yes_no(prompt: str) -> bool:
    """Ask a yes/no question and return the boolean result.

    Accepts the translated 'yes' and 'no' words as well as common language-
    neutral shortcuts. Keeps prompting until a recognised answer is given.

    Args:
        prompt: The question text to display to the user.

    Returns:
        True if the user answered yes; False if the user answered no.
    """
    while True:
        answer = input(f"{prompt} [{t('yes')}/{t('no')}]: ").strip().lower()
        if answer in (t("yes").lower(), "s", "si", "sí", "yes", "y", "1", "bai"):
            return True
        if answer in (t("no").lower(), "no", "n", "0", "ez"):
            return False


def run():
    """Entry point for the console (CLI) interface of the application.

    Guides the user through a sequential wizard:
    Step 0 — Language selection and API token validation.
    Step 1 — Email subject input, start time (now or a fixed date) and
             recipient source (agenda group or file).
    Step 2 — Email template selection.
    Step 3 — Sender address selection.
    Step 4 — Agenda group selection, or file, sheet and columns selection.
    Step 5 — Extra field (attachment URL field) selection, for a group.
    Step 6 — Certified email option.
    Step 7 — Recipient count summary and confirmation (simulation only when
             there is nothing to send).
    Step 8 — Bulk send (real or dry-run), both logged to a file.

    Exits with sys.exit(1) on unrecoverable API or file errors and
    sys.exit(0) when the user cancels or the source yields no recipients.
    """
    print("=" * 60)
    print("  MENSAGIA ATTACHMENT MAILER")
    print("=" * 60)

    _choose_language()
    show_ids = load_show_ids()

    # ── Step 0: API token validation ──────────────────────────────────────────
    # Try to load the token from the environment or .env file first
    api_token = load_api_token()
    client = None
    if api_token:
        client = MensagiaClient(api_token)
        if not client.validate_token():
            print(f"\n  {t('token_invalid')}")
            client = None

    # If the token from .env is missing or invalid, prompt the user
    while client is None:
        print(f"\n  {t('enter_token')}")
        api_token = getpass.getpass("  > ")
        if not api_token.strip():
            continue
        client = MensagiaClient(api_token.strip())
        if client.validate_token():
            print(f"  {t('token_ok')}")
        else:
            print(f"  {t('token_invalid')}")
            client = None

    # ── Step 1: Email subject ──────────────────────────────────────────────────
    print(f"\n--- {t('step_subject')} ---")
    subject = ""
    while not subject.strip():
        subject = input(f"  {t('subject_label')} ").strip()

    # ── Step 1b: Start time ───────────────────────────────────────────────────
    # A fixed start is checked against the current time right away; if it
    # gets too close before the send starts, the send postpones it
    print(f"\n--- {t('step_start')} ---")
    start_mode, start_at, start_time = _choose_start(datetime.now())
    by_day = start_mode == StartMode.CONTACT_DATE

    # ── Step 1c: Recipient source ─────────────────────────────────────────────
    source_kind = _choose_source()

    # ── Step 2: Template selection ─────────────────────────────────────────────
    print(f"\n--- {t('step_template')} ---")
    print(f"  {t('loading')}")
    try:
        templates = MensagiaEmailTemplateRepository(client).get_all()
    except MensagiaAPIError as e:
        print(f"  {t('error_api', error=str(e))}")
        sys.exit(1)
    if not templates:
        print(f"  {t('error_no_templates')}")
        sys.exit(1)
    template = _select_from_list(t("template_label"), templates, lambda x: f"[{x.id}] {x.name}" if show_ids else x.name)

    # ── Step 3: Sender address selection ──────────────────────────────────────
    print(f"\n--- {t('step_sender')} ---")
    print(f"  {t('loading')}")
    try:
        senders = MensagiaEmailAddressRepository(client).get_all()
    except MensagiaAPIError as e:
        print(f"  {t('error_api', error=str(e))}")
        sys.exit(1)
    if not senders:
        print(f"  {t('error_no_senders')}")
        sys.exit(1)
    sender = _select_from_list(t("sender_label"), senders, lambda x: f"{x.email}" + (f" ({x.name})" if x.name else ""))

    if source_kind == "agenda":
        # ── Step 4: Agenda group selection ────────────────────────────────────
        print(f"\n--- {t('step_group')} ---")
        print(f"  {t('loading')}")
        try:
            agenda = _select_agenda(client, show_ids)
        except MensagiaAPIError as e:
            print(f"  {t('error_api', error=str(e))}")
            sys.exit(1)

        # ── Step 5: Extra field selection ─────────────────────────────────────
        print(f"\n--- {t('step_field')} ---")
        print(f"  {t('loading')}")
        try:
            extra_fields = MensagiaExtraFieldRepository(client).get_all()
        except MensagiaAPIError as e:
            print(f"  {t('error_api', error=str(e))}")
            sys.exit(1)
        if not extra_fields:
            print(f"  {t('error_no_fields')}")
            sys.exit(1)
        extra_field = _select_from_list(t("field_label"), extra_fields, lambda x: f"[{x.id}] {x.name}" if show_ids else x.name)
        source_lines = [t("summary_group", value=agenda.name), t("summary_field", value=extra_field.name)]
        if by_day:
            # ── Step 5b: Send date field and format ───────────────────────────
            print(f"\n--- {t('step_date_field')} ---")
            date_field, date_format = _select_date_field(extra_fields, extra_field, show_ids)
            source = AgendaRecipientSource(MensagiaContactRepository(client), agenda.id, extra_field.name,
                                           date_field.name, date_format)
            source_lines.append(t("summary_date_field", value=date_field.name, format=date_format_label(date_format)))
        else:
            source = AgendaRecipientSource(MensagiaContactRepository(client), agenda.id, extra_field.name)
    else:
        # ── Step 4: File, sheet and columns selection ─────────────────────────
        print(f"\n--- {t('step_file')} ---")
        source = _select_file(with_date=by_day)
        source_lines = file_summary_lines(source.path, source.sheet, source.email_column, source.attachment_column)
        if by_day:
            source_lines.append(t("summary_date_column", value=source.date_column,
                                  format=date_format_label(source.date_format)))

    # Texts that count contacts of a group, or rows of a file
    rows = source_kind == "file"

    # ── Step 6: Certified email option ────────────────────────────────────────
    print(f"\n--- {t('step_certified')} ---")
    certified = 1 if _yes_no(f"  {t('certified_label')}") else 0

    # ── Step 7: Contact summary and confirmation ───────────────────────────────
    print(f"\n--- {t('step_summary')} ---")
    print(f"  {t('loading')}")
    try:
        recipients = source.get_recipients()
    except MensagiaAPIError as e:
        print(f"  {t('error_api', error=str(e))}")
        sys.exit(1)
    except TableFileError as e:
        print(f"  {file_error_message(e)}")
        sys.exit(1)

    # The source tells which recipients cannot be sent (no email, no attachment...)
    eligible = [r for r in recipients if r.skip_reason is None]

    # Resolve the base URL for relative attachment paths, prompting if needed.
    # A file is then read again with it: a relative path and the full URL it
    # resolves to are the same file, which changes the duplicate rows and
    # the keys the progress is recorded with
    attachment_base_url = _resolve_attachment_base_url(eligible)
    if rows and attachment_base_url:
        source.attachment_base_url = attachment_base_url
        try:
            recipients = source.get_recipients()
        except TableFileError as e:
            print(f"  {file_error_message(e)}")
            sys.exit(1)
        eligible = [r for r in recipients if r.skip_reason is None]
    skipped = [r for r in recipients if r.skip_reason is not None]

    # Detect contacts already sent this exact campaign in a previous,
    # interrupted run, and attempts it left unconfirmed (possible
    # duplicates), and let the user decide whether to skip the sent ones
    # or start the whole campaign over again
    send_registry = JsonSendRegistry()
    campaign = Campaign(source.identity, template.id, source.attachment_field, subject, start_mode,
                        source.date_field)
    sent_keys = send_registry.get_sent_keys(campaign)
    already_sent_count = len([r for r in eligible if r.key in sent_keys])
    uncertain = send_registry.get_uncertain_attempts(campaign)
    if already_sent_count or uncertain:
        if already_sent_count:
            print(f"\n  {t('resume_detected_rows' if rows else 'resume_detected', sent=already_sent_count)}")
        if uncertain:
            print(f"\n  {t('resume_uncertain')}")
            for line in resume_uncertain_lines(uncertain, recipients):
                print(f"    {line}")
        if not _yes_no(f"  {t('resume_continue_prompt_rows' if rows else 'resume_continue_prompt')}"):
            send_registry.clear(campaign)
            sent_keys = set()
            already_sent_count = 0

    # Recipients that will actually be sent to in this run. Sending by
    # contact date, the same checks as the send leave out the days that
    # have passed or are too far, and the schedule of each day is estimated
    pending = [r for r in eligible if r.key not in sent_keys]
    preview = []
    if by_day:
        now = datetime.now()
        pending, out_of_range = split_by_send_date(pending, start_time, now)
        skipped += out_of_range
        preview = preview_days([r.send_date for r in pending], start_time, now,
                               send_registry.get_last_start_dates_by_day(campaign))
    to_send_count = len(pending)

    # Print the summary for the user to review before committing to send
    sender_display = f"{sender.name} <{sender.email}>" if sender.name else sender.email
    print(f"\n  {t('summary_from', value=sender_display)}")
    print(f"  {t('summary_subject', value=subject)}")
    print(f"  {t('summary_template', value=template.name)}")
    for line in source_lines:
        print(f"  {line}")
    print(f"  {t('summary_certified', value=t('yes') if certified else t('no'))}")
    for line in summary_start_lines(start_mode, start_at, start_time):
        print(f"  {line}")
    print(f"  {t('summary_rows' if rows else 'summary_contacts', count=to_send_count)}")
    for line in skipped_lines(skipped, rows):
        print(f"  {line}")
    for line in day_lines(preview):
        print(f"  {line}")

    # The same address and attachment on several days are all sent: warn,
    # so the extra ones can be removed in the portal if they are a mistake
    repeated = repeated_lines(rows_on_several_dates(pending)) if rows and by_day else []
    if repeated:
        print()
    for line in repeated:
        print(f"  {line}")

    # Without a single recipient there is nothing to send nor to explain in
    # a simulation log, so exit cleanly without error
    if not recipients:
        print(f"\n  {t('no_eligible_rows' if rows else 'no_eligible_contacts')}")
        sys.exit(0)

    # The source may hold recipients and still have none that can be written
    # to, when they all lack a valid address, an attachment or a usable send
    # day: say why. In that case, or when every eligible recipient already
    # received this campaign in a previous run, only a simulation is offered,
    # since its log is the way to find out why each one was left out
    if not pending and not already_sent_count:
        print(f"\n  {t('no_eligible_rows' if rows else 'no_eligible_contacts')}")
    action = _choose_action(can_send=to_send_count > 0)
    if action is None:
        sys.exit(0)

    # ── Step 8: Bulk send ──────────────────────────────────────────────────────
    dry_run = action == "dry_run"
    use_case = SendBulkEmailsUseCase(MensagiaEmailSender(client))

    # Simulations are logged too, in a file named so it is never mistaken
    # for the log of a real send
    send_logger = SendLogger(simulation=dry_run)

    # The file is read again for the send, so it may have become unusable
    # since the summary (renamed column, file saved while being edited...)
    print(f"\n  {t('sending')}")
    try:
        result = use_case.execute(
            from_email=sender.email,
            recipient_source=source,
            subject=subject,
            template_id=template.id,
            certified=certified,
            attachment_base_url=attachment_base_url,
            attachment_checker=HttpAttachmentChecker(),
            dry_run=dry_run,
            logger=send_logger,
            send_registry=send_registry,
            start_mode=start_mode,
            start_at=start_at,
            start_time=start_time,
        )
    except TableFileError as e:
        print(f"  {file_error_message(e)}")
        sys.exit(1)

    # Report any per-recipient errors to the console
    for error_item in result.errors:
        print(f"  {t('send_error', email=error_item['recipient'].email, error=error_item['error'])}")

    # Print the final outcome summary
    key = "dry_run_complete" if dry_run else "send_complete"
    print(f"\n  {t(key, sent=len(result.sent), skipped=len(result.skipped), errors=len(result.errors))}")

    # Warn about sends that may have been scheduled without confirmation,
    # with the recipient and slot to check in the Mensagia portal
    for line in result_uncertain_lines(result.uncertain):
        print(f"\n  {line}")

    print(f"  {t('log_saved', path=str(send_logger.log_path))}")
