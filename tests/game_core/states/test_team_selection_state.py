import pytest

from game_core.entities.event import Event
from game_core.constants.event_type import EventType
from game_core.services.quest_service import QuestService
from game_core.services.round_service import RoundService
from game_core.constants.state_name import StateName
from game_core.states.team_selection_state import TeamSelectionState


@pytest.fixture
def state(mocker):
    return mocker.MagicMock()


@pytest.fixture
def quest_service(mocker):
    return mocker.MagicMock(spec=QuestService)


@pytest.fixture
def round_service(mocker):
    return mocker.MagicMock(spec=RoundService)


def test_team_selection_state(state, quest_service, round_service):
    # Given
    team_selection_state = TeamSelectionState(state, quest_service, round_service)
    event = Event(id="game_id", type=EventType.TEAM_PROPOSAL_SUBMITTED, recipient=[], payload={})

    # When
    next_state = team_selection_state.handle(event)

    # Then
    assert team_selection_state.name == StateName.TEAM_SELECTION
    assert next_state == state
    round_service.handle_team_proposal_submitted.assert_called_once_with(event)


def test_team_selection_state_with_invalid_event(state, quest_service, round_service):
    # Given
    team_selection_state = TeamSelectionState(state, quest_service, round_service)
    invalid_event = Event(id="game_id", type=EventType.QUEST_STARTED, recipient=[], payload={})

    # When
    with pytest.raises(ValueError):
        team_selection_state.handle(invalid_event)

    # Then
    round_service.handle_team_proposal_submitted.assert_not_called()


def test_team_selection_state_on_enter(state, quest_service, round_service):
    # Given
    team_selection_state = TeamSelectionState(state, quest_service, round_service)
    game_id = "game_id"

    # When
    team_selection_state.on_enter(game_id)

    # Then
    quest_service.handle_on_enter_team_selection_state.assert_called_once_with(game_id)
