import hashlib
import json
import sys
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

    Persists, for each campaign, the set of contact IDs that already
    received an email. Every mark_sent() call writes the file immediately
    so progress is never lost if the application is closed mid-send.

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
        key = _campaign_key(group_id, template_id, field_name, subject)
        record = self._load().get(key)
        return set(record["sent_contact_ids"]) if record else set()

    def mark_sent(
        self, group_id: int, template_id: int, field_name: str, subject: str, contact_id: int
    ) -> None:
        """Record that a contact successfully received an email in this campaign.

        Args:
            group_id: ID of the target agenda group.
            template_id: ID of the email template used.
            field_name: Name of the extra field holding the attachment URL.
            subject: Email subject line.
            contact_id: ID of the contact that was successfully emailed.
        """
        data = self._load()
        key = _campaign_key(group_id, template_id, field_name, subject)
        record = data.setdefault(key, {
            "group_id": group_id,
            "template_id": template_id,
            "field": field_name,
            "subject": subject,
            "sent_contact_ids": [],
        })
        # Avoid duplicate entries if the same contact is marked more than once
        if contact_id not in record["sent_contact_ids"]:
            record["sent_contact_ids"].append(contact_id)
        self._save(data)

    def clear(self, group_id: int, template_id: int, field_name: str, subject: str) -> None:
        """Forget all recorded sends for this campaign.

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
