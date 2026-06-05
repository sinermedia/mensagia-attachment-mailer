from dataclasses import dataclass


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
