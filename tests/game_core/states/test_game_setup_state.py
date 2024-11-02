import pytest

from game_core.entities.event import Event
from game_core.event_type import EventType
from game_core.services.player_service import PlayerService
from game_core.states.game_setup_state import GameSetupState
from game_core.states.state import StateName


@pytest.fixture
def state(mocker):
    return mocker.MagicMock()


@pytest.fixture
def player_service(mocker):
    return mocker.MagicMock(spec=PlayerService)


def test_game_setup_state(state, player_service):
    # Given
    event = Event(game_id="game_id", sk_id="", type=EventType.GAME_STARTED, recipient=[], payload={})
    game_setup_state = GameSetupState(state, player_service)

    # When
    next_state = game_setup_state.handle(event)

    # Then
    assert game_setup_state.name == StateName.GAME_SETUP
    assert next_state == state
    player_service.initialize.assert_called_once_with(event.game_id)


def test_game_setup_state_invalid_event(state, player_service):
    # Given
    invalid_event = Event(game_id="game_id", sk_id="", type=EventType.MISSION_STARTED, recipient=[], payload={})
    game_setup_state = GameSetupState(state, player_service)

    # When
    with pytest.raises(ValueError):
        game_setup_state.handle(invalid_event)

    # Then
    player_service.initialize.assert_not_called()
