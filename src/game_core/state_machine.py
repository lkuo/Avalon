from game_core.entities.event import Event
from game_core.services.game_service import GameService
from game_core.states.state import State


class StateMachine:

    def __init__(self, game_id: str, game_service: GameService):
        game = game_service.get_game(game_id)
        state_by_name = self._build_states()
        self._state = state_by_name.get(game.state)

    def handle_event(self, event: Event) -> None:
        ...

    def _build_states(self) -> dict[str: State]:
        return {}
