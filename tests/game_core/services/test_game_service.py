import random
from unittest.mock import call

import pytest

from game_core.constants.event_type import EventType
from game_core.constants.game_status import GameStatus
from game_core.constants.role import Role
from game_core.entities.event import Event
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
    player_service.get_players.return_value = players
    events = [
        _get_player_event(game_id, merlin_player.id, Role.Merlin, [mordred_player]),
        _get_player_event(game_id, mordred_player.id, Role.Mordred, [merlin_player]),
        _get_player_event(game_id, percival_player.id, Role.Percival, [merlin_player, mordred_player]),
        _get_player_event(game_id, villager_player1.id, Role.Villager, []),
        _get_player_event(game_id, villager_player2.id, Role.Villager, [])
    ]
    player_ids = [p.id for p in players]
    random.shuffle(player_ids)
    game_started_event = Event(game_id, EventType.GAME_STARTED, [], {"player_ids": player_ids})

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
    event = Event(game_id, EventType.GAME_STARTED, [], mocker.MagicMock())
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
    event = Event(game_id, EventType.GAME_STARTED, [], mocker.MagicMock())
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
    event = Event(game_id, EventType.GAME_STARTED, [], {"player_ids": player_ids})
    game = mocker.MagicMock()
    game.status = GameStatus.NotStarted
    repository.get_game.return_value = game
    players = [Player("player1", "player1", "secret1", Role.Merlin)]
    player_service.get_players.return_value = players
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
        EventType.GAME_STARTED,
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
