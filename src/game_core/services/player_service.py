class PlayerService:
    def __init__(self, comm_service: CommService):
        self._comm_service = comm_service

    def initialize(self, game_id: str) -> None:
        ...
