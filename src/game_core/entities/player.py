from dataclasses import dataclass
from typing import Optional

from game_core.constants.role import Role


@dataclass
class Player:
    id: str
    name: str
    secret: str
    role: Optional[Role] = None
    known_players: list[str] = None
