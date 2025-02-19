import logging

from pydantic import BaseModel, Field

from game_core.constants.config import DEFAULT_TEAM_SIZE_ROLES, KNOWN_ROLES, DEFAULT_QUEST_TEAM_SIZE, \
    DEFAULT_ASSASSINATION_ATTEMPTS
from game_core.constants.game_status import GameStatus
from game_core.constants.role import Role
from game_core.entities.action import Action
from game_core.entities.game import Game, GameConfig
from game_core.entities.player import Player
from game_core.repository import Repository
from game_core.services.event_service import EventService
from game_core.services.player_service import PlayerService

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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

    def handle_start_game(self, action: Action) -> None:
        game_id = action.game_id
        game = self.get_game(game_id)
        if game.status != GameStatus.NotStarted:
            raise ValueError(
                f"Game {game_id} is not in NotStarted state, got {game.status}"
            )

        StartGamePayload(**action.payload)
        num_players = len(action.payload["player_ids"])
        if num_players not in DEFAULT_TEAM_SIZE_ROLES:
            raise ValueError(f"Only support number of players from 5 to 10, got {num_players}")
        roles = action.payload.get("roles") or DEFAULT_TEAM_SIZE_ROLES[num_players]
        known_roles = action.payload.get("known_roles") or KNOWN_ROLES
        players = self._player_service.assign_roles(game_id, roles, known_roles)
        player_ids = action.payload["player_ids"]
        given_player_ids = set([f"{game_id}_player_{player_id}" for player_id in player_ids])
        actual_player_ids = set([player.id for player in players])
        if given_player_ids != actual_player_ids:
            raise ValueError(
                f"player_ids in GameStarted event payload does not match DB, got {given_player_ids}, actual {actual_player_ids}"
            )
        game.status = GameStatus.InProgress
        game.player_ids = player_ids
        game_config = GameConfig(
            quest_team_size=DEFAULT_QUEST_TEAM_SIZE[num_players],
            roles=roles,
            known_roles=known_roles,
            assassination_attempts=action.payload.get("assassination_attempts", DEFAULT_ASSASSINATION_ATTEMPTS[num_players])
        )
        game.config = game_config
        self._repository.update_game(game)
        self._event_service.create_game_started_events(game_id, players)

    def get_game(self, game_id: str) -> Game:
        game = self._repository.get_game(game_id)
        if not game:
            raise ValueError(f"Game {game_id} not found")

        return game

    def get_assassination_attempts(self, game_id: str) -> int:
        game = self.get_game(game_id)
        game_config = game.config
        if not game_config:
            raise ValueError(f"Game {game_id} config not found")
        return (
            game.assassination_attempts
            if game.assassination_attempts is not None
            else game_config.assassination_attempts
        )

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
            self.handle_game_ended(action.game_id)

    def handle_game_ended(self, game_id: str) -> None:
        game = self._repository.get_game(game_id)
        game.status = GameStatus.Finished
        self._repository.update_game(game)
        players = self._player_service.get_players(game_id)
        player_roles = {player.id: player.role.value for player in players}
        self._event_service.create_game_ended_event(game_id, player_roles)

    def is_game_finished(self, game_id: str) -> bool:
        game = self.get_game(game_id)
        return game.status == GameStatus.Finished


class StartGamePayload(BaseModel):
    player_ids: list[str]
    assassination_attempts: int | None = Field(default=None)
    roles: list[str] | None = Field(default=None)
    known_roles: dict[str, list[str]] | None = Field(default=None)


class SubmitAssassinationTargetPayload(BaseModel):
    target_id: str
