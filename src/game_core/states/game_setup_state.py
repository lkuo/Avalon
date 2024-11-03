from game_core.entities.event import Event
from game_core.event_type import EventType
from game_core.services.player_service import PlayerService
from game_core.states.state import State, StateName


class GameSetupState(State):
    """
    Handles GameStartEvent. Transitions to TeamLeaderAssignment state upon receiving GameStartEvent.
    On exit initialize players.
    """

    def __init__(self, leader_assignment_state: State, player_service: PlayerService):
        super().__init__(StateName.GAME_SETUP)
        self._player_service = player_service
        self._leader_assignment_state = leader_assignment_state

    def handle(self, event: Event) -> State:
        if event.type != EventType.GAME_STARTED:
            raise ValueError(f"GameSetupState expects only GAME_START_EVENT, got {event.type.value}")

        # TODO: rename the `initialize` method
        self._player_service.initialize(event.game_id)

        return self._leader_assignment_state
