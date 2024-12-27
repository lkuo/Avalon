import pytest

from game_core.constants.action_type import ActionType
from game_core.constants.vote_result import VoteResult
from game_core.entities.action import Action
from game_core.entities.round import Round
from game_core.services.round_service import RoundService
from game_core.states.quest_voting_state import QuestVotingState
from game_core.states.round_voting_state import RoundVotingState
from game_core.constants.state_name import StateName
from game_core.states.team_selection_state import TeamSelectionState

QUEST_NUMBER = 3
ROUND_NUMBER = 4
ACTION_ID = "action_id"
GAME_ID = "game_id"
PLAYER_ID = "player_id"
CAST_ROUND_VOTE_PAYLOAD = {}


@pytest.fixture
def team_selection_state(mocker):
    return mocker.MagicMock(spec=TeamSelectionState)


@pytest.fixture
def quest_voting_state(mocker):
    return mocker.MagicMock(spec=QuestVotingState)


@pytest.fixture
def round_service(mocker):
    return mocker.MagicMock(spec=RoundService)


@pytest.fixture
def cast_round_vote_action():
    return Action(
        ACTION_ID,
        GAME_ID,
        PLAYER_ID,
        ActionType.CastRoundVote,
        CAST_ROUND_VOTE_PAYLOAD,
    )


@pytest.fixture
def round_voting_state(team_selection_state, quest_voting_state, round_service):
    round_voting_state = RoundVotingState(round_service)
    round_voting_state.set_states(team_selection_state, quest_voting_state)
    return round_voting_state


def test_round_voting_state_when_round_not_voted(
    round_voting_state,
    round_service,
    cast_round_vote_action,
    mocker,
):
    # Given
    current_round = mocker.MagicMock(spec=Round)
    current_round.result = None
    round_service.get_current_round.return_value = current_round

    # When
    next_state = round_voting_state.handle(cast_round_vote_action)

    # Then
    assert round_voting_state.name == StateName.RoundVoting
    assert next_state == round_voting_state
    round_service.handle_cast_round_vote.assert_called_once_with(cast_round_vote_action)


def test_round_voting_state_when_proposal_passed(
    round_voting_state,
    team_selection_state,
    round_service,
    cast_round_vote_action,
    mocker,
):
    # Given
    current_round = mocker.MagicMock(spec=Round)
    current_round.result = VoteResult.Fail
    round_service.get_current_round.return_value = current_round

    # When
    next_state = round_voting_state.handle(cast_round_vote_action)

    # Then
    assert next_state == team_selection_state
    round_service.handle_cast_round_vote.assert_called_once_with(cast_round_vote_action)
