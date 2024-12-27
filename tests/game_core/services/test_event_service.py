import pytest
from unittest.mock import call

from game_core.constants.role import Role
from game_core.entities.player import Player
from game_core.repository import Repository
from game_core.services.event_service import EventService
from game_core.constants.event_type import EventType
from game_core.constants.vote_result import VoteResult
from game_core.entities.event import Event

TIMESTAMP = "123456"
GAME_ID = "test_game"
PLAYER_ID = "test_player"
PLAYER_NAME = "Test Player"
LEADER_ID = "leader_player"
TARGET_ID = "target_player"
QUEST_NUMBER = 1
ROUND_NUMBER = 2
TEAM_SIZE = 3


@pytest.fixture(autouse=True)
def mock_datetime(mocker):
    mock_datetime = mocker.patch("game_core.services.event_service.datetime")
    mock_datetime.now.return_value.isoformat.return_value = TIMESTAMP
    yield


@pytest.fixture
def comm_service(mocker):
    return mocker.MagicMock()


@pytest.fixture
def repository(mocker, created_event):
    mock_repository = mocker.MagicMock(spec=Repository)
    mock_repository.put_event.return_value = created_event
    return mock_repository


@pytest.fixture
def created_event(mocker):
    return mocker.MagicMock(spec=Event)


@pytest.fixture
def event_service(comm_service, repository):
    return EventService(comm_service, repository)


def test_create_player_joined_event(
    event_service, repository, comm_service, created_event
):
    # Given
    expected_payload = {"player_id": PLAYER_ID, "player_name": PLAYER_NAME}

    # When
    event_service.create_player_joined_event(PLAYER_ID, GAME_ID, PLAYER_NAME)

    # Then
    repository.put_event.assert_called_once_with(
        GAME_ID, EventType.PlayerJoined.value, [], expected_payload, TIMESTAMP
    )
    comm_service.broadcast.assert_called_once_with(created_event)


def test_create_game_started_events(
    mocker, event_service, repository, comm_service, created_event
):
    # Given
    player1 = Player(
        "p1", GAME_ID, "Player 1", "secret1", Role.Merlin, known_player_ids=["p2"]
    )
    player2 = Player(
        "p2", GAME_ID, "Player 2", "secret2", Role.Assassin, known_player_ids=["p1"]
    )
    players = [player1, player2]
    event1 = mocker.MagicMock(spec=Event)
    event2 = mocker.MagicMock(spec=Event)
    repository.put_event.side_effect = [event1, event2]

    # When
    event_service.create_game_started_events(GAME_ID, players)

    # Then
    calls = [
        call(
            GAME_ID,
            EventType.GameStarted.value,
            [player1.id],
            {
                "role": Role.Merlin.value,
                "known_players": [
                    {
                        "id": player2.id,
                        "name": player2.name,
                    }
                ],
            },
            TIMESTAMP,
        ),
        call(
            GAME_ID,
            EventType.GameStarted.value,
            [player2.id],
            {
                "role": Role.Assassin.value,
                "known_players": [
                    {
                        "id": player1.id,
                        "name": player1.name,
                    }
                ],
            },
            TIMESTAMP,
        ),
    ]
    repository.put_event.assert_has_calls(calls)
    comm_service.notify.assert_has_calls(
        [call(player1.id, event1), call(player2.id, event2)]
    )


def test_create_assassination_started_event(
    event_service, repository, comm_service, created_event
):
    # Given
    assassination_attempts = 1

    # When
    event_service.create_assassination_started_event(GAME_ID, assassination_attempts)

    # Then
    repository.put_event.assert_called_once_with(
        GAME_ID,
        EventType.AssassinationStarted.value,
        [],
        {"assassination_attempts": assassination_attempts},
        TIMESTAMP,
    )
    comm_service.broadcast.assert_called_once_with(created_event)


def test_create_round_started_event(
    event_service, repository, comm_service, created_event
):
    # Given

    # When
    event_service.create_round_started_event(
        GAME_ID, QUEST_NUMBER, ROUND_NUMBER, LEADER_ID
    )

    # Then
    repository.put_event.assert_called_once_with(
        GAME_ID,
        EventType.RoundStarted.value,
        [],
        {
            "quest_number": QUEST_NUMBER,
            "round_number": ROUND_NUMBER,
            "leader_id": LEADER_ID,
        },
        TIMESTAMP,
    )
    comm_service.broadcast.assert_called_once_with(created_event)


def test_create_quest_vote_cast_event(
    event_service, repository, comm_service, created_event
):
    # Given
    vote_result = VoteResult.Pass

    # When
    event_service.create_quest_vote_cast_event(
        GAME_ID, QUEST_NUMBER, PLAYER_ID, vote_result
    )

    # Then
    repository.put_event.assert_called_once_with(
        GAME_ID,
        EventType.QuestVoteCast.value,
        [],
        {
            "player_id": PLAYER_ID,
            "quest_number": QUEST_NUMBER,
            "result": vote_result.value,
        },
        TIMESTAMP,
    )
    comm_service.broadcast.assert_called_once_with(created_event)


def test_create_quest_started_event(
    event_service, repository, comm_service, created_event
):
    # Given
    # When
    event_service.create_quest_started_event(GAME_ID, QUEST_NUMBER)

    # Then
    repository.put_event.assert_called_once_with(
        GAME_ID,
        EventType.QuestStarted.value,
        [],
        {
            "quest_number": QUEST_NUMBER,
        },
        TIMESTAMP,
    )
    comm_service.broadcast.assert_called_once_with(created_event)


def test_create_team_selection_requested_event(
    event_service, repository, comm_service, created_event
):
    # Given
    # When
    event_service.create_team_selection_requested_event(
        GAME_ID, QUEST_NUMBER, ROUND_NUMBER, TEAM_SIZE
    )

    # Then
    repository.put_event.assert_called_once_with(
        GAME_ID,
        EventType.TeamSelectionRequested.value,
        [],
        {
            "quest_number": QUEST_NUMBER,
            "round_number": ROUND_NUMBER,
            "number_of_players": TEAM_SIZE,
        },
        TIMESTAMP,
    )
    comm_service.broadcast.assert_called_once_with(created_event)


def test_create_team_proposal_submitted_event(
    event_service, repository, comm_service, created_event
):
    # Given
    team_member_ids = ["player1", "player2"]

    # When
    event_service.create_team_proposal_submitted_event(
        GAME_ID, QUEST_NUMBER, ROUND_NUMBER, team_member_ids
    )

    # Then
    repository.put_event.assert_called_once_with(
        GAME_ID,
        EventType.TeamProposalSubmitted.value,
        [],
        {
            "quest_number": QUEST_NUMBER,
            "round_number": ROUND_NUMBER,
            "team_member_ids": team_member_ids,
        },
        TIMESTAMP,
    )
    comm_service.broadcast.assert_called_once_with(created_event)


def test_create_quest_vote_started_event(
    event_service, repository, comm_service, created_event
):
    # Given
    team_member_ids = ["player1", "player2"]

    # When
    event_service.create_quest_vote_started_event(
        GAME_ID, QUEST_NUMBER, team_member_ids
    )

    # Then
    repository.put_event.assert_called_once_with(
        GAME_ID,
        EventType.QuestVoteStarted.value,
        [],
        {"quest_number": QUEST_NUMBER, "team_member_ids": team_member_ids},
        TIMESTAMP,
    )
    comm_service.broadcast.assert_called_once_with(created_event)


def test_create_quest_vote_requested_event(
    event_service, repository, comm_service, created_event
):
    # Given
    team_member_ids = ["player1", "player2"]

    # When
    event_service.create_quest_vote_requested_event(
        GAME_ID, QUEST_NUMBER, team_member_ids
    )

    # Then
    repository.put_event.assert_called_once_with(
        GAME_ID,
        EventType.QuestVoteRequested.value,
        team_member_ids,
        {"quest_number": QUEST_NUMBER, "team_member_ids": team_member_ids},
        TIMESTAMP,
    )
    comm_service.notify.assert_has_calls(
        [
            call(team_member_ids[0], created_event),
            call(team_member_ids[1], created_event),
        ]
    )


def test_create_assassination_target_requested_event(
    event_service, repository, comm_service, created_event
):
    # Given
    assassin_id = "assassin1"

    # When
    event_service.create_assassination_target_requested_event(
        GAME_ID,
        assassin_id,
    )

    # Then
    repository.put_event.assert_called_once_with(
        GAME_ID,
        EventType.AssassinationTargetRequested.value,
        [assassin_id],
        {},
        TIMESTAMP,
    )
    comm_service.broadcast.assert_called_once_with(created_event)


def test_create_round_vote_cast_event(
    event_service, repository, comm_service, created_event
):
    # Given
    vote_result = VoteResult.Pass

    # When
    event_service.create_round_vote_cast_event(
        GAME_ID, QUEST_NUMBER, ROUND_NUMBER, PLAYER_ID, vote_result
    )

    # Then
    repository.put_event.assert_called_once_with(
        GAME_ID,
        EventType.RoundVoteCast.value,
        [],
        {
            "quest_number": QUEST_NUMBER,
            "round_number": ROUND_NUMBER,
            "player_id": PLAYER_ID,
            "result": vote_result.value,
        },
        TIMESTAMP,
    )
    comm_service.broadcast.assert_called_once_with(created_event)


def test_create_round_completed_event(
    event_service, repository, comm_service, created_event
):
    # Given
    vote_result = VoteResult.Pass

    # When
    event_service.create_round_completed_event(
        GAME_ID, QUEST_NUMBER, ROUND_NUMBER, vote_result
    )

    # Then
    repository.put_event.assert_called_once_with(
        GAME_ID,
        EventType.RoundCompleted.value,
        [],
        {
            "quest_number": QUEST_NUMBER,
            "round_number": ROUND_NUMBER,
            "result": vote_result.value,
        },
        TIMESTAMP,
    )
    comm_service.broadcast.assert_called_once_with(created_event)


def test_create_quest_completed_event(
    event_service, repository, comm_service, created_event
):
    # Given
    vote_result = VoteResult.Fail

    # When
    event_service.create_quest_completed_event(GAME_ID, QUEST_NUMBER, vote_result)

    # Then
    repository.put_event.assert_called_once_with(
        GAME_ID,
        EventType.QuestCompleted.value,
        [],
        {
            "quest_number": QUEST_NUMBER,
            "result": vote_result.value,
        },
        TIMESTAMP,
    )
    comm_service.broadcast.assert_called_once_with(created_event)


def test_create_assassination_event_success(
    event_service, repository, comm_service, created_event
):
    # Given
    is_successful = False

    # When
    event_service.create_assassination_event(GAME_ID, TARGET_ID, is_successful)

    # Then
    repository.put_event.assert_called_once_with(
        GAME_ID,
        EventType.AssassinationFailed.value,
        [],
        {"target_id": TARGET_ID, "is_successful": is_successful},
        TIMESTAMP,
    )
    comm_service.broadcast.assert_called_once_with(created_event)


def test_create_assassination_event_failure(
    event_service, repository, comm_service, created_event
):
    # Given
    is_successful = False

    # When
    event_service.create_assassination_event(GAME_ID, TARGET_ID, is_successful)

    # Then
    repository.put_event.assert_called_once_with(
        GAME_ID,
        EventType.AssassinationFailed.value,
        [],
        {"target_id": TARGET_ID, "is_successful": is_successful},
        TIMESTAMP,
    )
    comm_service.broadcast.assert_called_once_with(created_event)


def test_create_game_ended_event(
    event_service, repository, comm_service, created_event
):
    # Given
    player_roles = {
        "player1": Role.Merlin,
        "player2": Role.Assassin,
    }

    # When
    event_service.create_game_ended_event(GAME_ID, player_roles)

    # Then
    repository.put_event.assert_called_once_with(
        GAME_ID,
        EventType.GameEnded.value,
        [],
        {"player_roles": player_roles},
        TIMESTAMP,
    )
    comm_service.broadcast.assert_called_once_with(created_event)
