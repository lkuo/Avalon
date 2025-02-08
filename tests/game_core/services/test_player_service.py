from unittest.mock import call

import pytest

from game_core.constants.action_type import ActionType
from game_core.constants.config import KNOWN_ROLES, DEFAULT_TEAM_SIZE_ROLES
from game_core.constants.role import Role
from game_core.entities.action import Action
from game_core.entities.player import Player
from game_core.repository import Repository
from game_core.services.event_service import EventService
from game_core.services.player_service import PlayerService

ACTION_ID = "action_id"
GAME_ID = "game_id"
PLAYER_ID = "player_id"
PLAYER_NAME = "player_name"
PLAYER_SECRET = "uuid-v4-id"


@pytest.fixture
def event_service(mocker):
    return mocker.MagicMock(spec=EventService)


@pytest.fixture
def repository(mocker):
    return mocker.MagicMock(spec=Repository)


@pytest.fixture
def player_service(repository, event_service):
    return PlayerService(event_service, repository)


@pytest.fixture
def join_game_action():
    return Action(
        ACTION_ID, GAME_ID, PLAYER_ID, ActionType.JoinGame, {"name": PLAYER_NAME}
    )


def test_handle_player_joined(
    mocker, join_game_action, repository, player_service, event_service
):
    # Given
    mock_uuid = mocker.patch("game_core.services.player_service.uuid")
    mock_uuid.uuid4.return_value = PLAYER_SECRET
    player = Player(PLAYER_ID, "game_id", PLAYER_NAME, PLAYER_SECRET)
    repository.put_player.return_value = player

    # When
    player_service.handle_join_game(join_game_action)

    # Then
    repository.put_player.assert_called_once_with(PLAYER_ID, GAME_ID, PLAYER_NAME, PLAYER_SECRET)
    event_service.create_player_joined_event.assert_called_once_with(
        PLAYER_ID, GAME_ID, PLAYER_NAME
    )


def test_handle_player_joined_with_invalid_payload(
    join_game_action, repository, event_service, player_service
):
    # Given
    join_game_action.payload = {"invalid": "payload"}

    # When
    with pytest.raises(ValueError):
        player_service.handle_join_game(join_game_action)

    # Then
    repository.put_player.assert_not_called()
    event_service.create_player_joined_event.assert_not_called()


def test_assign_roles(mocker, repository, player_service):
    # Given
    game_id = "game_id"
    roles = DEFAULT_TEAM_SIZE_ROLES[10]
    known_roles = KNOWN_ROLES
    players = [
        Player(f"player_id_{i}", "game_id", f"Player {i}", f"secret_{i}")
        for i in range(10)
    ]
    mocker.patch(
        "game_core.services.player_service.random.shuffle", return_value=players
    )
    repository.get_players.return_value = players

    # When
    assigned_players = player_service.assign_roles(game_id, roles, known_roles)

    # Then

    merlin_players = [p for p in players if p.role == Role.Merlin]
    mordred_players = [p for p in players if p.role == Role.Mordred]
    percival_players = [p for p in players if p.role == Role.Percival]
    villagers = [p for p in players if p.role == Role.Villager]
    assert len(merlin_players) == 1
    assert len(mordred_players) == 1
    assert len(percival_players) == 1
    assert len(villagers) == 4

    assert len(assigned_players) == len(players)
    repository.get_players.assert_called_once_with(game_id)
    repository.update_player.assert_has_calls([call(p) for p in players])
    morgana_player = [p for p in players if p.role == Role.Morgana][0]
    assassin_player = [p for p in players if p.role == Role.Assassin][0]
    oberon_player = [p for p in players if p.role == Role.Oberon][0]
    assert set(merlin_players[0].known_player_ids) == {morgana_player.id, assassin_player.id, oberon_player.id}
    assert set(percival_players[0].known_player_ids) == {
        merlin_players[0].id,
        morgana_player.id,
    }
    assert set(mordred_players[0].known_player_ids) == {morgana_player.id, assassin_player.id, oberon_player.id}
