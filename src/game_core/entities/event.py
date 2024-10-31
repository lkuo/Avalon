from dataclasses import dataclass
from typing import Any

from game_core.event_type import EventType


@dataclass
class Event:
    game_id: str
    sk_id: str
    type: EventType
    recipient: list[str]
    payload: dict[str, Any]
