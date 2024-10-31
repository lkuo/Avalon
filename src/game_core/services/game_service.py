from game_core.entities.game import Game
from game_core.repositories.game_repository import GameRepository


class GameService:
    def __init__(self, game_repository: GameRepository):
        self._game_repository = game_repository

    def get_game(self, game_id: str) -> Game:
        ...

    def create_game(self, game: Game) -> None:
        ...

    def start_game(self, game: Game) -> None:
        """
        When start a game
        1. Update the game state to "started"
        2. Broadcast the game has started
        3. Notify the player their role and known players
        :param game:
        :return:
        """
        game = self._game_repository.find_game_by_id(game.game_id)
