import pytest

from game_core.constants.action_type import ActionType
from game_core.constants.state_name import StateName
from game_core.entities.action import Action
from game_core.entities.game import Game
from game_core.repository import Repository
from game_core.services.comm_service import CommService
from game_core.state_machine import StateMachine
from game_core.states.end_game_state import EndGameState
from game_core.states.game_setup_state import GameSetupState
from game_core.states.quest_voting_state import QuestVotingState
from game_core.states.round_voting_state import RoundVotingState
from game_core.states.team_selection_state import TeamSelectionState

ACTION_ID = "action_id"
GAME_ID = "game_id"
PLAYER_ID = "player_id"


@pytest.fixture
def comm_service(mocker):
    return mocker.MagicMock(spec=CommService)


@pytest.fixture
def repository(mocker):
    return mocker.MagicMock(spec=Repository)


@pytest.fixture
def state_machine(mocker, comm_service, repository):
    game = mocker.MagicMock(spec=Game)
    game.state = StateName.GameSetup.value
    repository.get_game.return_value = game
    return StateMachine(comm_service, repository, GAME_ID)


@pytest.fixture
def action():
    return Action(ACTION_ID, GAME_ID, PLAYER_ID, ActionType.StartGame, {})


@pytest.mark.parametrize(
    "state_name, expected_state",
    [
        (StateName.GameSetup.value, GameSetupState),
        (StateName.TeamSelection.value, TeamSelectionState),
        (StateName.QuestVoting.value, QuestVotingState),
        (StateName.RoundVoting.value, RoundVotingState),
        (StateName.EndGame.value, EndGameState),
    ],
)
def test_setup_states(mocker, comm_service, repository, state_name, expected_state):
    # Given
    game = mocker.MagicMock(spec=Game)
    game.state = state_name
    repository.get_game.return_value = game

    # When
    state_machine = StateMachine(comm_service, repository, GAME_ID)

    # Then
    assert isinstance(state_machine._current_state, expected_state)


def test_handle_action_with_invalid_payload(mocker, action, state_machine):
    # Given
    action.payload = None
    state_machine._current_state = mocker.MagicMock()

    # When
    with pytest.raises(ValueError):
        state_machine.handle_action(action)

    # Then
    state_machine._current_state.handle.assert_not_called()


def test_handle_action(mocker, action, state_machine):
    # Given
    mock_current_state = mocker.MagicMock()
    mock_next_state = mocker.MagicMock()
    mock_current_state.handle.return_value = mock_next_state
    mock_next_state.on_enter.return_value = None
    state_machine._current_state = mock_current_state

    # When
    state_machine.handle_action(action)

    # Then
    mock_current_state.handle.assert_called_once_with(action)
    mock_current_state.on_exit.assert_called_once_with()
    mock_next_state.on_enter.assert_called_once_with()
    state_machine._current_state = mock_next_state


def test_handle_action_with_transient_state(mocker, action, state_machine):
    # Given
    mock_current_state = mocker.MagicMock()
    mock_next_state = mocker.MagicMock()
    mock_current_state.handle.return_value = mock_next_state
    mock_third_state = mocker.MagicMock()
    mock_next_state.on_enter.return_value = mock_third_state
    state_machine._current_state = mock_current_state

    # When
    state_machine.handle_action(action)

    # Then
    mock_current_state.handle.assert_called_once_with(action)
    mock_current_state.on_exit.assert_called_once_with()
    mock_next_state.on_enter.assert_called_once_with()
    state_machine._current_state = mock_third_state
