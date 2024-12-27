from game_core.constants.action_type import ActionType
from game_core.constants.state_name import StateName
from game_core.entities.action import Action
from game_core.services.game_service import GameService
from game_core.services.player_service import PlayerService
from game_core.states.state import State


class GameSetupState(State):
    """
    Handles GameStarted event and PlayerJoined event.
    Transitions to TeamSelectionState state when receive GameStartEvent.
    """

    def __init__(
        self,
        game_service: GameService,
        player_service: PlayerService,
    ):
        super().__init__(StateName.GameSetup)
        self._player_service = player_service
        self._game_service = game_service
        self._team_selection_state = None

    def set_states(self, team_selection_state: State) -> None:
        self._team_selection_state = team_selection_state

    def handle(self, action: Action) -> State:
        if action.type not in [ActionType.StartGame, ActionType.JoinGame]:
            raise ValueError(
                f"GameSetupState expects GAME_STARTED or PLAYER_JOINED event, got {action.type.value}"
            )

        if action.type == ActionType.JoinGame:
            self._player_service.handle_join_game(action)
            return self

        self._game_service.handle_start_game(action)

        return self._team_selection_state
