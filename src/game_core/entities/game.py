from dataclasses import dataclass
from typing import Optional

from game_core.constants.game_status import GameStatus
from game_core.constants.state_name import StateName


@dataclass
class GameConfig:
    quest_team_size: dict[int, int]
    roles: list[str]
    known_roles: dict[str, list[str]]
    assassination_attempts: int


@dataclass
class Game:
    id: str
    status: GameStatus
    state: StateName
    config: Optional[GameConfig]
    player_ids: Optional[list[str]]
    assassination_attempts: Optional[int]
    result: Optional[str]
