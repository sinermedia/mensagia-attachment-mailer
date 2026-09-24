from dataclasses import dataclass, field


@dataclass
class Agenda:
    """Represents a contact group (agenda) in the Mensagia system.

    An agenda is a named list of contacts that can be targeted for a bulk
    send campaign. The total_users count is informational and comes from
    the API response; it is not enforced or computed locally.

    Attributes:
        id: Unique numeric identifier of the agenda in the Mensagia system.
        name: Human-readable name of the agenda as shown in the Mensagia UI.
        total_users: Number of contacts currently in this agenda. Provided
            by the API for display purposes. Defaults to 0 when not returned.
    """

    id: int
    name: str
    total_users: int = 0

    @property
    def has_contacts(self) -> bool:
        """Report whether this agenda holds at least one contact.

        Used by the user interfaces to keep empty agendas visible but
        unselectable, since choosing one leads to a campaign with no
        recipients. Note that a True result does not guarantee that any of
        those contacts is eligible for a send: they may lack an email
        address or the selected extra field.

        Returns:
            True if the API reported one or more contacts in this agenda.
        """
        return self.total_users > 0


@dataclass
class AgendaPage:
    """A single page of agenda search results.

    Carries both the agendas of the requested page and the total number of
    matches reported by the API, so the user interfaces can show how many
    results were left out without ever loading them into memory.

    Attributes:
        agendas: The Agenda objects contained in this page.
        total: Total number of agendas matching the search across all pages.
    """

    agendas: list[Agenda] = field(default_factory=list)
    total: int = 0

    @property
    def has_more(self) -> bool:
        """Report whether matches exist beyond the ones in this page.

        Returns:
            True if the API reported more matches than this page contains.
        """
        return self.total > len(self.agendas)
