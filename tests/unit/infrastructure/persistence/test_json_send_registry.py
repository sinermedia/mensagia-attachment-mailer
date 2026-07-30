import json
from src.infrastructure.persistence.json_send_registry import JsonSendRegistry


class TestJsonSendRegistry:
    """Tests for the local JSON-backed implementation of the SendRegistry port."""

    def test_returns_empty_set_when_no_file_exists(self, tmp_path):
        """No prior sends are reported when the registry file does not exist yet."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        assert registry.get_sent_contact_ids(10, 5, "attachment_url", "Hello") == set()

    def test_marked_contact_is_returned_by_get_sent_contact_ids(self, tmp_path):
        """A contact ID recorded with mark_sent() is later returned for the same campaign."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_sent(10, 5, "attachment_url", "Hello", 42)
        assert registry.get_sent_contact_ids(10, 5, "attachment_url", "Hello") == {42}

    def test_multiple_contacts_accumulate_in_the_same_campaign(self, tmp_path):
        """Marking several contacts in the same campaign accumulates all their IDs."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_sent(10, 5, "attachment_url", "Hello", 1)
        registry.mark_sent(10, 5, "attachment_url", "Hello", 2)
        registry.mark_sent(10, 5, "attachment_url", "Hello", 3)
        assert registry.get_sent_contact_ids(10, 5, "attachment_url", "Hello") == {1, 2, 3}

    def test_marking_the_same_contact_twice_does_not_duplicate(self, tmp_path):
        """Calling mark_sent() twice for the same contact keeps a single entry."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_sent(10, 5, "attachment_url", "Hello", 1)
        registry.mark_sent(10, 5, "attachment_url", "Hello", 1)
        assert registry.get_sent_contact_ids(10, 5, "attachment_url", "Hello") == {1}

    def test_different_campaigns_are_tracked_independently(self, tmp_path):
        """Sends recorded for one campaign do not leak into a campaign with a different subject."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_sent(10, 5, "attachment_url", "Hello", 1)
        registry.mark_sent(10, 5, "attachment_url", "Goodbye", 2)
        assert registry.get_sent_contact_ids(10, 5, "attachment_url", "Hello") == {1}
        assert registry.get_sent_contact_ids(10, 5, "attachment_url", "Goodbye") == {2}

    def test_clear_removes_the_campaign_record(self, tmp_path):
        """clear() forgets all sent IDs for a campaign so it starts fresh again."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_sent(10, 5, "attachment_url", "Hello", 1)
        registry.clear(10, 5, "attachment_url", "Hello")
        assert registry.get_sent_contact_ids(10, 5, "attachment_url", "Hello") == set()

    def test_clear_on_untracked_campaign_does_not_raise(self, tmp_path):
        """Clearing a campaign that was never recorded is a harmless no-op."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.clear(10, 5, "attachment_url", "Hello")  # must not raise

    def test_clear_does_not_affect_other_campaigns(self, tmp_path):
        """Clearing one campaign leaves other campaigns' records intact."""
        registry = JsonSendRegistry(tmp_path / "send_progress.json")
        registry.mark_sent(10, 5, "attachment_url", "Hello", 1)
        registry.mark_sent(20, 5, "attachment_url", "Hello", 2)
        registry.clear(10, 5, "attachment_url", "Hello")
        assert registry.get_sent_contact_ids(20, 5, "attachment_url", "Hello") == {2}

    def test_mark_sent_persists_to_disk_immediately(self, tmp_path):
        """Each mark_sent() call writes to disk right away, surviving a new instance."""
        path = tmp_path / "send_progress.json"
        JsonSendRegistry(path).mark_sent(10, 5, "attachment_url", "Hello", 1)
        # A second, independent instance reading the same file sees the update
        assert JsonSendRegistry(path).get_sent_contact_ids(10, 5, "attachment_url", "Hello") == {1}

    def test_returns_empty_set_on_corrupt_file(self, tmp_path):
        """A corrupted registry file is treated as empty instead of raising."""
        path = tmp_path / "send_progress.json"
        path.write_text("not valid json", encoding="utf-8")
        registry = JsonSendRegistry(path)
        assert registry.get_sent_contact_ids(10, 5, "attachment_url", "Hello") == set()

    def test_mark_sent_is_silent_on_write_error(self, tmp_path):
        """A write error (e.g. missing parent directory that cannot be created) does not raise."""
        bad_path = tmp_path / "ro" / "nested" / "send_progress.json"
        registry = JsonSendRegistry(bad_path)
        # Simulate an unwritable location by pointing at a path whose parent is a file
        blocker = tmp_path / "ro"
        blocker.write_text("i am a file, not a directory", encoding="utf-8")
        registry.mark_sent(10, 5, "attachment_url", "Hello", 1)  # must not raise

    def test_default_path_used_when_none_given(self, tmp_path, monkeypatch):
        """When no explicit path is given, the module's default path resolver is used."""
        default_file = tmp_path / "send_progress.json"
        monkeypatch.setattr(
            "src.infrastructure.persistence.json_send_registry._default_registry_path",
            lambda: default_file,
        )
        registry = JsonSendRegistry()
        registry.mark_sent(10, 5, "attachment_url", "Hello", 1)
        assert json.loads(default_file.read_text(encoding="utf-8"))
