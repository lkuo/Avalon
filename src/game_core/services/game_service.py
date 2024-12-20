from datetime import datetime
from typing import Any

from game_core.constants.event_type import EventType
from game_core.constants.game_status import GameStatus
from game_core.constants.role import Role
from game_core.entities.event import Event
from game_core.entities.player import Player
from game_core.repository import Repository
from game_core.services.comm_service import CommService
from game_core.services.player_service import PlayerService


class GameService:
    def __init__(self, comm_service: CommService, repository: Repository, player_service: PlayerService):
        self._repository = repository
        self._player_service = player_service
        self._comm_service = comm_service

    # todo: add docstring
    def handle_game_started(self, event: Event) -> None:
        game_id = event.game_id
        game = self._get_game(game_id)
        players = self._player_service.assign_roles(game_id, game.config.roles)
        player_ids = _get_player_ids(players, event.payload)
        player_events = _get_player_event(game_id, players)

        self._repository.put_events(list(player_events.values()))
        for player_id, event in player_events.items():
            self._comm_service.notify(player_id, event)
        game.status = GameStatus.InProgress
        game.player_ids = player_ids
        self._repository.put_game(game)

    def _get_game(self, game_id):
        game = self._repository.get_game(game_id)
        if not game:
            raise ValueError(f"Game {game_id} not found")
        if game.status != GameStatus.NotStarted:
            raise ValueError(f"Game {game_id} is not in NotStarted state, got {game.status}")
        return game

    # todo: add docstring
    def get_assassination_attempts(self, game_id: str) -> int:
        game = self._repository.get_game(game_id)
        if not game:
            raise ValueError(f"Game {game_id} not found")
        game_config = game.config
        if not game_config:
            raise ValueError(f"Game {game_id} config not found")
        return game.assassination_attempts if game.assassination_attempts is not None else game_config.assassination_attempts

    # todo: add docstring
    def on_enter_end_game_state(self, game_id: str) -> None:
        self._handle_assassination_started(game_id)

    def _handle_assassination_started(self, game_id: str) -> None:
        players = self._repository.get_players(game_id)
        assassins = [player for player in players if player.role == Role.Assassin]
        if len(assassins) != 1:
            raise ValueError(f"Game {game_id} has {len(assassins)} assassins, expected 1")
        assassin = assassins[0]
        assassination_target_requested_event = self._repository.put_event(game_id,
                                                                          EventType.AssassinationTargetRequested.value,
                                                                          [assassin.id], {},
                                                                          int(datetime.now().timestamp()))
        self._comm_service.notify(assassin.id, assassination_target_requested_event)
        assassination_started_event = self._repository.put_event(game_id, EventType.AssassinationStarted.value, [], {},
                                                                 int(datetime.now().timestamp()))
        self._comm_service.broadcast(assassination_started_event)

    # todo: add docstring
    def handle_assassination_target_submitted(self, event: Event) -> None:
        if not event.payload or not event.payload.get("target_id"):
            raise ValueError("target_id is required in ASSASSINATION_TARGET_SUBMITTED event payload")
        target = self._repository.get_player(event.game_id, event.payload["target_id"])
        if not target:
            raise ValueError(f"Player {event.payload['target_id']} not found")
        attempts = self.get_assassination_attempts(event.game_id)
        game = self._repository.get_game(event.game_id)
        game.assassination_attempts = attempts - 1
        self._repository.update_game(game)
        if target.role == Role.Merlin:
            assassination_succeeded_event = self._repository.put_event(event.game_id,
                                                                       EventType.AssassinationSucceeded.value, [], {},
                                                                       int(datetime.now().timestamp()))
            self._comm_service.broadcast(assassination_succeeded_event)
            self.handle_game_ended(event.game_id)
            return

        payload = {"target_id": target.id, "role": target.role.value}
        assassination_failed_event = self._repository.put_event(event.game_id, EventType.AssassinationFailed.value, [],
                                                                payload,
                                                                int(datetime.now().timestamp()))
        self._comm_service.broadcast(assassination_failed_event)

    # todo: add docstring
    def handle_game_ended(self, game_id: str) -> None:
        game = self._repository.get_game(game_id)
        game.status = GameStatus.Finished
        self._repository.update_game(game)
        players = self._repository.get_players(game_id)
        player_roles = {player.id: player.role.value for player in players}
        payload = {"player_roles": player_roles}
        game_ended_event = self._repository.put_event(game_id, EventType.GameEnded.value, [], payload,
                                                      int(datetime.now().timestamp()))
        self._comm_service.broadcast(game_ended_event)

    # todo: add docstring
    def is_game_finished(self, game_id: str) -> bool:
        game = self._repository.get_game(game_id)
        return game.status == GameStatus.Finished


def _get_player_ids(players: list[Player], payload: dict[str, Any]) -> list[str]:
    player_ids = payload.get("player_ids", [])
    if not player_ids:
        raise ValueError("player_ids is required in GameStarted event payload")
    given_player_ids = set(player_ids)
    actual_player_ids = set([player.id for player in players])
    if given_player_ids != actual_player_ids:
        raise ValueError(f"player_ids in GameStarted event payload does not match DB, got {given_player_ids}")
    return player_ids


def _get_player_event(game_id, players) -> dict[str: Event]:
    events = dict()
    id_players = {player.id: player for player in players}
    for player in players:
        known_players = [id_players[known_player_id] for known_player_id in player.known_player_ids]
        payload = {
            "role": player.role.value,
            "known_players": [{
                "id": known_player.id,
                "name": known_player.name,
            } for known_player in known_players],
        }
        events[player.id] = Event(
            id="event_id",
            game_id=game_id,
            type=EventType.GameStarted,
            recipients=[player.id],
            payload=payload,
            timestamp=123
        )
    return events
