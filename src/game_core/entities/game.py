from dataclasses import dataclass
from typing import Optional


@dataclass
class GameConfig:
    quest_team_size: dict[int, int]
    max_round: int
    roles: dict[str, list[str]]
    assassination_attempts: int


@dataclass
class Game:
    id: str
    status: str
    state: str
    config: GameConfig
    player_ids: Optional[list[str]]
    assassination_attempts: Optional[int]
    result: Optional[str]
