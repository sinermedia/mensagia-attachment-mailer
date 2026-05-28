from dataclasses import dataclass, field


@dataclass
class Contact:
    id: int
    name: str
    email: str
    extra_fields: dict = field(default_factory=dict)
