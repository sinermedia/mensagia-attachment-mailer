from dataclasses import dataclass


@dataclass
class ExtraField:
    """Represents a custom extra field defined at the Mensagia account level.

    Extra fields extend contacts with arbitrary per-contact data. In this
    application the relevant extra field holds the URL (or filename) of the
    personalised attachment that will be sent to each contact.

    Attributes:
        id: Unique numeric identifier of the extra field in the Mensagia system.
        name: Internal name of the field as stored in Mensagia. This name is
            used as the dictionary key when accessing a contact's extra_fields.
    """

    id: int
    name: str
