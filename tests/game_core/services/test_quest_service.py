from unittest.mock import ANY, call

import pytest

from game_core.constants.event_type import EventType
from game_core.constants.vote_result import VoteResult
from game_core.entities.event import Event
from game_core.entities.quest import Quest
from game_core.repository import Repository
from game_core.services.comm_service import CommService
from game_core.services.quest_service import QuestService
from game_core.services.round_service import RoundService


@pytest.fixture
def repository(mocker):
    return mocker.MagicMock(spec=Repository)


@pytest.fixture
def round_service(mocker):
    return mocker.MagicMock(spec=RoundService)


@pytest.fixture
def comm_service(mocker):
    return mocker.MagicMock(spec=CommService)


@pytest.fixture
def quest_service(repository, round_service, comm_service):
    return QuestService(repository, round_service, comm_service)


@pytest.mark.parametrize("quests", [
    [Quest("quest_id1", "game_id", 1, result=VoteResult.Approved),
     Quest("quest_id2", "game_id", 2, result=VoteResult.Rejected)], []])
def test_handle_on_enter_team_selection_state_create_quest(mocker, quest_service, repository, round_service,
                                                           comm_service, quests):
    # Given
    game_id = "game_id"
    repository.get_quests.return_value = quests
    player_ids = ["player_id1", "player_id2", "player_id3"]
    leader_id = player_ids[1]
    game = mocker.MagicMock()
    game.player_ids = player_ids
    game.leader_id = leader_id
    repository.get_game.return_value = game
    event = mocker.MagicMock()
    repository.put_event.return_value = event
    timestamp = 1234567890
    mock_datetime = mocker.patch("game_core.services.quest_service.datetime")
    mock_datetime.now.return_value.timestamp.return_value = timestamp
    current_quest = mocker.MagicMock()
    current_quest.quest_number = len(quests) + 1
    repository.put_quest.return_value = current_quest

    # When
    quest_service.handle_on_enter_team_selection_state(game_id)

    # then
    repository.get_quests.assert_called_with(game_id)
    repository.put_quest.assert_called_once_with(game_id, current_quest.quest_number)
    repository.get_game.assert_called_with(game_id)
    game.leader_id = player_ids[2]
    repository.put_game.assert_called_once_with(game)
    round_service.create_round.assert_called_once_with(game_id, player_ids[2], current_quest.quest_number)
    repository.put_event.assert_called_once_with(game_id, EventType.QuestStarted.value, [],
                                                 {"game_id": game_id, "quest_number": len(quests) + 1}, timestamp)
    comm_service.broadcast.assert_called_once_with(event)


def test_handle_on_enter_team_selection_state_no_create_quest(mocker, quest_service, repository, round_service,
                                                              comm_service):
    # Given
    game_id = "game_id"
    quests = [Quest("quest_id1", "game_id", 1, result=VoteResult.Approved), Quest("quest_id2", "game_id", 2)]
    repository.get_quests.return_value = quests
    player_ids = ["player_id1", "player_id2", "player_id3"]
    leader_id = player_ids[1]
    game = mocker.MagicMock()
    game.player_ids = player_ids
    game.leader_id = leader_id
    repository.get_game.return_value = game
    current_quest = mocker.MagicMock()
    current_quest.quest_number = len(quests)
    repository.put_quest.return_value = current_quest

    # When
    quest_service.handle_on_enter_team_selection_state(game_id)

    # then
    repository.get_quests.assert_called_with(game_id)
    repository.put_quest.assert_not_called()
    repository.get_game.assert_called_with(game_id)
    game.leader_id = player_ids[2]
    repository.put_game.assert_called_once_with(game)
    round_service.create_round.assert_called_once_with(game_id, player_ids[2], current_quest.quest_number)
    repository.put_event.assert_not_called()
    comm_service.broadcast.assert_not_called()


@pytest.mark.parametrize("current_leader_id, next_leader_id", [(0, 1), (1, 2), (2, 0)])
def test_handle_on_enter_team_selection_state_rotate_leader(mocker, quest_service, repository, round_service,
                                                            current_leader_id, next_leader_id):
    # Given
    game_id = "game_id"
    quests = [Quest("quest_id1", "game_id", 1, result=VoteResult.Approved), Quest("quest_id2", "game_id", 2)]
    repository.get_quests.return_value = quests
    player_ids = ["player_id1", "player_id2", "player_id3"]
    leader_id = player_ids[current_leader_id]
    game = mocker.MagicMock()
    game.player_ids = player_ids
    game.leader_id = leader_id
    repository.get_game.return_value = game

    # When
    quest_service.handle_on_enter_team_selection_state(game_id)

    # then
    round_service.create_round.assert_called_once_with(game_id, player_ids[next_leader_id], ANY)
    game.leader_id = player_ids[next_leader_id]
    repository.put_game.assert_called_once_with(game)


def test_set_team_member_ids(mocker, quest_service, repository):
    # Given
    game_id = "game_id"
    quest_number = 1
    team_member_ids = ["player_id1", "player_id2"]
    quest = mocker.MagicMock(spec=Quest)
    repository.get_quest.return_value = quest

    # When
    quest_service.set_team_member_ids(game_id, quest_number, team_member_ids)

    # then
    updated_quest = quest
    updated_quest.team_member_ids = team_member_ids
    repository.update_quest.assert_called_once_with(updated_quest)


def test_on_enter_quest_voting_state(mocker, quest_service, repository, comm_service):
    # Given
    game_id = "game_id"
    quest_number = 1
    team_member_ids = ["player_id1", "player_id2"]
    quest = mocker.MagicMock(spec=Quest)
    quest.quest_number = quest_number
    quest.team_member_ids = team_member_ids
    repository.get_quests.return_value = [quest]
    quest_voting_started_event = mocker.MagicMock()
    quest_vote_requested_event = mocker.MagicMock()
    repository.put_event.side_effect = [quest_voting_started_event, quest_vote_requested_event]
    timestamp = 1234567890
    mock_datetime = mocker.patch("game_core.services.quest_service.datetime")
    mock_datetime.now.return_value.timestamp.return_value = timestamp

    # When
    quest_service.on_enter_quest_voting_state(game_id)

    # then
    repository.put_event.assert_has_calls([call(game_id, EventType.QuestVoteStarted.value, [],
                                                {"game_id": game_id, "quest_number": quest_number,
                                                 "team_member_ids": team_member_ids}, timestamp),
                                           call(game_id, EventType.QuestVoteRequested.value, team_member_ids, {},
                                                timestamp)])
    comm_service.broadcast.assert_has_calls(
        [call(quest_voting_started_event), call(quest_vote_requested_event, team_member_ids)])


def test_handle_quest_vote_cast(mocker, quest_service, repository, comm_service):
    # Given
    game_id = "game_id"
    quest_number = 1
    player_id = "player_id"
    player = mocker.MagicMock()
    repository.get_player.return_value = player
    quest = mocker.MagicMock(spec=Quest)
    quest.result = None
    repository.get_quest.return_value = quest
    is_approved = True
    payload = {
        "player_id": player_id,
        "quest_number": quest_number,
        "is_approved": is_approved
    }
    timestamp = 1234567890
    mock_datetime = mocker.patch("game_core.services.quest_service.datetime")
    mock_datetime.now.return_value.timestamp.return_value = timestamp
    event = Event("event_id", game_id, EventType.QuestVoteCast.value, [], payload, timestamp)
    quest_vote_cast_event = mocker.MagicMock()
    repository.put_event.return_value = quest_vote_cast_event

    # When
    quest_service.handle_quest_vote_cast(event)

    # Then
    repository.put_quest_vote.assert_called_once_with(game_id, quest_number, player_id, is_approved)
    repository.put_event.assert_called_once_with(game_id, EventType.QuestVoteCast.value, [],
                                                 {"player_id": player_id, "quest_number": quest_number}, timestamp)
    comm_service.broadcast.assert_called_once_with(quest_vote_cast_event)


@pytest.mark.parametrize("payload", [None, {}, {"quest_number": 1, "is_approved": True},
                                     {"player_id": "player_id", "is_approved": False},
                                     {"player_id": "player_id", "quest_number": 2}])
def test_handle_quest_vote_cast_with_invalid_event(quest_service, repository, payload):
    # Given
    game_id = "game_id"
    event = Event("event_id", game_id, EventType.QuestVoteCast.value, [], payload, 0)

    # When
    with pytest.raises(ValueError):
        quest_service.handle_quest_vote_cast(event)

    # Then
    repository.put_quest_vote.assert_not_called()


def test_handle_quest_vote_cast_with_player_not_found(quest_service, repository):
    # Given
    game_id = "game_id"
    event = Event("event_id", game_id, EventType.QuestVoteCast.value, [],
                  {"player_id": "player_id", "quest_number": 1, "is_approved": False}, 0)
    repository.get_player.return_value = None

    # When
    with pytest.raises(ValueError):
        quest_service.handle_quest_vote_cast(event)

    # Then
    repository.put_quest_vote.assert_not_called()


def test_handle_quest_vote_cast_with_quest_not_found(mocker, quest_service, repository):
    # Given
    game_id = "game_id"
    event = Event("event_id", game_id, EventType.QuestVoteCast.value, [],
                  {"player_id": "player_id", "quest_number": 1, "is_approved": False}, 0)
    player = mocker.MagicMock()
    repository.get_player.return_value = player
    repository.get_quest.return_value = None

    # When
    with pytest.raises(ValueError):
        quest_service.handle_quest_vote_cast(event)

    # Then
    repository.put_quest_vote.assert_not_called()


def test_handle_quest_vote_cast_with_invalid_quest(mocker, quest_service, repository):
    # Given
    game_id = "game_id"
    event = Event("event_id", game_id, EventType.QuestVoteCast.value, [],
                  {"player_id": "player_id", "quest_number": 1, "is_approved": False}, 0)
    player = mocker.MagicMock()
    repository.get_player.return_value = player
    quest = mocker.MagicMock()
    quest.result = VoteResult.Approved
    repository.get_quest.return_value = quest

    # When
    with pytest.raises(ValueError):
        quest_service.handle_quest_vote_cast(event)

    # Then
    repository.put_quest_vote.assert_not_called()


@pytest.mark.parametrize("team_member_ids, quest_votes, is_completed",
                         [(["id1", "id2"], [{}], False), (["id1", "id2"], [{}, {}], True)])
def test_is_quest_vote_completed(mocker, quest_service, repository, team_member_ids, quest_votes, is_completed):
    # Given
    game_id = "game_id"
    quest_number = 1
    quest = mocker.MagicMock(spec=Quest)
    quest.team_member_ids = team_member_ids
    repository.get_quest.return_value = quest
    repository.get_quest_votes.return_value = quest_votes

    # When
    result = quest_service.is_quest_vote_completed(game_id, quest_number)

    # Then
    assert result == is_completed


@pytest.mark.parametrize("votes, quest_number, is_passed",
                         [([True, True], 2, True), ([True, False], 3, False), ([True, False], 4, True),
                          ([False, False], 4, False)])
def test_is_quest_passed(mocker, quest_service, repository, votes, quest_number, is_passed):
    # Given
    game_id = "game_id"
    quest_votes = []
    for vote in votes:
        quest_vote = mocker.MagicMock()
        quest_vote.result = vote
        quest_votes.append(quest_vote)
    repository.get_quest_votes.return_value = quest_votes

    # When
    result = quest_service.is_quest_passed(game_id, quest_number)

    # Then
    assert result == is_passed


def test_set_quest_result(mocker, quest_service, repository, comm_service):
    # Given
    game_id = "game_id"
    quest_number = 1
    result = VoteResult.Approved
    quest = mocker.MagicMock(spec=Quest)
    repository.get_quest.return_value = quest
    repository.update_quest.side_effect = lambda q: q
    event = mocker.MagicMock()
    repository.put_event.return_value = event
    timestamp = 1234567890
    mock_datetime = mocker.patch("game_core.services.quest_service.datetime")
    mock_datetime.now.return_value.timestamp.return_value = timestamp

    # When
    res = quest_service.set_quest_result(game_id, quest_number, result)

    # Then
    updated_quest = quest
    updated_quest.result = result
    repository.update_quest.assert_called_once_with(updated_quest)
    assert res == updated_quest
    repository.put_event.assert_called_once_with(game_id, EventType.QuestCompleted.value, [],
                                                 {"quest_number": quest_number, "result": result.value}, timestamp)
    comm_service.broadcast.assert_called_once_with(event)


@pytest.mark.parametrize("votes, result", [([True, True, True], True), ([False, False, False], True),
                                           ([True, True, False, False], False)])
def test_has_majority(mocker, quest_service, repository, votes, result):
    # Given
    game_id = "game_id"
    quests = []
    for vote in votes:
        quest = mocker.MagicMock(spec=Quest)
        quest.result = VoteResult.Approved if vote else VoteResult.Rejected
        quests.append(quest)
    repository.get_quests.return_value = quests

    # When
    res = quest_service.has_majority(game_id)

    # Then
    assert res == result
