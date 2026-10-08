import hashlib
from datetime import datetime
import json
from src.domain.entities.campaign import Campaign
from src.infrastructure.persistence.json_send_registry import JsonSendRegistry


# Fixed send slot used when the scheduled date itself is irrelevant to the test
T = datetime(2024, 1, 15, 14, 40, 0)


class TestJsonSendRegistry:
    """Tests for the local JSON-backed implementation of the SendRegistry port."""

    def test_returns_empty_set_when_no_file_exists(self, tmp_path):
        """No prior sends are reported when the registry file does not exist yet."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        assert registry.get_sent_contact_ids(Campaign(10, 5, "attachment_url", "Hello")) == set()

    def test_marked_contact_is_returned_by_get_sent_contact_ids(self, tmp_path):
        """A contact ID recorded with mark_sent(, T) is later returned for the same campaign."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_sent(Campaign(10, 5, "attachment_url", "Hello"), 42, T)
        assert registry.get_sent_contact_ids(Campaign(10, 5, "attachment_url", "Hello")) == {42}

    def test_multiple_contacts_accumulate_in_the_same_campaign(self, tmp_path):
        """Marking several contacts in the same campaign accumulates all their IDs."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_sent(Campaign(10, 5, "attachment_url", "Hello"), 1, T)
        registry.mark_sent(Campaign(10, 5, "attachment_url", "Hello"), 2, T)
        registry.mark_sent(Campaign(10, 5, "attachment_url", "Hello"), 3, T)
        assert registry.get_sent_contact_ids(Campaign(10, 5, "attachment_url", "Hello")) == {1, 2, 3}

    def test_marking_the_same_contact_twice_does_not_duplicate(self, tmp_path):
        """Calling mark_sent(, T) twice for the same contact keeps a single entry."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_sent(Campaign(10, 5, "attachment_url", "Hello"), 1, T)
        registry.mark_sent(Campaign(10, 5, "attachment_url", "Hello"), 1, T)
        assert registry.get_sent_contact_ids(Campaign(10, 5, "attachment_url", "Hello")) == {1}

    def test_different_campaigns_are_tracked_independently(self, tmp_path):
        """Sends recorded for one campaign do not leak into a campaign with a different subject."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_sent(Campaign(10, 5, "attachment_url", "Hello"), 1, T)
        registry.mark_sent(Campaign(10, 5, "attachment_url", "Goodbye"), 2, T)
        assert registry.get_sent_contact_ids(Campaign(10, 5, "attachment_url", "Hello")) == {1}
        assert registry.get_sent_contact_ids(Campaign(10, 5, "attachment_url", "Goodbye")) == {2}

    def test_clear_removes_the_campaign_record(self, tmp_path):
        """clear() forgets all sent IDs for a campaign so it starts fresh again."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_sent(Campaign(10, 5, "attachment_url", "Hello"), 1, T)
        registry.clear(Campaign(10, 5, "attachment_url", "Hello"))
        assert registry.get_sent_contact_ids(Campaign(10, 5, "attachment_url", "Hello")) == set()

    def test_clear_on_untracked_campaign_does_not_raise(self, tmp_path):
        """Clearing a campaign that was never recorded is a harmless no-op."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.clear(Campaign(10, 5, "attachment_url", "Hello"))  # must not raise

    def test_clear_does_not_affect_other_campaigns(self, tmp_path):
        """Clearing one campaign leaves other campaigns' records intact."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_sent(Campaign(10, 5, "attachment_url", "Hello"), 1, T)
        registry.mark_sent(Campaign(20, 5, "attachment_url", "Hello"), 2, T)
        registry.clear(Campaign(10, 5, "attachment_url", "Hello"))
        assert registry.get_sent_contact_ids(Campaign(20, 5, "attachment_url", "Hello")) == {2}

    def test_mark_sent_persists_to_disk_immediately(self, tmp_path):
        """Each mark_sent(, T) call writes to disk right away, surviving a new instance."""
        path = tmp_path / "send_progress.json"
        JsonSendRegistry(path).mark_sent(Campaign(10, 5, "attachment_url", "Hello"), 1, T)
        # A second, independent instance reading the same file sees the update
        assert JsonSendRegistry(path).get_sent_contact_ids(Campaign(10, 5, "attachment_url", "Hello")) == {1}

    def test_returns_empty_set_on_corrupt_file(self, tmp_path):
        """A corrupted registry file is treated as empty instead of raising."""
        path = tmp_path / "send_progress.json"
        path.write_text("not valid json", encoding="utf-8")
        registry = JsonSendRegistry(path)
        assert registry.get_sent_contact_ids(Campaign(10, 5, "attachment_url", "Hello")) == set()

    def test_mark_sent_is_silent_on_write_error(self, tmp_path):
        """A write error (e.g. missing parent directory that cannot be created) does not raise."""
        bad_path = tmp_path / "ro" / "nested" / "send_progress.json"
        registry = JsonSendRegistry(bad_path)
        # Simulate an unwritable location by pointing at a path whose parent is a file
        blocker = tmp_path / "ro"
        blocker.write_text("i am a file, not a directory", encoding="utf-8")
        registry.mark_sent(Campaign(10, 5, "attachment_url", "Hello"), 1, T)  # must not raise

    def test_default_path_used_when_none_given(self, tmp_path, monkeypatch):
        """When no explicit path is given, the module's default path resolver is used."""
        default_file = tmp_path / "send_progress.json"
        monkeypatch.setattr(
            "src.infrastructure.persistence.json_send_registry._default_registry_path",
            lambda: default_file,
        )
        registry = JsonSendRegistry()
        registry.mark_sent(Campaign(10, 5, "attachment_url", "Hello"), 1, T)
        assert json.loads(default_file.read_text(encoding="utf-8"))

    def test_default_path_lives_in_user_data_dir(self, tmp_path, monkeypatch):
        """By default the registry file is placed in the shared user data directory."""
        monkeypatch.setattr("src.infrastructure.persistence.json_send_registry.user_data_dir", lambda: tmp_path)
        assert JsonSendRegistry().path == tmp_path / "send_progress.json"


class TestJsonSendRegistryScheduling:
    """Tests for tracking the last scheduled slot of a campaign.

    A resumed campaign continues right after the last slot queued by the
    previous run, so the registry must remember the latest one reliably.
    """

    def test_last_start_date_is_none_when_campaign_has_no_record(self, tmp_path):
        """A campaign without any recorded attempt has no last start date."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        assert registry.get_last_start_date(Campaign(10, 5, "attachment_url", "Hello")) is None

    def test_mark_attempt_records_last_start_date(self, tmp_path):
        """Marking an attempt stores its slot as the campaign's last start date."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_attempt(Campaign(10, 5, "attachment_url", "Hello"), 1, T)
        assert registry.get_last_start_date(Campaign(10, 5, "attachment_url", "Hello")) == T

    def test_last_start_date_keeps_the_latest_slot(self, tmp_path):
        """An earlier slot recorded afterwards never moves the last start date backwards."""
        later = datetime(2024, 1, 15, 15, 0, 0)
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_attempt(Campaign(10, 5, "attachment_url", "Hello"), 1, later)
        registry.mark_attempt(Campaign(10, 5, "attachment_url", "Hello"), 2, T)
        assert registry.get_last_start_date(Campaign(10, 5, "attachment_url", "Hello")) == later

    def test_mark_sent_also_records_last_start_date(self, tmp_path):
        """A successful send updates the last start date even without a prior attempt mark."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_sent(Campaign(10, 5, "attachment_url", "Hello"), 1, T)
        assert registry.get_last_start_date(Campaign(10, 5, "attachment_url", "Hello")) == T

    def test_last_start_date_survives_a_new_instance(self, tmp_path):
        """The last start date is persisted to disk and read back as a datetime."""
        path = tmp_path / "send_progress.json"
        JsonSendRegistry(path).mark_attempt(Campaign(10, 5, "attachment_url", "Hello"), 1, T)
        assert JsonSendRegistry(path).get_last_start_date(Campaign(10, 5, "attachment_url", "Hello")) == T

    def test_record_from_previous_version_is_still_readable(self, tmp_path):
        """A record written before scheduling was tracked loads without last date or attempts."""
        path = tmp_path / "send_progress.json"
        registry = JsonSendRegistry(path)
        registry.mark_sent(Campaign(10, 5, "attachment_url", "Hello"), 1, T)
        data = json.loads(path.read_text(encoding="utf-8"))
        for record in data.values():
            record.pop("last_start_date")
            record.pop("uncertain_attempts")
        path.write_text(json.dumps(data), encoding="utf-8")
        assert registry.get_sent_contact_ids(Campaign(10, 5, "attachment_url", "Hello")) == {1}
        assert registry.get_last_start_date(Campaign(10, 5, "attachment_url", "Hello")) is None
        assert registry.get_uncertain_attempts(Campaign(10, 5, "attachment_url", "Hello")) == {}

    def test_record_keyed_by_a_previous_version_is_found(self, tmp_path):
        """A record stored under the key format of earlier versions is found for the same campaign."""
        path = tmp_path / "send_progress.json"
        key = hashlib.sha1("10|5|attachment_url|Hello".encode("utf-8")).hexdigest()
        path.write_text(json.dumps({key: {"sent_contact_ids": [7]}}), encoding="utf-8")
        assert JsonSendRegistry(path).get_sent_contact_ids(Campaign(10, 5, "attachment_url", "Hello")) == {7}


class TestJsonSendRegistryUncertainAttempts:
    """Tests for tracking send attempts whose outcome is unknown.

    Every attempt is recorded before calling the API and resolved once the
    answer is known. Attempts left unresolved (application closed abruptly,
    or no answer from the API) may have been scheduled, so the user must be
    told about them to check for duplicates.
    """

    LATER = datetime(2024, 1, 15, 15, 0, 0)

    def test_no_uncertain_attempts_when_campaign_has_no_record(self, tmp_path):
        """A campaign without records reports no uncertain attempts."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        assert registry.get_uncertain_attempts(Campaign(10, 5, "attachment_url", "Hello")) == {}

    def test_unresolved_attempt_is_reported_as_uncertain(self, tmp_path):
        """An attempt not yet resolved is reported with its contact and slot."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_attempt(Campaign(10, 5, "attachment_url", "Hello"), 42, T)
        assert registry.get_uncertain_attempts(Campaign(10, 5, "attachment_url", "Hello")) == {42: [T]}

    def test_mark_sent_resolves_the_matching_attempt(self, tmp_path):
        """A successful send removes the attempt made for that same slot."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_attempt(Campaign(10, 5, "attachment_url", "Hello"), 42, T)
        registry.mark_sent(Campaign(10, 5, "attachment_url", "Hello"), 42, T)
        assert registry.get_uncertain_attempts(Campaign(10, 5, "attachment_url", "Hello")) == {}

    def test_mark_sent_keeps_earlier_uncertain_attempts_of_the_contact(self, tmp_path):
        """A retry that succeeds leaves the earlier unresolved attempt reported as a possible duplicate."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_attempt(Campaign(10, 5, "attachment_url", "Hello"), 42, T)
        registry.mark_attempt(Campaign(10, 5, "attachment_url", "Hello"), 42, self.LATER)
        registry.mark_sent(Campaign(10, 5, "attachment_url", "Hello"), 42, self.LATER)
        assert registry.get_uncertain_attempts(Campaign(10, 5, "attachment_url", "Hello")) == {42: [T]}

    def test_discard_attempt_resolves_it_without_marking_sent(self, tmp_path):
        """Discarding an attempt removes it and does not count the contact as sent."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_attempt(Campaign(10, 5, "attachment_url", "Hello"), 42, T)
        registry.discard_attempt(Campaign(10, 5, "attachment_url", "Hello"), 42, T)
        assert registry.get_uncertain_attempts(Campaign(10, 5, "attachment_url", "Hello")) == {}
        assert registry.get_sent_contact_ids(Campaign(10, 5, "attachment_url", "Hello")) == set()

    def test_discard_attempt_keeps_last_start_date(self, tmp_path):
        """A discarded attempt still counts for the last start date, keeping later runs safely after it."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_attempt(Campaign(10, 5, "attachment_url", "Hello"), 42, T)
        registry.discard_attempt(Campaign(10, 5, "attachment_url", "Hello"), 42, T)
        assert registry.get_last_start_date(Campaign(10, 5, "attachment_url", "Hello")) == T

    def test_discard_unknown_attempt_does_not_raise(self, tmp_path):
        """Discarding an attempt that was never recorded is a harmless no-op."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.discard_attempt(Campaign(10, 5, "attachment_url", "Hello"), 42, T)  # must not raise

    def test_uncertain_attempts_survive_a_new_instance(self, tmp_path):
        """Unresolved attempts are persisted so they can be reported after an abrupt close."""
        path = tmp_path / "send_progress.json"
        JsonSendRegistry(path).mark_attempt(Campaign(10, 5, "attachment_url", "Hello"), 42, T)
        assert JsonSendRegistry(path).get_uncertain_attempts(Campaign(10, 5, "attachment_url", "Hello")) == {42: [T]}

    def test_clear_removes_uncertain_attempts_and_last_start_date(self, tmp_path):
        """clear() forgets attempts and the last start date along with sent contacts."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_attempt(Campaign(10, 5, "attachment_url", "Hello"), 42, T)
        registry.clear(Campaign(10, 5, "attachment_url", "Hello"))
        assert registry.get_uncertain_attempts(Campaign(10, 5, "attachment_url", "Hello")) == {}
        assert registry.get_last_start_date(Campaign(10, 5, "attachment_url", "Hello")) is None
