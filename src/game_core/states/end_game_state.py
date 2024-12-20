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
        super().__init__(StateName.EndGame)
        self._game_service = game_service

    # rename this to assassination state and create an endgame state only to announce the game results
    def handle(self, event: Event) -> State:
        if event.type != EventType.AssassinationTargetSubmitted:
            raise ValueError(f"EndGameState expects only ASSASSINATION_TARGET_SUBMITTED, got {event.type.value}")

        assassination_attempts = self._game_service.get_assassination_attempts(event.game_id)
        if assassination_attempts == 0:
            self._game_service.handle_game_ended(event.game_id)
            return self

        self._game_service.handle_assassination_target_submitted(event)

        return None if self._game_service.is_game_finished(event.game_id) else self

    def on_enter(self, game_id: str) -> None:
        assassination_attempts = self._game_service.get_assassination_attempts(game_id)
        if assassination_attempts == 0:
            self._game_service.handle_game_ended(game_id)
            return

        self._game_service.on_enter_end_game_state(game_id)
