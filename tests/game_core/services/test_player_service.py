import pytest

from game_core.constants.event_type import EventType
from game_core.constants.role import Role
from game_core.entities.event import Event
from game_core.entities.player import Player
from game_core.repository import Repository
from game_core.services.comm_service import CommService

from unittest.mock import patch

from game_core.services.player_service import PlayerService


@pytest.fixture
def comm_service(mocker):
    return mocker.MagicMock(spec=CommService)


@pytest.fixture
def repository(mocker):
    return mocker.MagicMock(spec=Repository)


@pytest.fixture
def player_service(comm_service, repository):
    return PlayerService(comm_service, repository)


def test_handle_player_joined(mocker, comm_service, repository, player_service):
    # Given
    game_id = "game_id"
    player_id = "player_id"
    name = "TestPlayer"
    secret = "uuid-v4-id"
    mock_uuid = mocker.patch('game_core.services.player_service.uuid')
    mock_uuid.uuid4.return_value = secret
    timestamp = 12345
    event_type = EventType.PlayerJoined
    event = Event("event_id", game_id, event_type, [], {"player_name": name}, timestamp)
    player = Player(player_id,  "game_id",name, secret)
    repository.put_player.return_value = player
    player_joined_event = Event("event_id", game_id, event_type, [], {"player_id": player_id, "player_name": name}, timestamp)
    repository.put_event.return_value = player_joined_event

    # When
    player_service.handle_player_joined(event)

    # Then
    repository.put_player.assert_called_once_with(game_id, name, secret)
    repository.put_event.assert_called_once_with(game_id, event_type.value, [],
                                                 {"player_id": player_id, "player_name": name}, timestamp)
    comm_service.broadcast.assert_called_once_with(player_joined_event)


@pytest.mark.parametrize("payload", [None, {"invalid_field": "some value"}])
def test_handle_player_joined_with_invalid_payload(comm_service, repository, player_service, payload):
    # Given
    game_id = "game_id"
    event_type = EventType.PlayerJoined
    timestamp = 12345
    event = Event("event_id", game_id, event_type, [], payload, timestamp)

    # When
    with pytest.raises(ValueError):
        player_service.handle_player_joined(event)

    # Then
    repository.put_player.assert_not_called()
    repository.put_event.assert_not_called()
    comm_service.broadcast.assert_not_called()


def test_assign_roles(mocker, repository, player_service):
    # Given
    game_id = "game_id"
    roles = {
        Role.Merlin.value: [Role.Mordred.value],
        Role.Percival.value: [Role.Merlin.value, Role.Mordred.value],
        Role.Mordred.value: [Role.Percival.value],
    }
    players = [Player(f"player_id_{i}", "game_id", f"Player {i}", f"secret_{i}") for i in range(10)]
    mocker.patch('game_core.services.player_service.random.shuffle', return_value=players)
    repository.get_players.return_value = players
    repository.put_players.side_effect = lambda _, _players: _players

    # When
    assigned_players = player_service.assign_roles(game_id, roles)

    # Then

    merlin_players = [p for p in players if p.role == Role.Merlin]
    mordred_players = [p for p in players if p.role == Role.Mordred]
    percival_players = [p for p in players if p.role == Role.Percival]
    villagers = [p for p in players if p.role == Role.Villager]
    assert len(merlin_players) == 1
    assert len(mordred_players) == 1
    assert len(percival_players) == 1
    assert len(villagers) == len(players) - 3

    assert len(assigned_players) == len(players)
    repository.get_players.assert_called_once_with(game_id)
    repository.put_players.assert_called_once_with(game_id, assigned_players)
    assert merlin_players[0].known_player_ids == [mordred_players[0].id]
    assert set(percival_players[0].known_player_ids) == {merlin_players[0].id, mordred_players[0].id}
    assert mordred_players[0].known_player_ids == [percival_players[0].id]
