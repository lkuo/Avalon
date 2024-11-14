from abc import ABC
from typing import Any

from game_core.entities.event import Event
from game_core.entities.game import Game
from game_core.entities.player import Player


class Repository(ABC):

    def get_game(self, game_id: str) -> Game:
        ...

    def put_event(self, game_id: str, event_type: str, recipients: list[str], payload: dict[str, Any],
                  timestamp: int) -> Event:
        pass

    def put_player(self, game_id: str, name: str, secret: str) -> Player:
        pass

    def put_players(self, game_id, players: list[Player]) -> list[Player]:
        pass

    def get_players(self, game_id: str) -> list[Player]:
        pass

    def put_events(self, events: list[Event]):
        pass

    def put_game(self, game):
        pass
