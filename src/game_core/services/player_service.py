import random
import uuid
from collections import defaultdict

from pydantic import BaseModel

from game_core.constants.role import Role
from game_core.entities.action import Action
from game_core.entities.player import Player
from game_core.repository import Repository
from game_core.services.event_service import EventService


class PlayerService:
    def __init__(
        self,
        event_service: EventService,
        repository: Repository,
    ):
        self._event_service = event_service
        self._repository = repository

    def handle_join_game(self, action: Action) -> None:
        """
        Persist the player, and create a PlayerJoined event then broadcast the event
        :param action: PlayerJoined event
        :return:
        """
        player = self._save_player(action)
        self._event_service.create_player_joined_event(
            player.id, action.game_id, player.name
        )

    def _save_player(self, action: Action) -> Player:
        payload = JoinGamePayload(**action.payload)
        game_id = action.game_id
        secret = str(uuid.uuid4())
        return self._repository.put_player(game_id, payload.name, secret)

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
            self._repository.update_player(player)
        return players

    def get_player(self, player_id: str) -> Player:
        player = self._repository.get_player(player_id)
        if not player:
            raise ValueError(f"Player {player_id} not found")
        return player

    def get_players(self, game_id: str) -> list[Player]:
        return self._repository.get_players(game_id)


class JoinGamePayload(BaseModel):
    name: str
