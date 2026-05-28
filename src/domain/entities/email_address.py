from dataclasses import dataclass


@dataclass
class EmailAddress:
    id: int
    email: str
    name: str = ""
