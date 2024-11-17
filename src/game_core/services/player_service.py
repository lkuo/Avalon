import random
import uuid
from collections import defaultdict

from game_core.constants.role import Role
from game_core.entities.event import Event
from game_core.entities.game import GameConfig
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

    def assign_roles(self, game_id: str, roles: dict[str, list[str]]) -> list[Player]:
        roles = {Role(k): [Role(v) for v in vals] for k, vals in roles.items()}
        roles[Role.Villager] = []

        players = self._repository.get_players(game_id)
        random.shuffle(players)
        role_keys = list(roles.keys())
        for i in range(len(players)):
            player = players[i]
            player.role = role_keys[i] if i < len(role_keys) else Role.Villager

        role_player_ids = defaultdict(list)
        for player in players:
            role_player_ids[player.role].append(player.id)

        for player in players:
            for known_role in roles[player.role]:
                player.known_player_ids.extend(role_player_ids[known_role])

        return self._repository.put_players(game_id, players)

    def get_players(self, game_id) -> list[Player]:
        return self._repository.get_players(game_id)
