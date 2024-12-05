from game_core.entities.event import Event
from game_core.constants.event_type import EventType
from game_core.services.game_service import GameService
from game_core.services.player_service import PlayerService
from game_core.states.state import State
from game_core.constants.state_name import StateName


class GameSetupState(State):
    """
    Handles GameStarted event and PlayerJoined event.
    Transitions to TeamSelectionState state when receive GameStartEvent.
    """

    def __init__(self, team_selection_state: State, game_service: GameService, player_service: PlayerService):
        super().__init__(StateName.GAME_SETUP)
        self._player_service = player_service
        self._game_service = game_service
        self._team_selection_state = team_selection_state

    def handle(self, event: Event) -> State:
        if event.type not in [EventType.GameStarted, EventType.PlayerJoined]:
            raise ValueError(f"GameSetupState expects GAME_STARTED or PLAYER_JOINED event, got {event.type.value}")

        if event.type == EventType.PlayerJoined:
            self._player_service.handle_player_joined(event)
            return self

        self._game_service.handle_game_started(event)

        return self._team_selection_state
