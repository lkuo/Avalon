import pytest

from game_core.constants.action_type import ActionType
from game_core.constants.state_name import StateName
from game_core.entities.action import Action
from game_core.services.player_service import PlayerService
from game_core.states.game_setup_state import GameSetupState

ACTION_ID = "action_id"
GAME_ID = "game_id"
PLAYER_ID = "player_id"
START_GAME_PAYLOAD = {}
JOIN_GAME_PAYLOAD = {}


@pytest.fixture
def start_game_action():
    return Action(
        ACTION_ID, GAME_ID, PLAYER_ID, ActionType.StartGame, START_GAME_PAYLOAD
    )


@pytest.fixture
def join_game_action():
    return Action(ACTION_ID, GAME_ID, PLAYER_ID, ActionType.JoinGame, JOIN_GAME_PAYLOAD)


@pytest.fixture
def team_selection_state(mocker):
    return mocker.MagicMock()


@pytest.fixture
def game_service(mocker):
    return mocker.MagicMock()


@pytest.fixture
def player_service(mocker):
    return mocker.MagicMock(spec=PlayerService)


@pytest.fixture
def game_setup_state(team_selection_state, game_service, player_service):
    game_setup_state = GameSetupState(game_service, player_service)
    game_setup_state.set_states(team_selection_state)
    return game_setup_state


def test_game_setup_state_with_start_game_action(
    team_selection_state,
    game_setup_state,
    game_service,
    player_service,
    start_game_action,
):
    # Given
    # When
    next_state = game_setup_state.handle(start_game_action)

    # Then
    assert game_setup_state.name == StateName.GameSetup
    assert next_state == team_selection_state
    player_service.handle_join_game.assert_not_called()
    game_service.handle_start_game.assert_called_once_with(start_game_action)


def test_game_setup_state_with_join_game_action(
    game_setup_state,
    game_service,
    player_service,
    join_game_action,
):
    # Given
    # When
    next_state = game_setup_state.handle(join_game_action)

    # Then
    assert game_setup_state.name == StateName.GameSetup
    assert next_state == game_setup_state
    player_service.handle_join_game.assert_called_once_with(join_game_action)
    game_service.handle_start_game.assert_not_called()


def test_game_setup_state_invalid_event(game_setup_state, game_service, player_service):
    # Given
    invalid_action = Action(
        ACTION_ID, GAME_ID, PLAYER_ID, ActionType.SubmitTeamProposal, START_GAME_PAYLOAD
    )

    # When
    with pytest.raises(ValueError):
        game_setup_state.handle(invalid_action)

    # Then
    player_service.handle_join_game.assert_not_called()
    game_service.handle_start_game.assert_not_called()
