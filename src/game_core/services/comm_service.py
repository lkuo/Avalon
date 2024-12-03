from typing import Optional

from game_core.entities.event import Event


class CommService:

    def broadcast(self, event: Event, player_ids: Optional[list[str]] = None) -> None:
        pass

    def notify(self, player_id: str, event: Event) -> None:
        pass
