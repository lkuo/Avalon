from dataclasses import dataclass


@dataclass
class Game:
    game_id: str
    sk_id: str
    status: str
    result: str
