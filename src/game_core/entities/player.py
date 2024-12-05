from dataclasses import dataclass, field
from typing import Optional

from game_core.constants.role import Role


# todo: add game id field
@dataclass
class Player:
    id: str
    game_id: str
    name: str
    secret: str
    role: Optional[Role] = None
    known_player_ids: list[str] = field(default_factory=list)
