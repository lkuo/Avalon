import pytest

from game_core.entities.event import Event
from game_core.event_type import EventType
from game_core.services.mission_service import QuestService
from game_core.states.end_game_state import EndGameState
from game_core.states.leader_assignment_state import LeaderAssignmentState
from game_core.states.quest_voting_state import QuestVotingState
from game_core.states.state import StateName


@pytest.fixture
def leader_assignment_state(mocker):
    return mocker.MagicMock(spec=LeaderAssignmentState)


@pytest.fixture
def end_game_state(mocker):
    return mocker.MagicMock(spec=EndGameState)


@pytest.fixture
def quest_service(mocker):
    return mocker.MagicMock(spec=QuestService)


@pytest.fixture
def event():
    return Event(game_id="game_id", sk_id="sk_id", type=EventType.QUEST_VOTE_CAST, recipient=[], payload={})


def test_quest_voting_state_when_mission_not_voted(leader_assignment_state, end_game_state, quest_service, event):
    # Given
    state = QuestVotingState(leader_assignment_state, end_game_state, quest_service)
    quest_service.is_quest_vote_completed.return_value = False

    # When
    next_state = state.handle(event)

    # Then
    assert state.name == StateName.QUEST_VOTING
    assert next_state == state
    quest_service.handle_quest_vote_cast.assert_called_once_with(event)
    quest_service.has_won_majority.assert_not_called()


def test_quest_voting_state_when_missions_completed(leader_assignment_state, end_game_state, quest_service, event):
    # Given
    state = QuestVotingState(leader_assignment_state, end_game_state, quest_service)
    quest_service.is_quest_vote_completed.return_value = True
    quest_service.has_won_majority.return_value = True

    # When
    next_state = state.handle(event)

    # Then
    assert state.name == StateName.QUEST_VOTING
    assert next_state == end_game_state
    quest_service.handle_quest_vote_cast.assert_called_once_with(event)
    quest_service.has_won_majority.assert_called_once_with(event.game_id)


def test_quest_voting_state_when_missions_not_completed(leader_assignment_state, end_game_state, quest_service, event):
    # Given
    state = QuestVotingState(leader_assignment_state, end_game_state, quest_service)
    quest_service.is_quest_vote_completed.return_value = True
    quest_service.has_won_majority.return_value = False

    # When
    next_state = state.handle(event)

    # Then
    assert state.name == StateName.QUEST_VOTING
    assert next_state == leader_assignment_state
    quest_service.handle_quest_vote_cast.assert_called_once_with(event)
    quest_service.has_won_majority.assert_called_once_with(event.game_id)


def test_quest_voting_state_with_invalid_event_type(leader_assignment_state, end_game_state, quest_service):
    # Given
    state = QuestVotingState(leader_assignment_state, end_game_state, quest_service)
    invalid_event = Event(game_id="game_id", sk_id="sk_id", type=EventType.QUEST_STARTED, recipient=[], payload={})

    # When
    with pytest.raises(ValueError):
        state.handle(invalid_event)

    # Then
    quest_service.handle_quest_vote_cast.assert_not_called()


def test_quest_voting_state_on_enter(leader_assignment_state, end_game_state, quest_service):
    # Given
    state = QuestVotingState(leader_assignment_state, end_game_state, quest_service)
    game_id = "game_id"

    # When
    state.on_enter(game_id)

    # Then
    quest_service.on_enter_quest_voting_state.assert_called_once_with(game_id)


def test_quest_voting_state_on_exit(leader_assignment_state, end_game_state, quest_service):
    # Given
    state = QuestVotingState(leader_assignment_state, end_game_state, quest_service)
    game_id = "game_id"

    # When
    state.on_exit(game_id)

    # Then
    quest_service.on_exit_quest_voting_state.assert_called_once_with(game_id)
