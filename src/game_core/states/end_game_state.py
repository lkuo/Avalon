from typing import Optional

from game_core.constants.action_type import ActionType
from game_core.constants.state_name import StateName
from game_core.entities.action import Action
from game_core.services.game_service import GameService
from game_core.states.state import State


class EndGameState(State):
    """
    Transitions from QuestVotingState.
    Broadcast assassination started, wait until the assassin picks a target.
    Calculate and broadcast the game results.
    """

    def __init__(self, game_service: GameService):
        super().__init__(StateName.EndGame)
        self._game_service = game_service

    def handle(self, action: Action) -> Optional[State]:
        if action.type != ActionType.SubmitAssassinationTarget:
            raise ValueError(
                f"EndGameState expects only SubmitAssassinationTarget, got {action.type.value}"
            )
        self._game_service.handle_submit_assassination_target(action)

        if self._game_service.get_assassination_attempts(action.game_id) == 0:
            self._game_service.handle_game_ended(action.game_id)
            return None

        return None if self._game_service.is_game_finished(action.game_id) else self

    def on_enter(self, game_id: str) -> None:
        if self._game_service.get_assassination_attempts(game_id) == 0:
            self._game_service.handle_game_ended(game_id)
            return

        self._game_service.on_enter_end_game_state(game_id)
