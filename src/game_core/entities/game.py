from dataclasses import dataclass
from typing import Optional

from game_core.constants.state_name import StateName


@dataclass
class Game:
    id: str
    state: StateName
    quest_team_size: dict[int, int] | None
    roles: list[str] | None
    known_roles: dict[str, list[str]] | None
    player_ids: Optional[list[str]] | None
    assassination_attempts: Optional[int] | None
    result: Optional[str] | None
