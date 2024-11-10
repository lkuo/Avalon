from dataclasses import dataclass


@dataclass
class Game:
    id: str
    status: str
    result: str
