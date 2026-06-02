from dataclasses import dataclass, field


@dataclass
class Contact:
    """Represents a contact in the Mensagia system.

    A contact is a person who belongs to one or more agenda groups and can
    receive emails. Each contact may have custom extra fields that store
    per-contact data such as personalised attachment URLs.

    Attributes:
        id: Unique numeric identifier assigned by the Mensagia API.
        name: Display name of the contact.
        email: Primary email address of the contact. May be an empty string
            if the contact has no email registered.
        extra_fields: Dictionary of custom field values keyed by field name.
            These fields are defined at the account level and hold
            per-contact data (e.g. attachment URLs, personalised codes).
    """

    id: int
    name: str
    email: str
    extra_fields: dict = field(default_factory=dict)
