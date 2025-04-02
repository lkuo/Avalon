import logging
import os

from pydantic import BaseModel

from game_core.constants.config import DEFAULT_TEAM_SIZE_ROLES, KNOWN_ROLES, DEFAULT_ASSASSINATION_ATTEMPTS, \
    DEFAULT_QUEST_TEAM_SIZE
from game_core.constants.game_status import GameStatus
from game_core.constants.role import Role
from game_core.constants.state_name import StateName
from game_core.entities.action import Action
from game_core.entities.game import Game
from game_core.entities.player import Player
from game_core.repository import Repository
from game_core.services.event_service import EventService
from game_core.services.player_service import PlayerService

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


class GameService:
    def __init__(
            self,
            player_service: PlayerService,
            event_service: EventService,
            repository: Repository,
    ):
        self._player_service = player_service
        self._event_service = event_service
        self._repository = repository

    def get_game(self, game_id: str) -> Game:
        game = self._repository.get_game(game_id)
        if not game:
            raise ValueError(f"Game {game_id} not found")

        return game

    def start_game(self, game_id: str, player_ids: list[str], assassination_attempt: int | None) -> Game:
        num_players = len(player_ids)
        roles = DEFAULT_TEAM_SIZE_ROLES[num_players]
        known_roles = KNOWN_ROLES
        assassination_attempts = DEFAULT_ASSASSINATION_ATTEMPTS[
            num_players] if assassination_attempt is None else assassination_attempt

        game = self.get_game(game_id)
        game.player_ids = [player_id for player_id in player_ids]
        game.roles = roles
        game.known_roles = known_roles
        game.assassination_attempts = assassination_attempts
        game.state = StateName.TeamSelection.value
        game.quest_team_size = DEFAULT_QUEST_TEAM_SIZE[num_players]
        return self.update_game(game)

    def _rotate_leader(self, game_id: str) -> str:
        """
        Rotates the leader to the next player
        :param game_id:
        :return: the next leader id
        """
        game = self._repository.get_game(game_id)
        rounds = self._repository.get_rounds(game_id)
        rounds.sort(key=lambda r: (r.quest_number, r.round_number))
        player_ids = game.player_ids
        leader_id = rounds[-1].leader_id if rounds else player_ids[0]
        idx = player_ids.index(leader_id)
        next_leader_id = player_ids[(idx + 1) % len(player_ids)]
        return next_leader_id

    def update_game(self, game: Game) -> Game:
        return self._repository.update_game(game)

    def get_assassination_attempts(self, game_id: str) -> int:
        game = self.get_game(game_id)
        return game.assassination_attempts

    def on_enter_end_game_state(self, game_id: str) -> None:
        assassin = self._get_assassin(game_id)
        assassination_attempts = self.get_assassination_attempts(game_id)
        self._event_service.create_assassination_started_event(
            game_id, assassination_attempts
        )
        self._event_service.create_assassination_target_requested_event(
            game_id, assassin.id
        )

    def _get_assassin(self, game_id: str) -> Player:
        players = self._player_service.get_players(game_id)
        assassins = [player for player in players if player.role == Role.Assassin]
        if len(assassins) != 1:
            raise ValueError(
                f"Game {game_id} has {len(assassins)} assassins, expected 1"
            )
        assassin = assassins[0]
        return assassin

    def handle_submit_assassination_target(self, action: Action) -> None:
        SubmitAssassinationTargetPayload(**action.payload)
        target = self._player_service.get_player(action.payload["target_id"])
        attempts = self.get_assassination_attempts(action.game_id)
        game = self.get_game(action.game_id)
        game.assassination_attempts = attempts - 1
        self._repository.update_game(game)
        is_successful = target.role == Role.Merlin
        self._event_service.create_assassination_event(
            action.game_id, target.id, is_successful
        )
        if is_successful:
            self.end_game(action.game_id)

    def end_game(self, game_id: str) -> None:
        game = self._repository.get_game(game_id)
        game.status = GameStatus.Finished
        self._repository.update_game(game)
        players = self._player_service.get_players(game_id)
        player_roles = {player.id: player.role.value for player in players}
        self._event_service.create_game_ended_event(game_id, player_roles)

    def is_game_finished(self, game_id: str) -> bool:
        game = self.get_game(game_id)
        return game.status == GameStatus.Finished


class SubmitAssassinationTargetPayload(BaseModel):
    target_id: str
