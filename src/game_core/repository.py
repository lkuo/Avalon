from abc import ABC

from game_core.entities.event import Event
from game_core.entities.game import Game
from game_core.entities.player import Player


class Repository(ABC):

    def get_game(self, game_id: str) -> Game:
        ...

    def put_event(self, event: Event) -> None:
        pass

    def put_player(self, player: Player):
        pass
