from game_core.entities.event import Event
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
        # game = self._game_repository.find_game_by_id(game.game_id)

    def on_exit_end_game_state(self, game_id):
        pass

    def get_assassination_attempts(self, game_id) -> int:
        pass

    def broadcast_assassination_started(self, game_id):
        pass

    def on_enter_end_game_state(self, game_id):
        pass

    def handle_assassination_target_submitted(self, event: Event):
        pass

    def handle_game_started(self, event):
        pass
