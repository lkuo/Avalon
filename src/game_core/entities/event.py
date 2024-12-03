from dataclasses import dataclass
from datetime import datetime
from typing import Any

from game_core.constants.event_type import EventType

# todo: add id, remove timestamp default value
@dataclass
class Event:
    game_id: str
    type: EventType
    recipients: list[str]  # empty list indicates a public event visible to everyone
    payload: dict[str, Any]
    timestamp: int = int(datetime.now().timestamp())
