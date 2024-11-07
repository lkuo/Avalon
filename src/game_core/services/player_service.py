from game_core.services.comm_service import CommService


class PlayerService:
    def __init__(self, comm_service: CommService):
        self._comm_service = comm_service

    def initialize(self, game_id: str) -> None:
        ...

    def handle_player_joined(self, event):
        pass
