import pytest

from game_core.entities.event import Event
from game_core.event_type import EventType
from game_core.services.mission_service import MissionService
from game_core.services.round_service import RoundService
from game_core.states.leader_assignment_state import LeaderAssignmentState
from game_core.states.state import StateName


@pytest.fixture
def state(mocker):
    return mocker.MagicMock()


@pytest.fixture
def mission_service(mocker):
    return mocker.MagicMock(spec=MissionService)


@pytest.fixture
def round_service(mocker):
    return mocker.MagicMock(spec=RoundService)


@pytest.mark.parametrize("event_type", [EventType.GAME_STARTED, EventType.QUEST_COMPLETED])
def test_leader_assignment_state_with_start_mission(state, mission_service, round_service, event_type):
    # Given
    leader_assignment_state = LeaderAssignmentState(state, mission_service, round_service)
    event = Event(game_id="game_id", sk_id="sk_id", type=event_type, recipient=[], payload={})

    # When
    next_state = leader_assignment_state.handle(event)

    # Then
    assert leader_assignment_state.name == StateName.LEADER_ASSIGNMENT
    assert next_state == state
    mission_service.start_mission.assert_called_once_with(event.game_id)
    round_service.start_round.assert_called_once_with(event.game_id)


def test_leader_assignment_state_without_start_mission(state, mission_service, round_service):
    # Given
    leader_assignment_state = LeaderAssignmentState(state, mission_service, round_service)
    event = Event(game_id="game_id", sk_id="sk_id", type=EventType.TEAM_REJECTED, recipient=[], payload={})

    # When
    next_state = leader_assignment_state.handle(event)

    # Then
    assert leader_assignment_state.name == StateName.LEADER_ASSIGNMENT
    assert next_state == state
    mission_service.start_mission.assert_not_called()
    round_service.start_round.assert_called_once_with(event.game_id)


def test_leader_assignment_state_invalid_event(state, mission_service, round_service):
    # Given
    leader_assignment_state = LeaderAssignmentState(state, mission_service, round_service)
    invalid_event = Event(game_id="game_id", sk_id="sk_id", type=EventType.QUEST_STARTED, recipient=[], payload={})

    # When
    with pytest.raises(ValueError):
        leader_assignment_state.handle(invalid_event)

    # Then
    mission_service.start_mission.assert_not_called()
    round_service.start_round.assert_not_called()
