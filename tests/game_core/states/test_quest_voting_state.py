import pytest

from game_core.entities.event import Event
from game_core.constants.event_type import EventType
from game_core.services.quest_service import QuestService
from game_core.states.end_game_state import EndGameState
from game_core.states.quest_voting_state import QuestVotingState
from game_core.constants.state_name import StateName
from game_core.states.team_selection_state import TeamSelectionState


@pytest.fixture
def team_selection_state(mocker):
    return mocker.MagicMock(spec=TeamSelectionState)


@pytest.fixture
def end_game_state(mocker):
    return mocker.MagicMock(spec=EndGameState)


@pytest.fixture
def quest_service(mocker):
    return mocker.MagicMock(spec=QuestService)


@pytest.fixture
def event():
    return Event(id="game_id", type=EventType.QUEST_VOTE_CAST, recipient=[], payload={})


def test_quest_voting_state_when_mission_not_voted(team_selection_state, end_game_state, quest_service, event):
    # Given
    state = QuestVotingState(team_selection_state, end_game_state, quest_service)
    quest_service.is_quest_vote_completed.return_value = False

    # When
    next_state = state.handle(event)

    # Then
    assert state.name == StateName.QUEST_VOTING
    assert next_state == state
    quest_service.handle_quest_vote_cast.assert_called_once_with(event)
    quest_service.has_won_majority.assert_not_called()


def test_quest_voting_state_when_missions_completed(team_selection_state, end_game_state, quest_service, event):
    # Given
    state = QuestVotingState(team_selection_state, end_game_state, quest_service)
    quest_service.is_quest_vote_completed.return_value = True
    quest_service.has_won_majority.return_value = True

    # When
    next_state = state.handle(event)

    # Then
    assert state.name == StateName.QUEST_VOTING
    assert next_state == end_game_state
    quest_service.handle_quest_vote_cast.assert_called_once_with(event)
    quest_service.has_won_majority.assert_called_once_with(event.id)


def test_quest_voting_state_when_missions_not_completed(team_selection_state, end_game_state, quest_service, event):
    # Given
    state = QuestVotingState(team_selection_state, end_game_state, quest_service)
    quest_service.is_quest_vote_completed.return_value = True
    quest_service.has_won_majority.return_value = False

    # When
    next_state = state.handle(event)

    # Then
    assert state.name == StateName.QUEST_VOTING
    assert next_state == team_selection_state
    quest_service.handle_quest_vote_cast.assert_called_once_with(event)
    quest_service.has_won_majority.assert_called_once_with(event.id)


def test_quest_voting_state_with_invalid_event_type(team_selection_state, end_game_state, quest_service):
    # Given
    state = QuestVotingState(team_selection_state, end_game_state, quest_service)
    invalid_event = Event(id="game_id", type=EventType.QUEST_STARTED, recipient=[], payload={})

    # When
    with pytest.raises(ValueError):
        state.handle(invalid_event)

    # Then
    quest_service.handle_quest_vote_cast.assert_not_called()


def test_quest_voting_state_on_enter(team_selection_state, end_game_state, quest_service):
    # Given
    state = QuestVotingState(team_selection_state, end_game_state, quest_service)
    game_id = "game_id"

    # When
    state.on_enter(game_id)

    # Then
    quest_service.on_enter_quest_voting_state.assert_called_once_with(game_id)


def test_quest_voting_state_on_exit(team_selection_state, end_game_state, quest_service):
    # Given
    state = QuestVotingState(team_selection_state, end_game_state, quest_service)
    game_id = "game_id"

    # When
    state.on_exit(game_id)

    # Then
    quest_service.on_exit_quest_voting_state.assert_called_once_with(game_id)
