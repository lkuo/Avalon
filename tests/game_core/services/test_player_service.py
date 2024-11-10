import pytest

from game_core.constants.event_type import EventType
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


def test_handle_player_joined(mocker, comm_service, repository):
    # Given
    game_id = "game_id"
    player_id = "player_id"
    name = "TestPlayer"
    secret = "uuid-v4-id"
    mock_uuid = mocker.patch('game_core.services.player_service.uuid')
    mock_uuid.uuid4.return_value = secret
    timestamp = 12345
    event_type = EventType.PLAYER_JOINED
    event = Event(game_id, event_type, [], {"player_name": name}, timestamp)
    player = Player(player_id, name, secret)
    repository.put_player.return_value = player
    player_joined_event = Event(game_id, event_type, [], {"player_id": player_id, "player_name": name}, timestamp)
    repository.put_event.return_value = player_joined_event
    player_service = PlayerService(comm_service, repository)

    # When
    player_service.handle_player_joined(event)

    # Then
    repository.put_player.assert_called_once_with(game_id, name, secret)
    repository.put_event.assert_called_once_with(game_id, event_type.value, [],
                                                 {"player_id": player_id, "player_name": name}, timestamp)
    comm_service.broadcast.assert_called_once_with(player_joined_event)


@pytest.mark.parametrize("payload", [None, {"invalid_field": "some value"}])
def test_handle_player_joined_with_invalid_payload(comm_service, repository, payload):
    # Given
    game_id = "game_id"
    event_type = EventType.PLAYER_JOINED
    timestamp = 12345
    event = Event(game_id, event_type, [], payload, timestamp)
    player_service = PlayerService(comm_service, repository)

    # When
    with pytest.raises(ValueError):
        player_service.handle_player_joined(event)

    # Then
    repository.put_player.assert_not_called()
    repository.put_event.assert_not_called()
    comm_service.broadcast.assert_not_called()
