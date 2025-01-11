import pytest

from game_core.constants.action_type import ActionType
from game_core.constants.state_name import StateName
from game_core.entities.action import Action
from game_core.services.quest_service import QuestService
from game_core.states.end_game_state import EndGameState
from game_core.states.quest_voting_state import QuestVotingState
from game_core.states.team_selection_state import TeamSelectionState

QUEST_NUMBER = 3
ACTION_ID = "action_id"
GAME_ID = "game_id"
PLAYER_ID = "player_id"
CAST_QUEST_VOTE_PAYLOAD = {"quest_number": QUEST_NUMBER}


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
def cast_quest_vote_action():
    return Action(
        ACTION_ID,
        GAME_ID,
        PLAYER_ID,
        ActionType.CastQuestVote,
        CAST_QUEST_VOTE_PAYLOAD,
    )


@pytest.fixture
def quest_voting_state(team_selection_state, end_game_state, quest_service):
    quest_voting_state = QuestVotingState(quest_service)
    quest_voting_state.set_states(team_selection_state, end_game_state)
    return quest_voting_state


def test_quest_voting_state_when_quest_not_voted(
    quest_voting_state, quest_service, cast_quest_vote_action
):
    # Given
    quest_service.is_quest_vote_completed.return_value = False

    # When
    next_state = quest_voting_state.handle(cast_quest_vote_action)

    # Then
    assert quest_voting_state.name == StateName.QuestVoting
    assert next_state == quest_voting_state
    quest_service.handle_cast_quest_vote.assert_called_once_with(cast_quest_vote_action)
    quest_service.is_quest_vote_completed.assert_called_once_with(GAME_ID, QUEST_NUMBER)
    quest_service.has_majority.assert_not_called()


def test_quest_voting_state_when_quests_completed(
    quest_voting_state, end_game_state, quest_service, cast_quest_vote_action
):
    # Given
    quest_service.is_quest_vote_completed.return_value = True
    quest_service.has_majority.return_value = True

    # When
    next_state = quest_voting_state.handle(cast_quest_vote_action)

    # Then
    assert next_state == end_game_state
    quest_service.handle_cast_quest_vote.assert_called_once_with(cast_quest_vote_action)
    quest_service.is_quest_vote_completed.assert_called_once_with(GAME_ID, QUEST_NUMBER)
    quest_service.has_majority.assert_called_once_with(GAME_ID)


def test_quest_voting_state_when_quests_not_completed(
    quest_voting_state, team_selection_state, quest_service, cast_quest_vote_action
):
    # Given
    quest_service.is_quest_vote_completed.return_value = True
    quest_service.has_majority.return_value = False

    # When
    next_state = quest_voting_state.handle(cast_quest_vote_action)

    # Then
    assert next_state == team_selection_state
    quest_service.handle_cast_quest_vote.assert_called_once_with(cast_quest_vote_action)
    quest_service.has_majority.assert_called_once_with(GAME_ID)


def test_quest_voting_state_with_invalid_event_type(
    quest_voting_state, cast_quest_vote_action, quest_service
):
    # Given
    invalid_action = Action(
        ACTION_ID,
        GAME_ID,
        PLAYER_ID,
        ActionType.CastRoundVote,
        CAST_QUEST_VOTE_PAYLOAD,
    )

    # When
    with pytest.raises(ValueError):
        quest_voting_state.handle(invalid_action)

    # Then
    quest_service.handle_cast_quest_vote.assert_not_called()


def test_quest_voting_state_on_enter(quest_voting_state, quest_service):
    # Given
    # When
    quest_voting_state.on_enter(GAME_ID)

    # Then
    quest_service.on_enter_quest_voting_state.assert_called_once_with(GAME_ID)
