from dataclasses import dataclass


@dataclass
class EmailAddress:
    """Represents a verified sender email address registered in Mensagia.

    Only addresses that have been verified in the Mensagia account can be
    used as the 'from' address when sending emails. This entity carries
    the identity information needed to present the option to the user.

    Attributes:
        id: Unique numeric identifier of the sender address in Mensagia.
        email: The actual email address string (e.g. 'noreply@example.com').
        name: Optional display name associated with the sender address
            (e.g. 'My Company'). Defaults to an empty string.
    """

    id: int
    email: str
    name: str = ""
