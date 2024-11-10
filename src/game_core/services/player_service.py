import uuid

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
        player = self._save_player(event)
        player_joined_event = self._save_player_joined_event(player, event)
        self._comm_service.broadcast(player_joined_event)

    def _save_player(self, event: Event) -> Player:
        payload = getattr(event, 'payload') or {}
        name = payload.get('player_name', '')
        if not name:
            raise ValueError(f"Player name is not found in event payload {payload}")
        game_id = event.game_id
        secret = str(uuid.uuid4())
        return self._repository.put_player(game_id, name, secret)

    def _save_player_joined_event(self, player: Player, event: Event) -> Event:
        game_id = event.game_id
        event_type = event.type.value
        recipients = []
        payload = {
            "player_id": player.id,
            'player_name': player.name,
        }
        timestamp = event.timestamp
        return self._repository.put_event(game_id, event_type, recipients, payload, timestamp)
