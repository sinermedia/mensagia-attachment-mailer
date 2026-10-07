import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

from src.domain.ports.send_registry import SendRegistry


# Name of the JSON file that persists per-campaign send progress
_FILE = "send_progress.json"


def _default_registry_path() -> Path:
    """Return the default absolute path to the send_progress.json file.

    Follows the same location convention as last_selections.json: next to
    the executable when bundled with PyInstaller (so progress survives app
    updates), or at the repository root in development mode.

    Returns:
        Path object pointing to the default send_progress.json location.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / _FILE
    return Path(__file__).parents[3] / _FILE


def _campaign_key(group_id: int, template_id: int, field_name: str, subject: str) -> str:
    """Build a stable, filesystem- and JSON-key-safe identifier for a campaign.

    A campaign is uniquely defined by the tuple (group, template, extra
    field, subject) — the same choices a user makes when configuring a
    send. Hashing avoids issues with special characters in the subject and
    keeps the registry file's keys short.

    Args:
        group_id: ID of the target agenda group.
        template_id: ID of the email template used.
        field_name: Name of the extra field holding the attachment URL.
        subject: Email subject line.

    Returns:
        A hexadecimal SHA-1 digest identifying this exact campaign.
    """
    raw = f"{group_id}|{template_id}|{field_name}|{subject}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


class JsonSendRegistry(SendRegistry):
    """Local JSON file implementation of the SendRegistry port.

    Persists, for each campaign, the contact IDs that already received an
    email, the latest send slot attempted, and the attempts whose outcome
    is still unknown. Every write goes to disk immediately so progress is
    never lost if the application is closed mid-send. Datetimes are stored
    as ISO-8601 strings; records written by earlier versions without the
    scheduling keys are read with empty defaults.

    Attributes:
        path: Absolute Path of the JSON file backing this registry.
    """

    def __init__(self, path: Path | None = None):
        """Initialise the registry, optionally overriding the storage path.

        Args:
            path: Path to the JSON file to use. Defaults to the standard
                location resolved by _default_registry_path(). Tests pass
                an explicit tmp_path-based file to isolate state.
        """
        self.path = path if path is not None else _default_registry_path()

    def _load(self) -> dict:
        """Read and parse the registry file, tolerating absence or corruption.

        Returns:
            The parsed registry dict, or an empty dict if the file does not
            exist or its content is not valid JSON.
        """
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self, data: dict) -> None:
        """Write the registry dict to disk, ignoring write failures.

        Progress tracking is best-effort: a read-only filesystem or missing
        permissions must never crash a bulk send in progress.

        Args:
            data: The full registry dict to persist.
        """
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _get_record(self, group_id: int, template_id: int, field_name: str, subject: str) -> dict:
        """Return the stored record of a campaign, or an empty dict when there is none.

        Args:
            group_id: ID of the target agenda group.
            template_id: ID of the email template used.
            field_name: Name of the extra field holding the attachment URL.
            subject: Email subject line.

        Returns:
            The campaign's record dict. Callers only read from it.
        """
        return self._load().get(_campaign_key(group_id, template_id, field_name, subject)) or {}

    def _update_record(self, group_id: int, template_id: int, field_name: str, subject: str, change) -> None:
        """Load the file, apply *change* to the campaign's record and save it.

        Args:
            group_id: ID of the target agenda group.
            template_id: ID of the email template used.
            field_name: Name of the extra field holding the attachment URL.
            subject: Email subject line.
            change: Callable receiving the mutable record dict.
        """
        data = self._load()
        record = data.setdefault(_campaign_key(group_id, template_id, field_name, subject), {
            "group_id": group_id,
            "template_id": template_id,
            "field": field_name,
            "subject": subject,
        })

        # Fill every key so *change* never deals with missing ones, including
        # on records written by earlier versions of the application
        record.setdefault("sent_contact_ids", [])
        record.setdefault("last_start_date", None)
        record.setdefault("uncertain_attempts", {})

        change(record)
        self._save(data)

    @staticmethod
    def _advance_last_start_date(record: dict, start_date: datetime) -> None:
        """Move the record's last start date forward to *start_date* if it is later.

        Args:
            record: Mutable campaign record.
            start_date: Slot just attempted or sent.
        """
        current = record["last_start_date"]
        if current is None or datetime.fromisoformat(current) < start_date:
            record["last_start_date"] = start_date.isoformat()

    @staticmethod
    def _remove_attempt(record: dict, contact_id: int, start_date: datetime) -> None:
        """Remove one attempt from the record, dropping the contact once it has none left.

        Args:
            record: Mutable campaign record.
            contact_id: ID of the contact whose attempt is resolved.
            start_date: Slot of the attempt to remove.
        """
        # JSON object keys are always strings, so contact IDs are stored as such
        attempts = record["uncertain_attempts"]
        key = str(contact_id)
        slot = start_date.isoformat()
        if slot in attempts.get(key, []):
            attempts[key].remove(slot)
            if not attempts[key]:
                del attempts[key]

    def get_sent_contact_ids(
        self, group_id: int, template_id: int, field_name: str, subject: str
    ) -> set[int]:
        """Return the IDs of contacts already sent an email in this campaign.

        Args:
            group_id: ID of the target agenda group.
            template_id: ID of the email template used.
            field_name: Name of the extra field holding the attachment URL.
            subject: Email subject line.

        Returns:
            A set of contact IDs, empty when the campaign has no record.
        """
        record = self._get_record(group_id, template_id, field_name, subject)
        return set(record.get("sent_contact_ids", []))

    def get_last_start_date(
        self, group_id: int, template_id: int, field_name: str, subject: str
    ) -> datetime | None:
        """Return the latest send slot ever attempted in this campaign.

        Args:
            group_id: ID of the target agenda group.
            template_id: ID of the email template used.
            field_name: Name of the extra field holding the attachment URL.
            subject: Email subject line.

        Returns:
            The latest recorded slot, or None when there is none.
        """
        value = self._get_record(group_id, template_id, field_name, subject).get("last_start_date")
        return datetime.fromisoformat(value) if value else None

    def get_uncertain_attempts(
        self, group_id: int, template_id: int, field_name: str, subject: str
    ) -> dict[int, list[datetime]]:
        """Return the attempts of this campaign whose outcome is unknown.

        Args:
            group_id: ID of the target agenda group.
            template_id: ID of the email template used.
            field_name: Name of the extra field holding the attachment URL.
            subject: Email subject line.

        Returns:
            A dict mapping contact IDs to their unresolved send slots.
        """
        attempts = self._get_record(group_id, template_id, field_name, subject).get("uncertain_attempts", {})
        return {int(cid): [datetime.fromisoformat(s) for s in slots] for cid, slots in attempts.items()}

    def mark_attempt(
        self, group_id: int, template_id: int, field_name: str, subject: str,
        contact_id: int, start_date: datetime,
    ) -> None:
        """Record that an email is about to be sent to a contact for a given slot.

        Args:
            group_id: ID of the target agenda group.
            template_id: ID of the email template used.
            field_name: Name of the extra field holding the attachment URL.
            subject: Email subject line.
            contact_id: ID of the contact about to be emailed.
            start_date: Send slot requested for this email.
        """
        def change(record):
            record["uncertain_attempts"].setdefault(str(contact_id), []).append(start_date.isoformat())
            self._advance_last_start_date(record, start_date)

        self._update_record(group_id, template_id, field_name, subject, change)

    def mark_sent(
        self, group_id: int, template_id: int, field_name: str, subject: str,
        contact_id: int, start_date: datetime,
    ) -> None:
        """Record that a contact successfully received an email in this campaign.

        Args:
            group_id: ID of the target agenda group.
            template_id: ID of the email template used.
            field_name: Name of the extra field holding the attachment URL.
            subject: Email subject line.
            contact_id: ID of the contact that was successfully emailed.
            start_date: Send slot the email was scheduled for.
        """
        def change(record):
            # Avoid duplicate entries if the same contact is marked more than once
            if contact_id not in record["sent_contact_ids"]:
                record["sent_contact_ids"].append(contact_id)
            self._remove_attempt(record, contact_id, start_date)
            self._advance_last_start_date(record, start_date)

        self._update_record(group_id, template_id, field_name, subject, change)

    def discard_attempt(
        self, group_id: int, template_id: int, field_name: str, subject: str,
        contact_id: int, start_date: datetime,
    ) -> None:
        """Resolve an attempt known not to have scheduled any email.

        Args:
            group_id: ID of the target agenda group.
            template_id: ID of the email template used.
            field_name: Name of the extra field holding the attachment URL.
            subject: Email subject line.
            contact_id: ID of the contact whose attempt failed.
            start_date: Send slot of the failed attempt.
        """
        self._update_record(
            group_id, template_id, field_name, subject,
            lambda record: self._remove_attempt(record, contact_id, start_date),
        )

    def clear(self, group_id: int, template_id: int, field_name: str, subject: str) -> None:
        """Forget everything recorded for this campaign.

        Args:
            group_id: ID of the target agenda group.
            template_id: ID of the email template used.
            field_name: Name of the extra field holding the attachment URL.
            subject: Email subject line.
        """
        data = self._load()
        key = _campaign_key(group_id, template_id, field_name, subject)
        if key in data:
            del data[key]
            self._save(data)
