from pydantic import BaseModel

from game_core.constants.game_status import GameStatus
from game_core.constants.role import Role
from game_core.entities.action import Action
from game_core.entities.game import Game
from game_core.entities.player import Player
from game_core.repository import Repository
from game_core.services.event_service import EventService
from game_core.services.player_service import PlayerService


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
        game = self._get_game(game_id)
        if game.status != GameStatus.NotStarted:
            raise ValueError(
                f"Game {game_id} is not in NotStarted state, got {game.status}"
            )
        players = self._player_service.assign_roles(game_id, game.config.roles)
        StartGamePayload(**action.payload)
        player_ids = action.payload["player_ids"]
        given_player_ids = set(player_ids)
        actual_player_ids = set([player.id for player in players])
        if given_player_ids != actual_player_ids:
            raise ValueError(
                f"player_ids in GameStarted event payload does not match DB, got {given_player_ids}"
            )
        game.status = GameStatus.InProgress
        self._repository.put_game(game)
        self._event_service.create_game_started_events(game_id, players)

    def _get_game(self, game_id: str) -> Game:
        game = self._repository.get_game(game_id)
        if not game:
            raise ValueError(f"Game {game_id} not found")

        return game

    def get_assassination_attempts(self, game_id: str) -> int:
        game = self._get_game(game_id)
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
        game = self._get_game(action.game_id)
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
        game = self._get_game(game_id)
        return game.status == GameStatus.Finished


class StartGamePayload(BaseModel):
    player_ids: list[str]


class SubmitAssassinationTargetPayload(BaseModel):
    target_id: str
