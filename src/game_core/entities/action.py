from dataclasses import dataclass
from typing import Any

from game_core.constants.action_type import ActionType


@dataclass
class Action:
    id: str
    game_id: str
    player_id: str
    type: ActionType
    payload: dict[str, Any]
