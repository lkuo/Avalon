from pydantic import BaseModel

from game_core.constants.action_type import ActionType
from game_core.constants.role import Role
from game_core.constants.state_name import StateName
from game_core.entities.action import Action
from game_core.services.event_service import EventService
from game_core.services.game_service import GameService
from game_core.services.player_service import PlayerService
from game_core.services.state_service import StateService
from game_core.states.state import State


class EndGameState(State):
    """
    Transitions from QuestVotingState.
    Broadcast assassination started, wait until the assassin picks a target.
    Calculate and broadcast the game results.
    """

    def __init__(self, state_service: StateService, game_service: GameService, player_service: PlayerService,
                 event_service: EventService):
        super().__init__(StateName.EndGame)
        self._game_service = game_service
        self._state_service = state_service
        self._player_service = player_service
        self._event_service = event_service

    def handle(self, action: Action) -> None:
        if action.type != ActionType.SubmitAssassinationTarget:
            raise ValueError(f"EndGameState expects only SubmitAssassinationTarget, got {action.type.value}")
        SubmitAssassinationTargetPayload(**action.payload)
        target = self._player_service.get_player(action.payload["target_id"])
        game = self._game_service.get_game(action.game_id)
        game.assassination_attempts -= 1
        is_successful = target.role == Role.Merlin
        self._event_service.create_assassination_event(
            action.game_id, target.id, is_successful
        )
        if is_successful:
            return self._state_service.end_game(action.game_id, "Evil")
        if game.assassination_attempts == 0:
            return self._state_service.end_game(action.game_id, "Good")
        self._state_service.start_assassination(action.game_id)


class SubmitAssassinationTargetPayload(BaseModel):
    target_id: str
