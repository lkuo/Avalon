from game_core.entities.event import Event
from game_core.services.comm_service import CommService


class StateMachine:

    def __init__(self, comm_service: CommService, repository):
        self._comm_service = comm_service
        self._repository = repository

    def handle_event(self, event: Event) -> None:
        ...
