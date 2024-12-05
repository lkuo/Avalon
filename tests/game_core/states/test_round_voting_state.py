import pytest

from game_core.constants.vote_result import VoteResult
from game_core.entities.event import Event
from game_core.constants.event_type import EventType
from game_core.entities.round import Round
from game_core.services.quest_service import QuestService
from game_core.services.round_service import RoundService
from game_core.states.quest_voting_state import QuestVotingState
from game_core.states.round_voting_state import RoundVotingState
from game_core.constants.state_name import StateName
from game_core.states.team_selection_state import TeamSelectionState

QUEST_NUMBER = 3
ROUND_NUMBER = 4


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
def quest_service(mocker):
    return mocker.MagicMock(spec=QuestService)


@pytest.fixture
def event():
    payload = {"quest_number": QUEST_NUMBER, "round_number": ROUND_NUMBER}
    return Event(id="event_id", game_id="game_id", type=EventType.RoundVoteCast, recipients=[], payload=payload, timestamp=123)


def test_round_voting_state_when_round_not_voted(team_selection_state, quest_voting_state, round_service, quest_service,
                                                 event):
    # Given
    round_voting_state = RoundVotingState(team_selection_state, quest_voting_state, round_service, quest_service)
    round_service.is_round_vote_completed.return_value = False

    # When
    next_state = round_voting_state.handle(event)

    # Then
    assert round_voting_state.name == StateName.RoundVoting
    assert next_state == round_voting_state
    round_service.handle_round_vote_cast.assert_called_once_with(event)
    round_service.is_round_vote_completed.assert_called_once_with(event.game_id, QUEST_NUMBER, ROUND_NUMBER)
    round_service.set_round_result.assert_not_called()
    round_service.is_proposal_passed.assert_not_called()


def test_round_voting_state_when_proposal_passed(mocker, team_selection_state, quest_voting_state, round_service,
                                                 quest_service, event):
    # Given
    round_voting_state = RoundVotingState(team_selection_state, quest_voting_state, round_service, quest_service)
    round_service.is_round_vote_completed.return_value = True
    round_service.is_proposal_passed.return_value = True
    game_round = mocker.MagicMock(spec=Round)
    team_member_ids = ["team_member_id_1", "team_member_id_2"]
    game_round.result = VoteResult.Approved
    game_round.team_member_ids = team_member_ids
    round_service.set_round_result.return_value = game_round

    # When
    next_state = round_voting_state.handle(event)

    # Then
    assert round_voting_state.name == StateName.RoundVoting
    assert next_state == quest_voting_state
    round_service.handle_round_vote_cast.assert_called_once_with(event)
    round_service.is_round_vote_completed.assert_called_once_with(event.game_id, QUEST_NUMBER, ROUND_NUMBER)
    round_service.is_proposal_passed.assert_called_once_with(event.game_id, QUEST_NUMBER, ROUND_NUMBER)
    round_service.set_round_result.assert_called_once_with(event.game_id, QUEST_NUMBER, ROUND_NUMBER,
                                                           VoteResult.Approved)
    quest_service.set_team_member_ids.assert_called_once_with(event.game_id, QUEST_NUMBER, team_member_ids)


def test_round_voting_state_when_proposal_rejected(mocker, team_selection_state, quest_voting_state, round_service,
                                                   quest_service, event):
    # Given
    round_voting_state = RoundVotingState(team_selection_state, quest_voting_state, round_service, quest_service)
    round_service.is_round_vote_completed.return_value = True
    round_service.is_proposal_passed.return_value = False
    game_round = mocker.MagicMock(spec=Round)
    game_round.result = VoteResult.Rejected
    round_service.set_round_result.return_value = game_round

    # When
    next_state = round_voting_state.handle(event)

    # Then
    assert round_voting_state.name == StateName.RoundVoting
    assert next_state == team_selection_state
    round_service.handle_round_vote_cast.assert_called_once_with(event)
    round_service.is_round_vote_completed.assert_called_once_with(event.game_id, QUEST_NUMBER, ROUND_NUMBER)
    round_service.is_proposal_passed.assert_called_once_with(event.game_id, QUEST_NUMBER, ROUND_NUMBER)
    round_service.set_round_result.assert_called_once_with(event.game_id, QUEST_NUMBER, ROUND_NUMBER,
                                                           VoteResult.Rejected)


def test_round_voting_state_with_invalid_event_type(team_selection_state, quest_voting_state, round_service,
                                                    quest_service):
    # Given
    round_voting_state = RoundVotingState(team_selection_state, quest_voting_state, round_service, quest_service)
    invalid_event = Event(id="event_id", game_id="game_id", type=EventType.QuestStarted, recipients=[], payload={}, timestamp=123)

    # When
    with pytest.raises(ValueError):
        round_voting_state.handle(invalid_event)

    # Then
    assert round_voting_state.name == StateName.RoundVoting
    round_service.handle_round_vote_cast.assert_not_called()
    round_service.is_round_vote_completed.assert_not_called()
    round_service.is_proposal_passed.assert_not_called()


def test_round_voting_state_on_enter(team_selection_state, quest_voting_state, round_service, quest_service):
    # Given
    state = RoundVotingState(team_selection_state, quest_voting_state, round_service, quest_service)
    game_id = "game_id"

    # When
    state.on_enter(game_id)

    # Then
    round_service.on_enter_round_voting_state.assert_called_once_with(game_id)
