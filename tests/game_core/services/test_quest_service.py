from unittest.mock import ANY, call

import pytest

from game_core.constants.event_type import EventType
from game_core.constants.voting_result import VotingResult
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
    [Quest("quest_id1", 1, result=VotingResult.Passed), Quest("quest_id2", 2, result=VotingResult.Failed)], []])
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
    repository.put_event.assert_called_once_with(game_id, EventType.QUEST_STARTED.value, [],
                                                 {"game_id": game_id, "quest_number": len(quests) + 1}, timestamp)
    comm_service.broadcast.assert_called_once_with(event)


def test_handle_on_enter_team_selection_state_no_create_quest(mocker, quest_service, repository, round_service,
                                                              comm_service):
    # Given
    game_id = "game_id"
    quests = [Quest("quest_id1", 1, result=VotingResult.Passed), Quest("quest_id2", 2)]
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
    quests = [Quest("quest_id1", 1, result=VotingResult.Passed), Quest("quest_id2", 2)]
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
    repository.put_event.assert_has_calls([call(game_id, EventType.QUEST_VOTING_STARTED.value, [],
                                                {"game_id": game_id, "quest_number": quest_number,
                                                 "team_member_ids": team_member_ids}, timestamp),
                                           call(game_id, EventType.QUEST_VOTE_REQUESTED.value, team_member_ids, {},
                                                timestamp)])
    comm_service.broadcast.assert_has_calls(
        [call(quest_voting_started_event), call(quest_vote_requested_event, team_member_ids)])
