from dataclasses import dataclass


@dataclass
class GameConfig:
    mission_number_size: dict[int, int]
    max_round: int
    roles: dict[str, list[str]]
    assassination_attempt: int


@dataclass
class Game:
    id: str
    status: str
    result: str
    config: GameConfig
