from dataclasses import dataclass
from typing import Any

from game_core.constants.event_type import EventType


@dataclass
class Event:
    id: str
    game_id: str
    type: EventType
    recipients: list[str]  # empty list indicates a public event visible to everyone
    payload: dict[str, Any]
    timestamp: str
