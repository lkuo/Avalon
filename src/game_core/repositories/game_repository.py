from game_core.entities.game import Game


class GameRepository:
    def __init__(self, table):
        self._table = table

    def find_game_by_id(self, game_id: str) -> Game:
        ...
