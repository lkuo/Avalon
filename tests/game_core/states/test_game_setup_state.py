import pytest

from game_core.entities.event import Event
from game_core.constants.event_type import EventType
from game_core.services.player_service import PlayerService
from game_core.states.game_setup_state import GameSetupState
from game_core.constants.state_name import StateName


@pytest.fixture
def state(mocker):
    return mocker.MagicMock()


@pytest.fixture
def game_service(mocker):
    return mocker.MagicMock()


@pytest.fixture
def player_service(mocker):
    return mocker.MagicMock(spec=PlayerService)


def test_game_setup_state_with_game_started_event(state, game_service, player_service):
    # Given
    event = Event(game_id="game_id", type=EventType.GAME_STARTED, recipient=[], payload={})
    game_setup_state = GameSetupState(state, game_service, player_service)

    # When
    next_state = game_setup_state.handle(event)

    # Then
    assert game_setup_state.name == StateName.GAME_SETUP
    assert next_state == state
    player_service.handle_player_joined.assert_not_called()
    game_service.handle_game_started.assert_called_once_with(event)


def test_game_setup_state_with_player_joined_event(state, game_service, player_service):
    # Given
    event = Event(game_id="game_id", type=EventType.PLAYER_JOINED, recipient=[], payload={})
    game_setup_state = GameSetupState(state, game_service, player_service)

    # When
    next_state = game_setup_state.handle(event)

    # Then
    assert game_setup_state.name == StateName.GAME_SETUP
    assert next_state == game_setup_state
    player_service.handle_player_joined.assert_called_once_with(event)
    game_service.handle_game_started.assert_not_called()


def test_game_setup_state_invalid_event(state, game_service, player_service):
    # Given
    invalid_event = Event(game_id="game_id", type=EventType.QUEST_STARTED, recipient=[], payload={})
    game_setup_state = GameSetupState(state, game_service, player_service)

    # When
    with pytest.raises(ValueError):
        game_setup_state.handle(invalid_event)

    # Then
    player_service.handle_player_joined.assert_not_called()
    game_service.handle_game_started.assert_not_called()
