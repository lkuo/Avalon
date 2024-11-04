import pytest

from game_core.entities.event import Event
from game_core.event_type import EventType
from game_core.services.round_service import RoundService
from game_core.states.state import StateName
from game_core.states.team_selection_state import TeamSelectionState


@pytest.fixture
def state(mocker):
    return mocker.MagicMock()


@pytest.fixture
def round_service(mocker):
    return mocker.MagicMock(spec=RoundService)


def test_team_selection_state(state, round_service):
    # Given
    team_selection_state = TeamSelectionState(state, round_service)
    event = Event(game_id="game_id", sk_id="sk_id", type=EventType.TEAM_PROPOSAL_SUBMITTED, recipient=[], payload={})

    # When
    next_state = team_selection_state.handle(event)

    # Then
    assert team_selection_state.name == StateName.TEAM_SELECTION
    assert next_state == state


def test_team_selection_state_with_invalid_event(state, round_service):
    # Given
    team_selection_state = TeamSelectionState(state, round_service)
    invalid_event = Event(game_id="game_id", sk_id="sk_id", type=EventType.QUEST_STARTED, recipient=[], payload={})

    # When
    with pytest.raises(ValueError):
        team_selection_state.handle(invalid_event)

    # Then
    round_service.broadcast_team_proposal.assert_not_called()


def test_team_selection_state_on_enter(state, round_service):
    # Given
    team_selection_state = TeamSelectionState(state, round_service)
    game_id = "game_id"

    # When
    team_selection_state.on_enter(game_id)

    # Then
    round_service.notify_submit_team_proposal.assert_called_once_with(game_id)
