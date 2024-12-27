import pytest

from game_core.constants.action_type import ActionType
from game_core.constants.vote_result import VoteResult
from game_core.entities.action import Action
from game_core.services.quest_service import QuestService
from game_core.services.round_service import RoundService
from game_core.constants.state_name import StateName
from game_core.states.team_selection_state import TeamSelectionState

ACTION_ID = "action_id"
GAME_ID = "game_id"
PLAYER_ID = "player_id"
SUBMIT_TEAM_PROPOSAL_PAYLOAD = {}


@pytest.fixture
def round_voting_state(mocker):
    return mocker.MagicMock()


@pytest.fixture
def end_game_state(mocker):
    return mocker.MagicMock()


@pytest.fixture
def quest_service(mocker):
    return mocker.MagicMock(spec=QuestService)


@pytest.fixture
def round_service(mocker):
    return mocker.MagicMock(spec=RoundService)


@pytest.fixture
def team_selection_state(
    quest_service, round_service, round_voting_state, end_game_state
):
    team_selection_state = TeamSelectionState(quest_service, round_service)
    team_selection_state.set_states(round_voting_state, end_game_state)
    return team_selection_state


@pytest.fixture
def submit_team_proposal_action():
    return Action(
        ACTION_ID,
        GAME_ID,
        PLAYER_ID,
        ActionType.SubmitTeamProposal,
        SUBMIT_TEAM_PROPOSAL_PAYLOAD,
    )


def test_team_selection_state(
    team_selection_state,
    round_voting_state,
    submit_team_proposal_action,
    quest_service,
    round_service,
):
    # Given
    # When
    next_state = team_selection_state.handle(submit_team_proposal_action)

    # Then
    assert team_selection_state.name == StateName.TeamSelection
    assert next_state == round_voting_state
    round_service.handle_submit_team_proposal.assert_called_once_with(
        submit_team_proposal_action
    )


def test_team_selection_state_with_invalid_event(
    team_selection_state,
    round_service,
):
    # Given
    invalid_action = Action(
        ACTION_ID,
        GAME_ID,
        PLAYER_ID,
        ActionType.StartGame,
        SUBMIT_TEAM_PROPOSAL_PAYLOAD,
    )

    # When
    with pytest.raises(ValueError):
        team_selection_state.handle(invalid_action)

    # Then
    round_service.handle_submit_team_proposal.assert_not_called()


def test_team_selection_state_on_enter_with_final_proposal_failed(
    team_selection_state,
    quest_service,
):
    # Given
    quest_service.is_final_proposal_failed.return_value = False
    quest_service.has_majority.return_value = False

    # When
    team_selection_state.on_enter(GAME_ID)

    # Then
    quest_service.complete_current_quest.assert_not_called()
    quest_service.handle_on_enter_team_selection_state.assert_called_once_with(GAME_ID)


def test_team_selection_state_on_enter_with_has_majority(
    team_selection_state,
    end_game_state,
    quest_service,
):
    # Given
    quest_service.is_final_proposal_failed.return_value = True
    quest_service.has_majority.return_value = True

    # When
    next_state = team_selection_state.on_enter(GAME_ID)

    # Then
    quest_service.complete_current_quest.assert_called_once_with(
        GAME_ID, VoteResult.Fail
    )
    quest_service.handle_on_enter_team_selection_state.assert_not_called()
    assert next_state == end_game_state
