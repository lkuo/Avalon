from game_core.entities.event import Event
from game_core.entities.player import Player
from game_core.repository import Repository
from game_core.services.comm_service import CommService


class PlayerService:
    def __init__(self, comm_service: CommService, repository: Repository):
        self._comm_service = comm_service
        self._repository = repository

    def handle_player_joined(self, event: Event):
        """
        Persist the player, and create a PlayerJoined event then broadcast the event
        :param event: PlayerJoined event
        :return:
        """
        self._validate_player_joined_event(event)

        player = self._build_player(event)
        self._repository.put_player(player)

        player_joined_event = self._build_player_joined_event(player)
        self._repository.put_event(player_joined_event)
        self._comm_service.broadcast_event(player_joined_event)

    def _validate_player_joined_event(self, event: Event):
        """
        The payload of the event must contain:

        :param event:
        :return:
        """
        pass

    def _build_player(self, event) -> Player:
        pass

    def _build_player_joined_event(self, player) -> Event:
        pass
