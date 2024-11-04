import pytest

from game_core.entities.event import Event
from game_core.event_type import EventType
from game_core.services.round_service import RoundService
from game_core.states.leader_assignment_state import LeaderAssignmentState
from game_core.states.quest_voting_state import QuestVotingState
from game_core.states.round_voting_state import RoundVotingState
from game_core.states.state import StateName


@pytest.fixture
def leader_assignment_state(mocker):
    return mocker.MagicMock(spec=LeaderAssignmentState)


@pytest.fixture
def mission_voting_state(mocker):
    return mocker.MagicMock(spec=QuestVotingState)


@pytest.fixture
def round_service(mocker):
    return mocker.MagicMock(spec=RoundService)


@pytest.fixture
def event():
    payload = {
        "mission_number": 1,
        "round_number": 2,
        "player_id": "player_id",
        "vote": True
    }
    return Event(game_id="game_id", sk_id="sk_id", type=EventType.ROUND_VOTE_CASTED, recipient=[], payload=payload)


def test_round_voting_state_when_round_not_voted(leader_assignment_state, mission_voting_state, round_service, event):
    # Given
    round_voting_state = RoundVotingState(leader_assignment_state, mission_voting_state, round_service)
    round_service.is_round_voted.return_value = False

    # When
    next_state = round_voting_state.handle(event)

    # Then
    assert round_voting_state.name == StateName.ROUND_VOTING
    assert next_state == round_voting_state
    round_service.handle_vote.assert_called_once_with(event.game_id, event.payload["mission_number"],
                                                      event.payload["round_number"], event.payload["player_id"],
                                                      event.payload["vote"])
    round_service.is_round_voted.assert_called_once_with(event.game_id)
    round_service.is_proposal_passed.assert_not_called()


def test_round_voting_state_when_proposal_passed(leader_assignment_state, mission_voting_state, round_service, event):
    # Given
    round_voting_state = RoundVotingState(leader_assignment_state, mission_voting_state, round_service)
    round_service.is_round_voted.return_value = True
    round_service.is_proposal_passed.return_value = True

    # When
    next_state = round_voting_state.handle(event)

    # Then
    assert round_voting_state.name == StateName.ROUND_VOTING
    assert next_state == mission_voting_state
    round_service.handle_vote.assert_called_once_with(event.game_id, event.payload["mission_number"],
                                                      event.payload["round_number"], event.payload["player_id"],
                                                      event.payload["vote"])
    round_service.is_round_voted.assert_called_once_with(event.game_id)
    round_service.is_proposal_passed.assert_called_once_with(event.game_id)


def test_round_voting_state_when_proposal_rejected(leader_assignment_state, mission_voting_state, round_service, event):
    # Given
    round_voting_state = RoundVotingState(leader_assignment_state, mission_voting_state, round_service)
    round_service.is_round_voted.return_value = True
    round_service.is_proposal_passed.return_value = False

    # When
    next_state = round_voting_state.handle(event)

    # Then
    assert round_voting_state.name == StateName.ROUND_VOTING
    assert next_state == leader_assignment_state
    round_service.handle_vote.assert_called_once_with(event.game_id, event.payload["mission_number"],
                                                      event.payload["round_number"], event.payload["player_id"],
                                                      event.payload["vote"])
    round_service.is_round_voted.assert_called_once_with(event.game_id)
    round_service.is_proposal_passed.assert_called_once_with(event.game_id)


def test_round_voting_state_with_invalid_event_type(leader_assignment_state, mission_voting_state, round_service):
    # Given
    round_voting_state = RoundVotingState(leader_assignment_state, mission_voting_state, round_service)
    invalid_event = Event(game_id="game_id", sk_id="sk_id", type=EventType.QUEST_STARTED, recipient=[], payload={})

    # When
    with pytest.raises(ValueError):
        round_voting_state.handle(invalid_event)

    # Then
    assert round_voting_state.name == StateName.ROUND_VOTING
    round_service.handle_vote.assert_not_called()
    round_service.is_round_voted.assert_not_called()
    round_service.is_proposal_passed.assert_not_called()


@pytest.mark.parametrize("payload_key", ["mission_number", "round_number", "player_id", "vote"])
def test_round_voting_state_with_invalid_event_payload(leader_assignment_state, mission_voting_state, round_service,
                                                       event, payload_key):
    # Given
    round_voting_state = RoundVotingState(leader_assignment_state, mission_voting_state, round_service)
    payload = event.payload
    payload.update({payload_key: None})
    invalid_event = Event(game_id="game_id", sk_id="sk_id", type=EventType.QUEST_STARTED, recipient=[],
                          payload=payload)

    # When
    with pytest.raises(ValueError):
        round_voting_state.handle(invalid_event)

    # Then
    assert round_voting_state.name == StateName.ROUND_VOTING
    round_service.handle_vote.assert_not_called()
    round_service.is_round_voted.assert_not_called()
    round_service.is_proposal_passed.assert_not_called()
