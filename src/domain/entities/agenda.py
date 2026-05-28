from dataclasses import dataclass


@dataclass
class Agenda:
    id: int
    name: str
    total_users: int = 0
