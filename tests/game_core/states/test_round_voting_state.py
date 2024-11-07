import pytest

from game_core.entities.event import Event
from game_core.event_type import EventType
from game_core.services.round_service import RoundService
from game_core.states.quest_voting_state import QuestVotingState
from game_core.states.round_voting_state import RoundVotingState
from game_core.states.state import StateName
from game_core.states.team_selection_state import TeamSelectionState


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
def event():
    return Event(game_id="game_id", sk_id="sk_id", type=EventType.ROUND_VOTE_CAST, recipient=[], payload={})


def test_round_voting_state_when_round_not_voted(team_selection_state, quest_voting_state, round_service, event):
    # Given
    round_voting_state = RoundVotingState(team_selection_state, quest_voting_state, round_service)
    round_service.is_round_vote_completed.return_value = False

    # When
    next_state = round_voting_state.handle(event)

    # Then
    assert round_voting_state.name == StateName.ROUND_VOTING
    assert next_state == round_voting_state
    round_service.handle_round_vote_cast.assert_called_once_with(event)
    round_service.is_round_vote_completed.assert_called_once_with(event.game_id)
    round_service.is_proposal_passed.assert_not_called()


def test_round_voting_state_when_proposal_passed(team_selection_state, quest_voting_state, round_service, event):
    # Given
    round_voting_state = RoundVotingState(team_selection_state, quest_voting_state, round_service)
    round_service.is_round_vote_completed.return_value = True
    round_service.is_proposal_passed.return_value = True

    # When
    next_state = round_voting_state.handle(event)

    # Then
    assert round_voting_state.name == StateName.ROUND_VOTING
    assert next_state == quest_voting_state
    round_service.handle_round_vote_cast.assert_called_once_with(event)
    round_service.is_round_vote_completed.assert_called_once_with(event.game_id)
    round_service.is_proposal_passed.assert_called_once_with(event.game_id)


def test_round_voting_state_when_proposal_rejected(team_selection_state, quest_voting_state, round_service, event):
    # Given
    round_voting_state = RoundVotingState(team_selection_state, quest_voting_state, round_service)
    round_service.is_round_vote_completed.return_value = True
    round_service.is_proposal_passed.return_value = False

    # When
    next_state = round_voting_state.handle(event)

    # Then
    assert round_voting_state.name == StateName.ROUND_VOTING
    assert next_state == team_selection_state
    round_service.handle_round_vote_cast.assert_called_once_with(event)
    round_service.is_round_vote_completed.assert_called_once_with(event.game_id)
    round_service.is_proposal_passed.assert_called_once_with(event.game_id)


def test_round_voting_state_with_invalid_event_type(team_selection_state, quest_voting_state, round_service):
    # Given
    round_voting_state = RoundVotingState(team_selection_state, quest_voting_state, round_service)
    invalid_event = Event(game_id="game_id", sk_id="sk_id", type=EventType.QUEST_STARTED, recipient=[], payload={})

    # When
    with pytest.raises(ValueError):
        round_voting_state.handle(invalid_event)

    # Then
    assert round_voting_state.name == StateName.ROUND_VOTING
    round_service.handle_round_vote_cast.assert_not_called()
    round_service.is_round_vote_completed.assert_not_called()
    round_service.is_proposal_passed.assert_not_called()


def test_round_voting_state_on_enter(team_selection_state, quest_voting_state, round_service):
    # Given
    state = RoundVotingState(team_selection_state, quest_voting_state, round_service)
    game_id = "game_id"

    # When
    state.on_enter(game_id)

    # Then
    round_service.on_enter_round_voting_state.assert_called_once_with(game_id)


def test_round_voting_state_on_exit(team_selection_state, quest_voting_state, round_service):
    # Given
    state = RoundVotingState(team_selection_state, quest_voting_state, round_service)
    game_id = "game_id"

    # When
    state.on_exit(game_id)

    # Then
    round_service.on_exit_round_voting_state.assert_called_once_with(game_id)
