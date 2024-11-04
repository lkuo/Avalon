import pytest

from game_core.entities.event import Event
from game_core.event_type import EventType
from game_core.services.mission_service import MissionService
from game_core.states.game_end_state import GameEndState
from game_core.states.leader_assignment_state import LeaderAssignmentState
from game_core.states.quest_voting_state import QuestVotingState
from game_core.states.state import StateName


@pytest.fixture
def leader_assignment_state(mocker):
    return mocker.MagicMock(spec=LeaderAssignmentState)


@pytest.fixture
def game_end_state(mocker):
    return mocker.MagicMock(spec=GameEndState)


@pytest.fixture
def mission_service(mocker):
    return mocker.MagicMock(spec=MissionService)


@pytest.fixture
def event():
    payload = {
        "mission_number": 1,
        "player_id": "player_id",
        "vote": True
    }
    return Event(game_id="game_id", sk_id="sk_id", type=EventType.QUEST_VOTE_CASTED, recipient=[], payload=payload)


def test_quest_voting_state_when_mission_not_voted(leader_assignment_state, game_end_state, mission_service, event):
    # Given
    state = QuestVotingState(leader_assignment_state, game_end_state, mission_service)
    mission_service.is_mission_voted.return_value = False

    # When
    next_state = state.handle(event)

    # Then
    assert state.name == StateName.QUEST_VOTING
    assert next_state == state
    mission_service.save_mission_vote.assert_called_once_with(event.game_id,
                                                              event.payload["mission_number"],
                                                              event.payload["player_id"],
                                                              event.payload["vote"])
    mission_service.is_missions_completed.assert_not_called()


def test_quest_voting_state_when_missions_completed(leader_assignment_state, game_end_state, mission_service, event):
    # Given
    state = QuestVotingState(leader_assignment_state, game_end_state, mission_service)
    mission_service.is_mission_voted.return_value = True
    mission_service.is_missions_completed.return_value = True

    # When
    next_state = state.handle(event)

    # Then
    assert state.name == StateName.QUEST_VOTING
    assert next_state == game_end_state
    mission_service.save_mission_vote.assert_called_once_with(event.game_id,
                                                              event.payload["mission_number"],
                                                              event.payload["player_id"],
                                                              event.payload["vote"])
    mission_service.is_missions_completed.assert_called_once_with(event.game_id)


def test_quest_voting_state_when_missions_not_completed(leader_assignment_state, game_end_state, mission_service,
                                                        event):
    # Given
    state = QuestVotingState(leader_assignment_state, game_end_state, mission_service)
    mission_service.is_mission_voted.return_value = True
    mission_service.is_missions_completed.return_value = False

    # When
    next_state = state.handle(event)

    # Then
    assert state.name == StateName.QUEST_VOTING
    assert next_state == leader_assignment_state
    mission_service.save_mission_vote.assert_called_once_with(event.game_id,
                                                              event.payload["mission_number"],
                                                              event.payload["player_id"],
                                                              event.payload["vote"])
    mission_service.is_missions_completed.assert_called_once_with(event.game_id)


def test_quest_voting_state_with_invalid_event_type(leader_assignment_state, game_end_state, mission_service):
    # Given
    state = QuestVotingState(leader_assignment_state, game_end_state, mission_service)
    invalid_event = Event(game_id="game_id", sk_id="sk_id", type=EventType.QUEST_STARTED, recipient=[], payload={})

    # When
    with pytest.raises(ValueError):
        state.handle(invalid_event)

    # Then
    mission_service.save_mission_vote.assert_not_called()


@pytest.mark.parametrize("payload_key", ["mission_number", "player_id", "vote"])
def test_quest_voting_state_with_invalid_event_payload(leader_assignment_state, game_end_state, mission_service, event,
                                                       payload_key):
    # Given
    state = QuestVotingState(leader_assignment_state, game_end_state, mission_service)
    payload = event.payload
    payload.update({payload_key: None})
    invalid_event = Event(game_id="game_id", sk_id="sk_id", type=EventType.QUEST_STARTED, recipient=[], payload=payload)

    # When
    with pytest.raises(ValueError):
        state.handle(invalid_event)

    # Then
    mission_service.save_mission_vote.assert_not_called()


def test_quest_voting_state_on_enter(leader_assignment_state, game_end_state, mission_service):
    # Given
    state = QuestVotingState(leader_assignment_state, game_end_state, mission_service)
    game_id = "game_id"

    # When
    state.on_enter(game_id)

    # Then
    mission_service.broadcast_quest_vote_started.assert_called_once_with(game_id)
    mission_service.notify_cast_quest_vote.assert_called_once_with(game_id)


def test_quest_voting_state_on_exit(leader_assignment_state, game_end_state, mission_service):
    # Given
    state = QuestVotingState(leader_assignment_state, game_end_state, mission_service)
    game_id = "game_id"

    # When
    state.on_exit(game_id)

    # Then
    mission_service.broadcast_quest_vote_result.assert_called_once_with(game_id)
