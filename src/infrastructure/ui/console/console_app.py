import getpass
import sys
from src.infrastructure.api.mensagia_client import MensagiaClient, MensagiaAPIError
from src.infrastructure.api.mensagia_agenda_repository import MensagiaAgendaRepository
from src.infrastructure.api.mensagia_contact_repository import MensagiaContactRepository
from src.infrastructure.api.mensagia_email_address_repository import MensagiaEmailAddressRepository
from src.infrastructure.api.mensagia_email_template_repository import MensagiaEmailTemplateRepository
from src.infrastructure.api.mensagia_extra_field_repository import MensagiaExtraFieldRepository
from src.infrastructure.api.mensagia_email_sender import MensagiaEmailSender
from src.application.use_cases.send_bulk_emails import SendBulkEmailsUseCase
from src.infrastructure.ui.i18n import t, set_language, language_names, detect_system_language
from src.infrastructure.config.settings import load_api_token, load_language, load_attachment_base_url, load_show_ids
from src.domain.attachment_url import resolve_attachment_url
from src.infrastructure.http.http_attachment_checker import HttpAttachmentChecker
from src.infrastructure.logging.send_logger import SendLogger


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


def _resolve_attachment_base_url(eligible: list, extra_field) -> str | None:
    """Determine the base URL to use for resolving relative attachment paths.

    If all contacts already have absolute attachment URLs no base URL is
    needed. When at least one contact has a relative value, the function
    tries to load it from the environment; if it is not configured there
    it prompts the user to enter one interactively.

    Args:
        eligible: List of Contact objects that will receive an email.
        extra_field: The ExtraField whose value contains the attachment path.

    Returns:
        The base URL string, or None if all attachment values are already
        absolute URLs.
    """
    # Check whether any contact has a relative (non-absolute) attachment value
    needs_base = any(
        not v.startswith(("http://", "https://"))
        for c in eligible
        if (v := c.extra_fields.get(extra_field.name))
    )

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
    Step 1 — Email subject input.
    Step 2 — Email template selection.
    Step 3 — Sender address selection.
    Step 4 — Agenda group selection.
    Step 5 — Extra field (attachment URL field) selection.
    Step 6 — Certified email option.
    Step 7 — Contact count summary and confirmation.
    Step 8 — Bulk send (real or dry-run).

    Exits with sys.exit(1) on unrecoverable API errors and sys.exit(0)
    when the user cancels or there are no eligible contacts.
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

    # ── Step 4: Agenda group selection ────────────────────────────────────────
    print(f"\n--- {t('step_group')} ---")
    print(f"  {t('loading')}")
    try:
        agenda = _select_agenda(client, show_ids)
    except MensagiaAPIError as e:
        print(f"  {t('error_api', error=str(e))}")
        sys.exit(1)

    # ── Step 5: Extra field selection ─────────────────────────────────────────
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

    # ── Step 6: Certified email option ────────────────────────────────────────
    print(f"\n--- {t('step_certified')} ---")
    certified = 1 if _yes_no(f"  {t('certified_label')}") else 0

    # ── Step 7: Contact summary and confirmation ───────────────────────────────
    print(f"\n--- {t('step_summary')} ---")
    print(f"  {t('loading')}")
    try:
        contacts = MensagiaContactRepository(client).get_by_group(agenda.id, in_mail_blacklist=False)
    except MensagiaAPIError as e:
        print(f"  {t('error_api', error=str(e))}")
        sys.exit(1)

    # Determine which contacts are eligible (have both email and attachment value)
    eligible = [
        c for c in contacts
        if c.email and c.extra_fields.get(extra_field.name)
    ]
    skipped_count = len(contacts) - len(eligible)

    # Resolve the base URL for relative attachment paths, prompting if needed
    attachment_base_url = _resolve_attachment_base_url(eligible, extra_field)

    # Print the summary for the user to review before committing to send
    sender_display = f"{sender.name} <{sender.email}>" if sender.name else sender.email
    print(f"\n  {t('summary_from', value=sender_display)}")
    print(f"  {t('summary_subject', value=subject)}")
    print(f"  {t('summary_template', value=template.name)}")
    print(f"  {t('summary_group', value=agenda.name)}")
    print(f"  {t('summary_field', value=extra_field.name)}")
    print(f"  {t('summary_certified', value=t('yes') if certified else t('no'))}")
    print(f"  {t('summary_contacts', count=len(eligible))}")
    print(f"  {t('summary_skipped', count=skipped_count)}")

    # Nothing to send — say why and exit cleanly without error. The group may
    # well hold contacts: they can all lack an email address or the extra field
    if not eligible:
        print(f"\n  {t('no_eligible_contacts')}")
        sys.exit(0)

    action = _confirm_action()
    if action is None:
        sys.exit(0)

    # ── Step 8: Bulk send ──────────────────────────────────────────────────────
    dry_run = action == "dry_run"
    contact_repo = MensagiaContactRepository(client)
    email_sender = MensagiaEmailSender(client)
    use_case = SendBulkEmailsUseCase(contact_repo, email_sender)

    # Create a logger only for real sends; dry-runs produce no log file
    send_logger = SendLogger() if not dry_run else None

    print(f"\n  {t('sending')}")
    result = use_case.execute(
        from_email=sender.email,
        group_id=agenda.id,
        subject=subject,
        template_id=template.id,
        extra_field=extra_field,
        certified=certified,
        attachment_base_url=attachment_base_url,
        attachment_checker=HttpAttachmentChecker(),
        dry_run=dry_run,
        logger=send_logger,
    )

    # Report any per-contact errors to the console
    for error_item in result.errors:
        print(f"  {t('send_error', email=error_item['contact'].email, error=error_item['error'])}")

    # Print the final outcome summary
    key = "dry_run_complete" if dry_run else "send_complete"
    print(f"\n  {t(key, sent=len(result.sent), skipped=len(result.skipped), errors=len(result.errors))}")

    if send_logger:
        print(f"  {t('log_saved', path=str(send_logger.log_path))}")
