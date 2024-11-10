from game_core.entities.event import Event
from game_core.constants.event_type import EventType
from game_core.services.game_service import GameService
from game_core.states.state import State
from game_core.constants.state_name import StateName


class EndGameState(State):
    """
    Transitions from QuestVotingState.
    Broadcast assassination started, wait until the assassin picks a target.
    Calculate and broadcast the game results.
    """

    def __init__(self, game_service: GameService):
        super().__init__(StateName.END_GAME)
        self._game_service = game_service

    def handle(self, event: Event) -> State:
        if event.type != EventType.ASSASSINATION_TARGET_SUBMITTED:
            raise ValueError(f"EndGameState expects only ASSASSINATION_TARGET_SUBMITTED, got {event.type.value}")

        self._game_service.handle_assassination_target_submitted(event)

        assassination_attempts = self._game_service.get_assassination_attempts(event.game_id)
        return self if assassination_attempts > 0 else None

    def on_enter(self, game_id: str) -> None:
        assassination_attempts = self._game_service.get_assassination_attempts(game_id)
        if assassination_attempts == 0:
            self.on_exit(game_id)
            return

        self._game_service.on_enter_end_game_state(game_id)

    def on_exit(self, game_id: str) -> None:
        self._game_service.on_exit_end_game_state(game_id)
