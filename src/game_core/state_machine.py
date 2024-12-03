from game_core.entities.event import Event
from game_core.services.comm_service import CommService


class StateMachine:

    def __init__(self, comm_service: CommService, repository):
        self._comm_service = comm_service
        self._repository = repository

    def handle_event(self, event: Event) -> None:
        next_state = self._current_state.handle(event)
        if next_state != self._current_state:
            self._current_state.on_exit()
            next_state.on_enter()
            self._current_state = next_state
