from dataclasses import dataclass
from datetime import datetime
from typing import Any

from game_core.constants.event_type import EventType


@dataclass
class Event:
    id: str
    type: EventType
    recipient: list[str]
    payload: dict[str, Any]
    timestamp: int = datetime.now()
