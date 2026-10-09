import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field


# A field is whatever sits between two # signs without any space, the
# notation Mensagia uses for custom fields. Requiring no spaces keeps
# ordinary text such as 'Pedido #12 y #34' from being taken as a field
_PLACEHOLDER = re.compile(r"#([^#\s]+)#")

# Line breaks of any kind, with the spaces around them, in a field value
_LINE_BREAK = re.compile(r"\s*[\r\n]+\s*")


class SubjectFieldError(ValueError):
    """Raised when the fields of a subject cannot be matched with the available names.

    Attributes:
        unknown: Fields of the subject, as written, that match no name.
        ambiguous: Fields of the subject, as written, that match more than
            one name, each with the names it matches.
    """

    def __init__(self, unknown: list[str], ambiguous: dict[str, list[str]]):
        """Initialise the error with every problem found in the subject.

        Args:
            unknown: Fields that match no name.
            ambiguous: Fields that match more than one name, with those names.
        """
        super().__init__(f"unknown={unknown} ambiguous={ambiguous}")
        self.unknown = unknown
        self.ambiguous = ambiguous


def _normalize(name: str) -> str:
    """Return the form in which a field and a name are compared.

    The match ignores case and takes a space in a column or field name as
    an underscore, since a field written in the subject cannot hold spaces.

    Args:
        name: Field written in the subject, or field or column name.

    Returns:
        The name lowercased, with its spaces as underscores.
    """
    return name.strip().lower().replace(" ", "_")


def subject_placeholders(subject: str) -> list[str]:
    """List the fields written in a subject.

    Args:
        subject: Subject as written by the user.

    Returns:
        The names written between # signs, in order of appearance and
        without repetitions.
    """
    return list(dict.fromkeys(_PLACEHOLDER.findall(subject)))


def subject_placeholder(name: str) -> str | None:
    """Write a field or column name the way it is used in a subject.

    Args:
        name: Name of the custom field or column.

    Returns:
        The name between # signs with its spaces as underscores, such as
        '#num_factura#' for 'num factura', or None when the name cannot be
        written as a field (empty, or holding a # or another blank).
    """
    written = name.strip().replace(" ", "_")
    if not written or "#" in written or re.search(r"\s", written):
        return None
    return f"#{written}#"


def clean_field_value(value: str) -> str:
    """Prepare a field value to be put into a subject.

    A subject is a single line, so line breaks become spaces, and the
    spaces at both ends, which nobody sees in a cell, are removed.

    Args:
        value: Value of the field or cell, as text.

    Returns:
        The value on one line, stripped.
    """
    return _LINE_BREAK.sub(" ", value).strip()


@dataclass(frozen=True)
class SubjectTemplate:
    """A subject that may take part of its text from each recipient's data.

    Built with bind(), which checks that every field of the subject matches
    one available field or column name. The text as written is what
    identifies the campaign; render() builds the final subject of each
    recipient.

    Attributes:
        text: Subject as written by the user.
        fields: Field written in the subject mapped to the field or column
            name it matches.
    """

    text: str
    fields: dict[str, str] = field(default_factory=dict)

    @classmethod
    def bind(cls, text: str, names: Iterable[str]) -> "SubjectTemplate":
        """Match the fields of a subject with the available names.

        Args:
            text: Subject as written by the user.
            names: Custom field names of the account, or column names of the file.

        Returns:
            The template, ready to render each recipient's subject.

        Raises:
            SubjectFieldError: When a field matches no name, or more than one.
        """
        names = list(names)
        fields, unknown, ambiguous = {}, [], {}
        for placeholder in subject_placeholders(text):
            matches = [name for name in names if _normalize(name) == _normalize(placeholder)]
            if not matches:
                unknown.append(placeholder)
            elif len(matches) > 1:
                ambiguous[placeholder] = matches
            else:
                fields[placeholder] = matches[0]

        # Every problem is reported at once, so the subject is fixed in one go
        if unknown or ambiguous:
            raise SubjectFieldError(unknown, ambiguous)
        return cls(text, fields)

    @property
    def has_fields(self) -> bool:
        """Tell whether the subject takes any text from the recipients.

        Returns:
            True when the subject has at least one field.
        """
        return bool(self.fields)

    @property
    def names(self) -> list[str]:
        """List the field or column names the subject needs.

        Returns:
            Each matched name once, in order of first use.
        """
        return list(dict.fromkeys(self.fields.values()))

    def render(self, values: Mapping[str, str]) -> tuple[str | None, str | None]:
        """Build the final subject of one recipient.

        Args:
            values: Text of the recipient's fields, keyed by field or column
                name. A name that is missing counts as empty.

        Returns:
            The subject and None; or None and the name of the first field
            whose value is empty, since Mensagia would leave a gap that
            cannot be undone once sent.
        """
        cleaned = {}
        for name in self.names:
            cleaned[name] = clean_field_value(values.get(name) or "")
            if not cleaned[name]:
                return None, name
        return _PLACEHOLDER.sub(lambda m: cleaned[self.fields[m.group(1)]], self.text), None
