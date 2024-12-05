import pytest

from game_core.constants.voting_result import VotingResult
from game_core.entities.event import Event
from game_core.constants.event_type import EventType
from game_core.services.quest_service import QuestService
from game_core.states.end_game_state import EndGameState
from game_core.states.quest_voting_state import QuestVotingState
from game_core.constants.state_name import StateName
from game_core.states.team_selection_state import TeamSelectionState

QUEST_NUMBER = 3


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
    return Event(game_id="game_id", type=EventType.QuestVoteCast, recipients=[],
                 payload={"quest_number": QUEST_NUMBER})


def test_quest_voting_state_when_quest_not_voted(team_selection_state, end_game_state, quest_service, event):
    # Given
    state = QuestVotingState(team_selection_state, end_game_state, quest_service)
    quest_service.is_quest_vote_completed.return_value = False

    # When
    next_state = state.handle(event)

    # Then
    assert state.name == StateName.QuestVoting
    assert next_state == state
    quest_service.handle_quest_vote_cast.assert_called_once_with(event)
    quest_service.has_majority.assert_not_called()


@pytest.mark.parametrize("is_quest_passed, voting_result", [(True, VotingResult.Passed), (False, VotingResult.Failed)])
def test_quest_voting_state_when_quests_completed(team_selection_state, end_game_state, quest_service, event,
                                                  is_quest_passed, voting_result):
    # Given
    state = QuestVotingState(team_selection_state, end_game_state, quest_service)
    quest_service.is_quest_vote_completed.return_value = True
    quest_service.is_quest_passed.return_value = is_quest_passed
    quest_service.has_majority.return_value = True

    # When
    next_state = state.handle(event)

    # Then
    assert state.name == StateName.QuestVoting
    assert next_state == end_game_state
    quest_service.handle_quest_vote_cast.assert_called_once_with(event)
    quest_service.set_quest_result.assert_called_once_with(event.game_id, QUEST_NUMBER, voting_result)
    quest_service.has_majority.assert_called_once_with(event.game_id)


def test_quest_voting_state_when_quests_not_completed(team_selection_state, end_game_state, quest_service, event):
    # Given
    state = QuestVotingState(team_selection_state, end_game_state, quest_service)
    quest_service.is_quest_vote_completed.return_value = True
    quest_service.has_majority.return_value = False

    # When
    next_state = state.handle(event)

    # Then
    assert state.name == StateName.QuestVoting
    assert next_state == team_selection_state
    quest_service.handle_quest_vote_cast.assert_called_once_with(event)
    quest_service.has_majority.assert_called_once_with(event.game_id)


def test_quest_voting_state_with_invalid_event_type(team_selection_state, end_game_state, quest_service):
    # Given
    state = QuestVotingState(team_selection_state, end_game_state, quest_service)
    invalid_event = Event(game_id="game_id", type=EventType.QuestStarted, recipients=[], payload={})

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
