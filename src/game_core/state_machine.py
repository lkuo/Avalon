from game_core.entities.event import Event
from game_core.services.comm_service import CommService


class StateMachine:

    def __init__(self, comm_service: CommService, repository):
        self._comm_service = comm_service
        self._repository = repository
        self._current_state = None

    def handle_event(self, event: Event) -> None:
        next_state = self._current_state.handle(event)
        if next_state != self._current_state:
            self._current_state.on_exit()
            fast_forward_state = next_state.on_enter()
            self._current_state = fast_forward_state or next_state
