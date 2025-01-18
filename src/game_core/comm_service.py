from abc import abstractmethod

from game_core.entities.event import Event


class CommService:

    @abstractmethod
    def broadcast(self, event: Event) -> None:
        pass

    @abstractmethod
    def notify(self, player_id: str, event: Event) -> None:
        pass
