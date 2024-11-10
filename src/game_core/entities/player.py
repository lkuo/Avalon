from dataclasses import dataclass

from game_core.constants.role import Role


@dataclass
class Player:
    id: str
    name: str
    role: Role
