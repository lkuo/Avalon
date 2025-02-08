import logging
import os
import random
import uuid
from collections import defaultdict

from pydantic import BaseModel

from game_core.constants.role import Role
from game_core.entities.action import Action
from game_core.entities.player import Player
from game_core.repository import Repository
from game_core.services.event_service import EventService

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


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
        player_id = action.player_id
        game_id = action.game_id
        secret = str(uuid.uuid4())
        return self._repository.put_player(player_id, game_id, payload.name, secret)

    def assign_roles(self, game_id: str, roles: list[str], known_roles: dict[str, list[str]]) -> list[Player]:
        players = self._repository.get_players(game_id)
        logger.debug(f"Num of players {len(players)} with roles: {roles}")
        random.shuffle(players)
        for i in range(len(players)):
            player = players[i]
            player.role = Role(roles[i]) if i < len(roles) else Role.Villager

        role_player_ids = defaultdict(list)
        for player in players:
            role_player_ids[player.role.value].append(player.id)

        logger.debug(f"role_player_ids: {role_player_ids}")

        for player in players:
            for known_role in known_roles[player.role.value]:
                player.known_player_ids.extend(role_player_ids[known_role])
            logger.debug(f"player: {player}, known_player_ids: {player.known_player_ids}")
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
