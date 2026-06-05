from dataclasses import dataclass


@dataclass
class EmailTemplate:
    """Represents an email template stored in the Mensagia platform.

    Templates define the HTML layout and content of outgoing emails.
    They are created and managed through the Mensagia web interface and
    referenced by ID when scheduling a send.

    Attributes:
        id: Unique numeric identifier of the template in the Mensagia system.
        name: Human-readable name of the template as shown in the Mensagia UI.
    """

    id: int
    name: str
