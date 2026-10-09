from dataclasses import dataclass, field


# Basic contact fields Mensagia lets a message use besides the custom ones,
# by the name written between # signs. City and language are left out, as
# the Mensagia portal does not offer them in messages either. No custom
# field can take one of these names, so they never clash
SUBJECT_BASIC_FIELDS = ("email", "name", "number")


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
        number: Phone number of the contact. May be an empty string if the
            contact has none.
    """

    id: int
    name: str
    email: str
    extra_fields: dict = field(default_factory=dict)
    number: str = ""

    def subject_values(self) -> dict[str, str]:
        """Return the values a subject can take from this contact.

        Returns:
            The basic fields of SUBJECT_BASIC_FIELDS and every custom field,
            keyed by the name used in the subject, all written as text so a
            numeric value still fits; an empty value is an empty string.
        """
        values = {"email": self.email, "name": self.name, "number": self.number}
        values.update(self.extra_fields)
        return {name: "" if value is None else str(value) for name, value in values.items()}
