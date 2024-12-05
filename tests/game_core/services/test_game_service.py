import random
from unittest.mock import call

import pytest

from game_core.constants.event_type import EventType
from game_core.constants.game_status import GameStatus
from game_core.constants.role import Role
from game_core.entities.event import Event
from game_core.entities.game import Game, GameConfig
from game_core.entities.player import Player
from game_core.repository import Repository
from game_core.services.comm_service import CommService
from game_core.services.game_service import GameService
from game_core.services.player_service import PlayerService

TIMESTAMP = 1234567


@pytest.fixture
def repository(mocker):
    return mocker.Mock(spec=Repository)


@pytest.fixture
def player_service(mocker):
    return mocker.Mock(spec=PlayerService)


@pytest.fixture
def comm_service(mocker):
    return mocker.Mock(spec=CommService)


@pytest.fixture
def game_service(repository, player_service, comm_service):
    return GameService(repository, player_service, comm_service)


def test_handle_game_started(mocker, game_service, repository, player_service, comm_service):
    # Given
    mock_event = mocker.patch("game_core.services.game_service.Event")
    mock_event.side_effect = lambda *args, **kwargs: Event(*args, **kwargs, timestamp=TIMESTAMP)
    game_id = "game_id"
    game_config = mocker.MagicMock()
    game = mocker.MagicMock()
    game.status = GameStatus.NotStarted
    game.config = game_config
    repository.get_game.return_value = game
    merlin_player = Player("player1", "merlin_player", "secret1", Role.Merlin)
    mordred_player = Player("player2", "mordred_player", "secret2", Role.Mordred)
    percival_player = Player("player3", "percival_player", "secret3", Role.Percival)
    villager_player1 = Player("player4", "villager_player1", "secret4", Role.Villager)
    villager_player2 = Player("player5", "villager_player2", "secret5", Role.Villager)
    merlin_player.known_player_ids = [mordred_player.id]
    mordred_player.known_player_ids = [merlin_player.id]
    percival_player.known_player_ids = [merlin_player.id, mordred_player.id]
    players = [
        merlin_player,
        mordred_player,
        percival_player,
        villager_player1,
        villager_player2
    ]
    player_service.assign_roles.return_value = players
    repository.get_players.return_value = players
    events = [
        _get_player_event(game_id, merlin_player.id, Role.Merlin, [mordred_player]),
        _get_player_event(game_id, mordred_player.id, Role.Mordred, [merlin_player]),
        _get_player_event(game_id, percival_player.id, Role.Percival, [merlin_player, mordred_player]),
        _get_player_event(game_id, villager_player1.id, Role.Villager, []),
        _get_player_event(game_id, villager_player2.id, Role.Villager, [])
    ]
    player_ids = [p.id for p in players]
    random.shuffle(player_ids)
    game_started_event = Event(game_id, EventType.GameStarted, [], {"player_ids": player_ids})

    # When
    game_service.handle_game_started(game_started_event)

    # Then
    player_service.assign_roles.assert_called_once_with(game_id, game.config.roles)
    repository.put_events.assert_called_once_with(events)
    calls = [call(player.id, event) for player, event in zip(players, events)]
    comm_service.notify.assert_has_calls(calls, any_order=True)
    game.status = GameStatus.InProgress
    game.player_ids = player_ids
    repository.put_game.assert_called_once_with(game)


@pytest.mark.parametrize("game_status", [GameStatus.InProgress, GameStatus.Finished])
def test_handle_game_started_with_game_already_started(mocker, game_service, player_service, repository, comm_service,
                                                       game_status):
    # Given
    game_id = "game_id"
    event = Event(game_id, EventType.GameStarted, [], mocker.MagicMock())
    game = mocker.MagicMock()
    game.status = game_status
    repository.get_game.return_value = game

    # When
    with pytest.raises(ValueError):
        game_service.handle_game_started(event)

    # Then
    repository.get_game.assert_called_once_with(game_id)
    player_service.assign_roles.assert_not_called()
    repository.put_events.assert_not_called()
    repository.put_events.assert_not_called()
    comm_service.notify.assert_not_called()


def test_handle_game_started_with_game_not_exists(mocker, game_service, player_service, repository, comm_service):
    # Given
    game_id = "game_id"
    event = Event(game_id, EventType.GameStarted, [], mocker.MagicMock())
    repository.get_game.return_value = None

    # When
    with pytest.raises(ValueError):
        game_service.handle_game_started(event)

    # Then
    repository.get_game.assert_called_once_with(game_id)
    player_service.assign_roles.assert_not_called()
    repository.put_events.assert_not_called()
    repository.put_events.assert_not_called()
    comm_service.notify.assert_not_called()


@pytest.mark.parametrize("player_ids", [[], ["invalid_id1", "invalid_id2"]])
def test_handle_game_started_with_invalid_player_ids(mocker, game_service, player_service, repository, comm_service,
                                                     player_ids):
    # Given
    game_id = "game_id"
    event = Event(game_id, EventType.GameStarted, [], {"player_ids": player_ids})
    game = mocker.MagicMock()
    game.status = GameStatus.NotStarted
    repository.get_game.return_value = game
    players = [Player("player1", "player1", "secret1", Role.Merlin)]
    repository.get_players.return_value = players
    player_service.assign_roles.return_value = players

    # When
    with pytest.raises(ValueError):
        game_service.handle_game_started(event)

    # Then
    repository.get_game.assert_called_once_with(game_id)
    player_service.assign_roles.assert_called_once_with(game_id, game.config.roles)
    repository.put_events.assert_not_called()
    comm_service.notify.assert_not_called()


def _get_player_event(game_id, player_id, role, known_players) -> Event:
    return Event(
        game_id,
        EventType.GameStarted,
        [player_id],
        {
            "role": role.value,
            "known_players": [{
                "id": kp.id,
                "name": kp.name,
            } for kp in known_players]
        },
        TIMESTAMP,
    )


GAME_ASSASSINATION_ATTEMPTS = 2


@pytest.mark.parametrize("game_assassination_attempts, result", [(None, GAME_ASSASSINATION_ATTEMPTS), (0, 0), (1, 1)])
def test_get_assassination_attempts(mocker, game_service, repository, game_assassination_attempts, result):
    # Given
    game_id = "game_id"
    game = mocker.MagicMock(spec=Game)
    game.assassination_attempts = game_assassination_attempts
    game_config = mocker.MagicMock(spec=GameConfig)
    game_config.assassination_attempts = GAME_ASSASSINATION_ATTEMPTS
    game.config = game_config
    repository.get_game.return_value = game

    # When
    res = game_service.get_assassination_attempts(game_id)

    # Then
    assert res == result


def test_get_assassination_attempts_with_game_not_found(game_service, repository):
    # Given
    game_id = "game_id"
    repository.get_game.return_value = None

    # When
    with pytest.raises(ValueError):
        game_service.get_assassination_attempts(game_id)


def test_get_assassination_attempts_with_game_config_not_found(mocker, game_service, repository):
    # Given
    game_id = "game_id"
    game = mocker.MagicMock(spec=Game)
    game.config = None
    repository.get_game.return_value = None

    # When
    with pytest.raises(ValueError):
        game_service.get_assassination_attempts(game_id)


def test_on_enter_end_game_state(mocker, game_service, repository, comm_service):
    # Given
    game_id = "game_id"
    game = mocker.MagicMock(spec=Game)
    assassin_id = "assassin_id"
    repository.get_players.return_value = [
        Player("player1", "player1", "secret1", Role.Merlin),
        Player("player2", "player2", "secret2", Role.Mordred),
        Player(assassin_id, "player3", "secret3", Role.Assassin),
    ]
    assassination_target_requested_event = mocker.MagicMock(spec=Event)
    assassination_started_event = mocker.MagicMock(spec=Event)
    repository.put_event.side_effect = [assassination_target_requested_event, assassination_started_event]
    timestamp = 1234567890
    mock_datetime = mocker.patch("game_core.services.game_service.datetime")
    mock_datetime.now.return_value.timestamp.return_value = timestamp

    # When
    game_service.on_enter_end_game_state(game_id)

    # Then
    repository.put_event.assert_has_calls([
        call(game_id, EventType.AssassinationTargetRequested.value, [assassin_id], {}, timestamp),
        call(game_id, EventType.AssassinationStarted.value, [], {}, timestamp),
    ])
    comm_service.notify.assert_called_once_with(assassin_id, assassination_target_requested_event)
    comm_service.broadcast.assert_called_once_with(assassination_started_event)


def test_handle_assassination_target_submitted_failed(mocker, game_service, repository, comm_service):
    # Given
    game_id = "game_id"
    target_id = "target_id"
    event = mocker.MagicMock(spec=Event)
    event.game_id = game_id
    event.payload = {"target_id": target_id}
    game = mocker.MagicMock(spec=Game)
    game_config = mocker.MagicMock(spec=GameConfig)
    game_config.assassination_attempts = GAME_ASSASSINATION_ATTEMPTS
    game.config = game_config
    game.assassination_attempts = 1
    repository.get_game.return_value = game
    player = mocker.MagicMock(spec=Player)
    player.id = target_id
    player.role = Role.Percival
    repository.get_player.return_value = player
    assassination_failed_event = mocker.MagicMock(spec=Event)
    repository.put_event.return_value = assassination_failed_event
    timestamp = 1234567890
    mock_datetime = mocker.patch("game_core.services.game_service.datetime")
    mock_datetime.now.return_value.timestamp.return_value = timestamp

    # When
    game_service.handle_assassination_target_submitted(event)

    # Then
    game.assassination_attempts = GAME_ASSASSINATION_ATTEMPTS - 1
    repository.update_game.assert_called_once_with(game)
    repository.put_event.assert_called_once_with(game_id, EventType.AssassinationFailed.value, [], {
        "target_id": target_id,
        "role": player.role.value
    }, timestamp)
    comm_service.broadcast.assert_called_once_with(assassination_failed_event)


def test_handle_assassination_target_submitted_succeeded(mocker, game_service, repository, comm_service):
    # Given
    game_id = "game_id"
    target_id = "target_id"
    event = mocker.MagicMock(spec=Event)
    event.game_id = game_id
    event.payload = {"target_id": target_id}
    game = mocker.MagicMock(spec=Game)
    game_config = mocker.MagicMock(spec=GameConfig)
    game_config.assassination_attempts = GAME_ASSASSINATION_ATTEMPTS
    game.config = game_config
    game.assassination_attempts = 1
    repository.get_game.return_value = game
    player = mocker.MagicMock(spec=Player)
    player.id = target_id
    player.role = Role.Merlin
    repository.get_player.return_value = player
    assassination_succeeded_event = mocker.MagicMock(spec=Event)
    repository.put_event.return_value = assassination_succeeded_event
    timestamp = 1234567890
    mock_datetime = mocker.patch("game_core.services.game_service.datetime")
    mock_datetime.now.return_value.timestamp.return_value = timestamp
    game_service.handle_game_ended = mocker.MagicMock()

    # When
    game_service.handle_assassination_target_submitted(event)

    # Then
    game.assassination_attempts = GAME_ASSASSINATION_ATTEMPTS - 1
    repository.update_game.assert_called_once_with(game)
    repository.put_event.assert_called_once_with(game_id, EventType.AssassinationSucceeded.value, [], {}, timestamp)
    comm_service.broadcast.assert_called_once_with(assassination_succeeded_event)
    game_service.handle_game_ended.assert_called_once_with(game_id)


@pytest.mark.parametrize("payload", [None, {}])
def test_handle_assassination_target_submitted_with_invalid_event_payload(mocker, game_service, repository,
                                                                          comm_service,
                                                                          payload):
    # Given
    game_id = "game_id"
    event = mocker.MagicMock(spec=Event)
    event.game_id = game_id
    event.payload = payload

    # When
    with pytest.raises(ValueError):
        game_service.handle_assassination_target_submitted(event)

    # Then
    repository.update_game.assert_not_called()
    repository.put_event.assert_not_called()
    comm_service.broadcast.assert_not_called()


def test_handle_assassination_target_submitted_with_target_not_found(mocker, game_service, repository, comm_service):
    # Given
    game_id = "game_id"
    target_id = "target_id"
    event = mocker.MagicMock(spec=Event)
    event.game_id = game_id
    event.payload = {"target_id": target_id}
    repository.get_player.return_value = None

    # When
    with pytest.raises(ValueError):
        game_service.handle_assassination_target_submitted(event)

    # Then
    repository.get_player.assert_called_once_with(game_id, target_id)
    repository.update_game.assert_not_called()
    repository.put_event.assert_not_called()
    comm_service.broadcast.assert_not_called()


@pytest.mark.parametrize("game_status, result", [(GameStatus.InProgress, False), (GameStatus.Finished, True)])
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


def test_handle_game_ended(mocker, game_service, repository, comm_service):
    # Given
    game_id = "game_id"
    game = mocker.MagicMock(spec=Game)
    repository.get_game.return_value = game
    players = [
        Player("player1", "player1", "secret1", Role.Merlin),
        Player("player2", "player2", "secret2", Role.Mordred),
        Player("player3", "player3", "secret3", Role.Assassin),
    ]
    repository.get_players.return_value = players
    game_ended_event = mocker.MagicMock(spec=Event)
    repository.put_event.return_value = game_ended_event
    timestamp = 1234567890
    mock_datetime = mocker.patch("game_core.services.game_service.datetime")
    mock_datetime.now.return_value.timestamp.return_value = timestamp

    # When
    game_service.handle_game_ended(game_id)

    # Then
    game.status = GameStatus.Finished
    repository.update_game.assert_called_once_with(game)
    payload = {"player_roles": {player.id: player.role.value for player in players}}
    repository.put_event.assert_called_once_with(game_id, EventType.GameEnded.value, [], payload, timestamp)
    comm_service.broadcast.assert_called_once_with(game_ended_event)
