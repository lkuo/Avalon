from game_core.entities.event import Event
from game_core.event_type import EventType
from game_core.services.game_service import GameService
from game_core.states.state import State, StateName


class EndGameState(State):
    """
    This is the end state
    Transitions from QuestVotingState
    Handles ASSASSINATION_TARGET_SUBMITTED event
    Broadcast assassination started, pending for the assassin to pick a target
    Broadcast the assassin picked target
    If the assassination attempts exhausted, broadcast everyone's role and the game result
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
