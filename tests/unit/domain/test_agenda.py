from src.domain.entities.agenda import Agenda, AgendaPage


class TestAgendaHasContacts:
    """Covers the rule that decides whether an agenda can be targeted for a send."""

    def test_agenda_with_contacts_has_contacts(self):
        """Returns True when the agenda reports at least one contact."""
        assert Agenda(id=1, name="Clients", total_users=3).has_contacts is True

    def test_agenda_without_contacts_has_no_contacts(self):
        """Returns False when the agenda reports zero contacts."""
        assert Agenda(id=1, name="Empty", total_users=0).has_contacts is False

    def test_agenda_defaults_to_no_contacts(self):
        """Returns False when the API omitted the contact count."""
        assert Agenda(id=1, name="Unknown").has_contacts is False


class TestAgendaPage:
    """Covers the page of search results returned by the agenda repository."""

    def test_reports_whether_more_results_exist(self):
        """Reports that more results exist when the total exceeds the page size."""
        page = AgendaPage(agendas=[Agenda(id=1, name="A")], total=42)
        assert page.has_more is True

    def test_reports_no_more_results_when_page_is_complete(self):
        """Reports no further results when the page already holds every match."""
        page = AgendaPage(agendas=[Agenda(id=1, name="A")], total=1)
        assert page.has_more is False

    def test_empty_page_reports_no_more_results(self):
        """Reports no further results when the search matched nothing."""
        assert AgendaPage(agendas=[], total=0).has_more is False
