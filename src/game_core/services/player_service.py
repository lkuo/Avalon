import logging
import os
import random
import uuid

from game_core.constants.role import Role
from game_core.entities.game import Game
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

    def save_player(self, player_id: str, name: str) -> Player:
        secret = str(uuid.uuid4())
        return self._repository.put_player(player_id, name, secret)

    def get_player(self, player_id: str) -> Player:
        return self._repository.get_player(player_id)

    def get_players(self, game_id: str) -> list[Player]:
        return self._repository.get_players(game_id)

    def assign_roles(self, players: list[Player], game: Game) -> list[Player]:
        roles = game.roles
        known_roles = game.known_roles
        logger.debug(f"Roles: {roles}, known_roles: {known_roles}, num of players {len(players)}")
        random.shuffle(players)
        for i in range(len(players)):
            player = players[i]
            player.role = Role(roles[i]) if i < len(roles) else Role.Villager

        role_player_id = {player.role.value: player.id for player in players if player.role != Role.Villager}
        logger.debug(f"role_player_ids: {role_player_id}")

        for player in players:
            player.known_player_ids = []
            logger.debug(f"player: {player}")
            for known_role in known_roles[player.role.value]:
                logger.debug(f"known_role: {known_role}")
                if known_role in role_player_id:
                    logger.debug(f"appending {role_player_id[known_role]}")
                    player.known_player_ids.append(role_player_id[known_role])
            logger.debug(f"player: {player}, known_player_ids: {player.known_player_ids}")
            self._repository.update_player(player)
        return players

