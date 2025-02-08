import random
from typing import Any

import pytest

from game_core.constants.action_type import ActionType
from game_core.constants.game_status import GameStatus
from game_core.constants.role import Role
from game_core.entities.action import Action
from game_core.entities.game import Game, GameConfig
from game_core.entities.player import Player
from game_core.repository import Repository
from game_core.services.event_service import EventService
from game_core.services.game_service import GameService
from game_core.services.player_service import PlayerService

ACTION_ID = "action_id"
GAME_ID = "game_id"
PLAYER_ID = "player_id"
TARGET_ID = "target_id"


@pytest.fixture
def repository(mocker):
    return mocker.Mock(spec=Repository)


@pytest.fixture
def player_service(mocker):
    return mocker.Mock(spec=PlayerService)


@pytest.fixture
def event_service(mocker):
    return mocker.Mock(spec=EventService)


@pytest.fixture
def game_service(repository, player_service, event_service):
    return GameService(player_service, event_service, repository)


@pytest.fixture
def start_game_action():
    return Action(ACTION_ID, GAME_ID, PLAYER_ID, ActionType.StartGame, {})


@pytest.fixture
def submit_assassination_target_action():
    return Action(
        ACTION_ID, GAME_ID, PLAYER_ID, ActionType.SubmitAssassinationTarget, {}
    )


def test_handle_start_game(
    mocker, game_service, repository, player_service, event_service, start_game_action
):
    # Given
    game_config = mocker.MagicMock()
    game = mocker.MagicMock()
    game.status = GameStatus.NotStarted
    game.config = game_config
    repository.get_game.return_value = game
    merlin_player = Player(
        "game_id_player_player1", "game_id", "merlin_player", "secret1", Role.Merlin
    )
    mordred_player = Player(
        "game_id_player_player2", "game_id", "mordred_player", "secret2", Role.Mordred
    )
    percival_player = Player(
        "game_id_player_player3", "game_id", "percival_player", "secret3", Role.Percival
    )
    villager_player1 = Player(
        "game_id_player_player4", "game_id", "villager_player1", "secret4", Role.Villager
    )
    villager_player2 = Player(
        "game_id_player_player5", "game_id", "villager_player2", "secret5", Role.Villager
    )
    merlin_player.known_player_ids = [mordred_player.id]
    mordred_player.known_player_ids = [merlin_player.id]
    percival_player.known_player_ids = [merlin_player.id, mordred_player.id]
    players = [
        merlin_player,
        mordred_player,
        percival_player,
        villager_player1,
        villager_player2,
    ]
    player_service.assign_roles.return_value = players
    repository.get_players.return_value = players
    player_ids = [p.id.split("_")[-1] for p in players]
    random.shuffle(player_ids)
    start_game_action.payload = {"player_ids": player_ids}

    # When
    game_service.handle_start_game(start_game_action)

    # Then
    player_service.assign_roles.assert_called_once_with(GAME_ID, game.config.roles, game.config.known_roles)
    event_service.create_game_started_events.assert_called_once_with(GAME_ID, players)
    game.status = GameStatus.InProgress
    game.player_ids = player_ids
    repository.update_game.assert_called_once_with(game)


@pytest.mark.parametrize("game_status", [GameStatus.InProgress, GameStatus.Finished])
def test_handle_start_game_with_game_already_started(
    mocker,
    game_service,
    player_service,
    repository,
    game_status,
    start_game_action,
):
    # Given
    game = mocker.MagicMock()
    game.status = game_status
    repository.get_game.return_value = game

    # When
    with pytest.raises(ValueError):
        game_service.handle_start_game(start_game_action)

    # Then
    repository.get_game.assert_called_once_with(GAME_ID)
    player_service.assign_roles.assert_not_called()
    repository.update_game.assert_not_called()


def test_handle_game_started_with_game_not_exists(
    game_service, player_service, repository, start_game_action
):
    # Given
    game_id = "game_id"
    repository.get_game.return_value = None

    # When
    with pytest.raises(ValueError):
        game_service.handle_start_game(start_game_action)

    # Then
    repository.get_game.assert_called_once_with(game_id)
    player_service.assign_roles.assert_not_called()
    repository.put_event.assert_not_called()


@pytest.mark.parametrize("player_ids", [[], ["invalid_id1", "invalid_id2"]])
def test_handle_game_started_with_invalid_player_ids(
    mocker, game_service, player_service, repository, player_ids, start_game_action
):
    # Given
    game_id = "game_id"
    game = mocker.MagicMock()
    game.status = GameStatus.NotStarted
    repository.get_game.return_value = game
    players = [Player("player_id", GAME_ID, "player1", "secret1", Role.Merlin)]
    repository.get_players.return_value = players
    player_service.assign_roles.return_value = players

    # When
    with pytest.raises(ValueError):
        game_service.handle_start_game(start_game_action)

    # Then
    repository.get_game.assert_called_once_with(game_id)
    player_service.assign_roles.assert_called_once_with(game_id, game.config.roles, game.config.known_roles)
    repository.put_event.assert_not_called()


def _get_payload(role, known_players) -> dict[str, Any]:
    return {
        "role": role.value,
        "known_players": [
            {
                "id": kp.id,
                "name": kp.name,
            }
            for kp in known_players
        ],
    }


GAME_ASSASSINATION_ATTEMPTS = 2


@pytest.mark.parametrize(
    "game_assassination_attempts, result",
    [(None, GAME_ASSASSINATION_ATTEMPTS), (0, 0), (1, 1)],
)
def test_get_assassination_attempts(
    mocker, game_service, repository, game_assassination_attempts, result
):
    # Given
    game = mocker.MagicMock(spec=Game)
    game.assassination_attempts = game_assassination_attempts
    game_config = mocker.MagicMock(spec=GameConfig)
    game_config.assassination_attempts = GAME_ASSASSINATION_ATTEMPTS
    game.config = game_config
    repository.get_game.return_value = game

    # When
    res = game_service.get_assassination_attempts(GAME_ID)

    # Then
    assert res == result


def test_get_assassination_attempts_with_game_not_found(game_service, repository):
    # Given
    game_id = "game_id"
    repository.get_game.return_value = None

    # When
    with pytest.raises(ValueError):
        game_service.get_assassination_attempts(game_id)


def test_get_assassination_attempts_with_game_config_not_found(
    mocker, game_service, repository
):
    # Given
    game = mocker.MagicMock(spec=Game)
    game.config = None
    repository.get_game.return_value = None

    # When
    with pytest.raises(ValueError):
        game_service.get_assassination_attempts(GAME_ID)


def test_on_enter_end_game_state(
    mocker, game_service, player_service, event_service, repository
):
    # Given
    assassin_id = "assassin_id"
    player_service.get_players.return_value = [
        Player("player_id1", "game_id", "player1", "secret1", Role.Merlin),
        Player("player_id2", "game_id", "player2", "secret2", Role.Mordred),
        Player(assassin_id, "game_id", "player3", "secret3", Role.Assassin),
    ]
    game_config = mocker.MagicMock(spec=GameConfig)
    game_config.assassination_attempts = GAME_ASSASSINATION_ATTEMPTS
    game = mocker.MagicMock(spec=Game)
    game.assassination_attempts = None
    game.config = game_config
    repository.get_game.return_value = game

    # When
    game_service.on_enter_end_game_state(GAME_ID)

    # Then
    event_service.create_assassination_started_event.assert_called_once_with(GAME_ID, 2)


def test_handle_assassination_target_submitted_failed(
    mocker,
    game_service,
    player_service,
    event_service,
    repository,
    submit_assassination_target_action,
):
    # Given
    submit_assassination_target_action.payload = {"target_id": TARGET_ID}
    game = mocker.MagicMock(spec=Game)
    game_config = mocker.MagicMock(spec=GameConfig)
    game_config.assassination_attempts = GAME_ASSASSINATION_ATTEMPTS
    game.config = game_config
    game.assassination_attempts = 1
    repository.get_game.return_value = game
    player = mocker.MagicMock(spec=Player)
    player.id = TARGET_ID
    player.role = Role.Percival
    player_service.get_player.return_value = player

    # When
    game_service.handle_submit_assassination_target(submit_assassination_target_action)

    # Then
    game.assassination_attempts = GAME_ASSASSINATION_ATTEMPTS - 1
    repository.update_game.assert_called_once_with(game)
    event_service.create_assassination_event.assert_called_once_with(
        GAME_ID, TARGET_ID, False
    )


def test_handle_assassination_target_submitted_succeeded(
    mocker,
    game_service,
    player_service,
    event_service,
    repository,
    submit_assassination_target_action,
):
    # Given
    submit_assassination_target_action.payload = {"target_id": TARGET_ID}
    game = mocker.MagicMock(spec=Game)
    game_config = mocker.MagicMock(spec=GameConfig)
    game_config.assassination_attempts = GAME_ASSASSINATION_ATTEMPTS
    game.config = game_config
    game.assassination_attempts = 1
    repository.get_game.return_value = game
    player = mocker.MagicMock(spec=Player)
    player.id = TARGET_ID
    player.role = Role.Merlin
    player_service.get_player.return_value = player
    assassin_id = "assassin_id"
    players = [
        Player("player_id1", "game_id", "player1", "secret1", Role.Merlin),
        Player("player_id2", "game_id", "player2", "secret2", Role.Mordred),
        Player(assassin_id, "game_id", "player3", "secret3", Role.Assassin),
    ]
    player_service.get_players.return_value = players

    # When
    game_service.handle_submit_assassination_target(submit_assassination_target_action)

    # Then
    game.assassination_attempts = GAME_ASSASSINATION_ATTEMPTS - 1
    event_service.create_assassination_event.assert_called_once_with(
        GAME_ID, TARGET_ID, True
    )
    game.status = GameStatus.Finished
    event_service.create_game_ended_event.assert_called_once_with(
        GAME_ID,
        {player.id: player.role.value for player in players},
    )


def test_handle_assassination_target_submitted_with_target_not_found(
    game_service, player_service, repository, submit_assassination_target_action
):
    # Given
    submit_assassination_target_action.payload = {"target_id": TARGET_ID}
    player_service.get_player.side_effect = ValueError("Player not found")

    # When
    with pytest.raises(ValueError):
        game_service.handle_submit_assassination_target(
            submit_assassination_target_action
        )

    # Then
    player_service.get_player.assert_called_once_with(TARGET_ID)
    repository.update_game.assert_not_called()
    repository.put_event.assert_not_called()


@pytest.mark.parametrize(
    "game_status, result", [(GameStatus.InProgress, False), (GameStatus.Finished, True)]
)
def test_is_game_finished(mocker, game_service, repository, game_status, result):
    # Given
    game_id = "game_id"
    game = mocker.MagicMock(spec=Game)
    game.status = game_status
    repository.get_game.return_value = game

    # When
    res = game_service.is_game_finished(game_id)

    # Then
    assert res == result


def test_handle_game_ended(
    mocker, game_service, player_service, event_service, repository
):
    # Given
    game = mocker.MagicMock(spec=Game)
    repository.get_game.return_value = game
    players = [
        Player("player1", "game_id", "player1", "secret1", Role.Merlin),
        Player("player2", "game_id", "player2", "secret2", Role.Mordred),
        Player("player3", "game_id", "player3", "secret3", Role.Assassin),
    ]
    player_service.get_players.return_value = players

    # When
    game_service.handle_game_ended(GAME_ID)

    # Then
    game.status = GameStatus.Finished
    repository.update_game.assert_called_once_with(game)
    player_roles = {player.id: player.role.value for player in players}
    event_service.create_game_ended_event.assert_called_once_with(GAME_ID, player_roles)
