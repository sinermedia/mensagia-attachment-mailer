import hashlib
import json
from datetime import datetime
from pathlib import Path

from src.domain.entities.campaign import Campaign
from src.domain.ports.send_registry import SendRegistry
from src.domain.scheduling import StartMode
from src.infrastructure.config.app_paths import user_data_dir


# Name of the JSON file that persists per-campaign send progress
_FILE = "send_progress.json"


def _default_registry_path() -> Path:
    """Return the default absolute path to the send_progress.json file.

    Lives in the shared user data directory, like last_selections.json:
    next to the .exe on Windows (so progress survives app updates), in
    ~/Mensagia Mailer on macOS, or at the repository root in development
    mode (see user_data_dir).

    Returns:
        Path object pointing to the default send_progress.json location.
    """
    return user_data_dir() / _FILE


def _campaign_key(campaign: Campaign) -> str:
    """Build a stable, filesystem- and JSON-key-safe identifier for a campaign.

    Hashing avoids issues with special characters in the subject and
    keeps the registry file's keys short. The start mode is only added
    when it is not StartMode.NOW, so campaigns recorded by earlier
    versions, which always started now, keep their key. The source of an
    agenda group is its ID, the value earlier versions used in its place.

    Args:
        campaign: Campaign the progress belongs to.

    Returns:
        A hexadecimal SHA-1 digest identifying this exact campaign.
    """
    raw = f"{campaign.source}|{campaign.template_id}|{campaign.field_name}|{campaign.subject}"
    if campaign.start_mode != StartMode.NOW:
        raw += f"|{campaign.start_mode.value}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


class JsonSendRegistry(SendRegistry):
    """Local JSON file implementation of the SendRegistry port.

    Persists, for each campaign, the keys of the recipients that already
    received an email, the latest send slot attempted, and the attempts whose outcome
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

    def _get_record(self, campaign: Campaign) -> dict:
        """Return the stored record of a campaign, or an empty dict when there is none.

        Args:
            campaign: Campaign the progress belongs to.

        Returns:
            The campaign's record dict. Callers only read from it.
        """
        return self._load().get(_campaign_key(campaign)) or {}

    def _update_record(self, campaign: Campaign, change) -> None:
        """Load the file, apply *change* to the campaign's record and save it.

        Args:
            campaign: Campaign the progress belongs to.
            change: Callable receiving the mutable record dict.
        """
        data = self._load()
        record = data.setdefault(_campaign_key(campaign), {
            "source": campaign.source,
            "template_id": campaign.template_id,
            "field": campaign.field_name,
            "subject": campaign.subject,
            "start_mode": campaign.start_mode.value,
        })

        # Fill every key so *change* never deals with missing ones, including
        # on records written by earlier versions of the application, whose
        # numeric contact IDs become the keys of agenda recipients
        record.setdefault("sent_keys", [])
        for contact_id in record.pop("sent_contact_ids", []):
            if str(contact_id) not in record["sent_keys"]:
                record["sent_keys"].append(str(contact_id))
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
    def _remove_attempt(record: dict, key: str, start_date: datetime) -> None:
        """Remove one attempt from the record, dropping the recipient once it has none left.

        Args:
            record: Mutable campaign record.
            key: Key of the recipient whose attempt is resolved.
            start_date: Slot of the attempt to remove.
        """
        attempts = record["uncertain_attempts"]
        slot = start_date.isoformat()
        if slot in attempts.get(key, []):
            attempts[key].remove(slot)
            if not attempts[key]:
                del attempts[key]

    def get_sent_keys(
        self, campaign: Campaign
    ) -> set[str]:
        """Return the keys of the recipients already sent an email in this campaign.

        Records of earlier versions list numeric contact IDs under another
        name; they are returned as the keys of those agenda recipients.

        Args:
            campaign: Campaign the progress belongs to.

        Returns:
            A set of recipient keys, empty when the campaign has no record.
        """
        record = self._get_record(campaign)
        legacy = (str(contact_id) for contact_id in record.get("sent_contact_ids", []))
        return set(record.get("sent_keys", [])) | set(legacy)

    def get_last_start_date(
        self, campaign: Campaign
    ) -> datetime | None:
        """Return the latest send slot ever attempted in this campaign.

        Args:
            campaign: Campaign the progress belongs to.

        Returns:
            The latest recorded slot, or None when there is none.
        """
        value = self._get_record(campaign).get("last_start_date")
        return datetime.fromisoformat(value) if value else None

    def get_uncertain_attempts(
        self, campaign: Campaign
    ) -> dict[str, list[datetime]]:
        """Return the attempts of this campaign whose outcome is unknown.

        Args:
            campaign: Campaign the progress belongs to.

        Returns:
            A dict mapping recipient keys to their unresolved send slots.
        """
        attempts = self._get_record(campaign).get("uncertain_attempts", {})
        return {key: [datetime.fromisoformat(s) for s in slots] for key, slots in attempts.items()}

    def mark_attempt(
        self, campaign: Campaign,
        key: str, start_date: datetime,
    ) -> None:
        """Record that an email is about to be sent to a recipient for a given slot.

        Args:
            campaign: Campaign the progress belongs to.
            key: Key of the recipient about to be emailed.
            start_date: Send slot requested for this email.
        """
        def change(record):
            record["uncertain_attempts"].setdefault(key, []).append(start_date.isoformat())
            self._advance_last_start_date(record, start_date)

        self._update_record(campaign, change)

    def mark_sent(
        self, campaign: Campaign,
        key: str, start_date: datetime,
    ) -> None:
        """Record that a recipient successfully received an email in this campaign.

        Args:
            campaign: Campaign the progress belongs to.
            key: Key of the recipient that was successfully emailed.
            start_date: Send slot the email was scheduled for.
        """
        def change(record):
            # Avoid duplicate entries if the same recipient is marked more than once
            if key not in record["sent_keys"]:
                record["sent_keys"].append(key)
            self._remove_attempt(record, key, start_date)
            self._advance_last_start_date(record, start_date)

        self._update_record(campaign, change)

    def discard_attempt(
        self, campaign: Campaign,
        key: str, start_date: datetime,
    ) -> None:
        """Resolve an attempt known not to have scheduled any email.

        Args:
            campaign: Campaign the progress belongs to.
            key: Key of the recipient whose attempt failed.
            start_date: Send slot of the failed attempt.
        """
        self._update_record(
            campaign,
            lambda record: self._remove_attempt(record, key, start_date),
        )

    def clear(self, campaign: Campaign) -> None:
        """Forget everything recorded for this campaign.

        Args:
            campaign: Campaign the progress belongs to.
        """
        data = self._load()
        key = _campaign_key(campaign)
        if key in data:
            del data[key]
            self._save(data)
