import logging
import os

from pydantic import BaseModel, Field

from game_core.constants.action_type import ActionType
from game_core.constants.state_name import StateName
from game_core.entities.action import Action
from game_core.services.event_service import EventService
from game_core.services.game_service import GameService
from game_core.services.player_service import PlayerService
from game_core.services.state_service import StateService
from game_core.states.state import State, InvalidActionTypeException, InvalidInputException

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


class GameSetupState(State):
    """
    Handles GameStarted event and PlayerJoined event.
    Transitions to TeamSelectionState state when receive GameStartEvent.
    """

    def __init__(
            self,
            state_service: StateService,
            game_service: GameService,
            player_service: PlayerService,
            event_service: EventService,
    ):
        super().__init__(StateName.GameSetup)
        self._state_service = state_service
        self._game_service = game_service
        self._player_service = player_service
        self._event_service = event_service

    def handle(self, action: Action) -> None:
        if action.type == ActionType.JoinGame:
            payload = JoinGamePayload(**action.payload)
            self._player_service.save_player(action.player_id, payload.player_name)
            self._event_service.create_player_joined_event(action.player_id, action.game_id, payload.player_name)
        elif action.type == ActionType.StartGame:
            game_id = action.game_id
            payload = StartGamePayload(**action.payload)
            players = self._player_service.get_players(game_id)

            if (found := set([player.id for player in players])) != (given := set(payload.player_ids)):
                raise InvalidInputException(f"Player ids do not match, found: {found}, given: {given}")

            game = self._game_service.init_game(game_id, payload.player_ids, payload.assassination_attempts)
            players = self._player_service.assign_roles(players, game)
            self._state_service.start_game(game_id, players)
        else:
            raise InvalidActionTypeException([ActionType.JoinGame, ActionType.StartGame], action.type)


class JoinGamePayload(BaseModel):
    name: str


class StartGamePayload(BaseModel):
    player_ids: list[str]
    assassination_attempts: int | None = Field(default=None)
