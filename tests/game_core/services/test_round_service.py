from unittest.mock import call

import pytest

from game_core.constants.event_type import EventType
from game_core.constants.vote_result import VoteResult
from game_core.entities.event import Event
from game_core.entities.game import GameConfig
from game_core.entities.player import Player
from game_core.entities.round import Round
from game_core.entities.round_vote import RoundVote
from game_core.repository import Repository
from game_core.services.comm_service import CommService
from game_core.services.round_service import RoundService


@pytest.fixture
def repository(mocker):
    return mocker.MagicMock(spec=Repository)


@pytest.fixture
def comm_service(mocker):
    return mocker.MagicMock(spec=CommService)


@pytest.fixture
def round_service(repository, comm_service):
    return RoundService(repository, comm_service)


def test_round_service_create_round(mocker, round_service, repository, comm_service):
    # Given
    game_id = "game_id"
    leader_id = "leader_id"
    quest_number = 3
    rounds = []
    round_number = 4
    for i in [3, 2, 1]:
        rnd = mocker.MagicMock(spec=Round)
        rnd.round_number = i
        rounds.append(rnd)
    repository.get_rounds_by_quest.return_value = rounds
    timestamp = 1234567890
    mock_datetime = mocker.patch("game_core.services.round_service.datetime")
    mock_datetime.now.return_value.timestamp.return_value = timestamp
    round_started_event = mocker.MagicMock()
    select_team_event = mocker.MagicMock()
    repository.put_event.side_effect = [round_started_event, select_team_event]
    game = mocker.MagicMock()
    game_config = mocker.MagicMock(spec=GameConfig)
    number_of_players = 4
    game_config.quest_team_size = {quest_number: number_of_players}
    repository.get_game.return_value = game
    current_round = mocker.MagicMock()
    repository.put_round.return_value = current_round

    # When
    res = round_service.create_round(game_id, leader_id, quest_number)

    # Then
    repository.get_rounds_by_quest.assert_called_once_with(game_id, quest_number)
    repository.put_round.assert_called_once_with(game_id, quest_number, round_number, leader_id)
    repository.put_event.has_call(call(game_id, EventType.RoundStarted.value, [],
                                       {"quest_number": quest_number, "round_number": round_number,
                                        "leader_id": leader_id}, timestamp))
    comm_service.broadcast.assert_called_once_with(round_started_event)
    repository.put_event.has_call(call(game_id, EventType.SelectTeam.value, [leader_id],
                                       {"quest_number": quest_number, "round_number": round_number,
                                        "number_of_players": number_of_players},
                                       timestamp))
    comm_service.notify.assert_called_once_with(leader_id, select_team_event)
    assert res == current_round


def test_handle_team_proposal_submitted(mocker, round_service, repository, comm_service):
    # Given
    game_id = "game_id"
    quest_number = 3
    round_number = 4
    team_member_ids = ["player_id1", "player_id2"]
    quest_team_size = {quest_number: len(team_member_ids)}
    game = mocker.MagicMock()
    game_config = mocker.MagicMock(spec=GameConfig)
    game_config.quest_team_size = quest_team_size
    game.config = game_config
    repository.get_game.return_value = game
    players = []
    for player_id in team_member_ids:
        player = mocker.MagicMock()
        player.id = player_id
        players.append(player)
    repository.get_players.return_value = players
    timestamp = 1234567890
    mock_datetime = mocker.patch("game_core.services.round_service.datetime")
    mock_datetime.now.return_value.timestamp.return_value = timestamp
    event = Event(game_id, EventType.TeamProposalSubmitted.value, [],
                  {"quest_number": quest_number, "round_number": round_number, "team_member_ids": team_member_ids})
    saved_event = mocker.MagicMock()
    repository.put_event.return_value = saved_event
    repository.get_round_vote.return_value = None
    game_round = mocker.MagicMock(spec=Round)
    repository.get_round.return_value = game_round

    # When
    round_service.handle_team_proposal_submitted(event)

    # Then
    repository.get_game.assert_called_once_with(game_id)
    repository.get_players.assert_called_once_with(game_id)
    repository.put_event.assert_called_once_with(game_id, EventType.TeamProposalSubmitted.value, [],
                                                 {"quest_number": quest_number, "round_number": round_number,
                                                  "team_member_ids": team_member_ids}, timestamp)
    repository.get_round.assert_called_once_with(game_id, quest_number, round_number)
    game_round.team_member_ids = team_member_ids
    repository.update_round.assert_called_once_with(game_round)
    comm_service.broadcast.assert_called_once_with(saved_event)


@pytest.mark.parametrize("payload", [None, {}, {"round_number": 4, "team_member_ids": []},
                                     {"quest_number": 3, "team_member_ids": []},
                                     {"quest_number": 3, "round_number": 4, "team_member_ids": ["player_id1"]},
                                     {"quest_number": 3, "round_number": 4,
                                      "team_member_ids": ["player_id1", "player_id3"]}])
def test_handle_team_proposal_submitted_with_invalid_event(mocker, round_service, repository, comm_service, payload):
    # Given
    game_id = "game_id"
    quest_number = 3
    team_member_ids = ["player_id1", "player_id2"]
    quest_team_size = {quest_number: len(team_member_ids)}
    game = mocker.MagicMock()
    game_config = mocker.MagicMock(spec=GameConfig)
    game_config.quest_team_size = quest_team_size
    game.config = game_config
    repository.get_game.return_value = game
    players = []
    for player_id in team_member_ids:
        player = mocker.MagicMock()
        player.id = player_id
        players.append(player)
    repository.get_players.return_value = players
    event = Event(game_id, EventType.TeamProposalSubmitted.value, [], payload)

    # When
    with pytest.raises(ValueError):
        round_service.handle_team_proposal_submitted(event)


def test_handle_round_vote_cast(mocker, round_service, repository, comm_service):
    # Given
    game_id = "game_id"
    quest_number = 3
    round_number = 4
    player_id = "player_id"
    is_approved = True
    payload = {"quest_number": quest_number, "round_number": round_number, "player_id": player_id,
               "is_approved": is_approved}
    event = Event(game_id, EventType.RoundVoteCast.value, [], payload)
    player = mocker.MagicMock(spec=Player)
    repository.get_player.return_value = player
    quest = mocker.MagicMock()
    quest.quest_number = quest_number
    quest.result = None
    repository.get_quest.return_value = quest
    game_round = mocker.MagicMock(spec=Round)
    game_round.round_number = round_number
    game_round.result = None
    repository.get_round.return_value = game_round
    repository.get_round_vote.return_value = None

    # When
    round_service.handle_round_vote_cast(event)

    # Then
    repository.get_player.assert_called_once_with(game_id, player_id)
    repository.get_quest.assert_called_once_with(game_id, quest_number)
    repository.get_round.assert_called_once_with(game_id, quest_number, round_number)
    repository.put_round_vote.assert_called_once_with(game_id, quest_number, round_number, player_id, is_approved)
    repository.get_round_vote.assert_called_once_with(game_id, quest_number, round_number, player_id)
    round_vote_cast_event = Event(game_id, EventType.RoundVoteCast.value, [],
                                  {"player_id": player_id, "quest_number": quest_number, "round_number": round_number})
    comm_service.broadcast.assert_called_once_with(round_vote_cast_event)


@pytest.mark.parametrize("payload", [None, {},
                                     {"round_number": 4, "player_id": "player_id", "is_approved": True},
                                     {"quest_number": 3, "player_id": "player_id", "is_approved": True},
                                     {"quest_number": 3, "round_number": 4, "is_approved": True},
                                     {"quest_number": 3, "round_number": 4, "player_id": "player_id"},
                                     {"quest_number": 3, "round_number": 4, "player_id": "player_id",
                                      "is_approved": None}])
def test_handle_round_vote_cast_with_invalid_event(round_service, payload):
    # Given
    game_id = "game_id"
    event = Event(game_id, EventType.RoundVoteCast.value, [], payload)

    # When
    with pytest.raises(ValueError):
        round_service.handle_round_vote_cast(event)


def test_handle_round_vote_cast_with_player_voted(mocker, round_service, repository):
    # Given
    game_id = "game_id"
    quest_number = 3
    round_number = 4
    player_id = "player_id"
    is_approved = True
    payload = {"quest_number": quest_number, "round_number": round_number, "player_id": player_id,
               "is_approved": is_approved}
    event = Event(game_id, EventType.RoundVoteCast.value, [], payload)
    player = mocker.MagicMock(spec=Player)
    repository.get_player.return_value = player
    quest = mocker.MagicMock()
    quest.quest_number = quest_number
    quest.result = None
    repository.get_quest.return_value = quest
    game_round = mocker.MagicMock(spec=Round)
    game_round.round_number = round_number
    game_round.result = None
    repository.get_round.return_value = game_round
    repository.get_round_vote.return_value = mocker.MagicMock()

    # When
    with pytest.raises(ValueError):
        round_service.handle_round_vote_cast(event)

    # Then
    repository.get_player.assert_called_once_with(game_id, player_id)
    repository.get_quest.assert_called_once_with(game_id, quest_number)
    repository.get_round.assert_called_once_with(game_id, quest_number, round_number)
    repository.get_round_vote.assert_called_once_with(game_id, quest_number, round_number, player_id)


@pytest.mark.parametrize("num_of_votes, is_completed", [(10, True), (4, False)])
def test_is_round_vote_completed(round_service, repository, num_of_votes, is_completed):
    # Given
    game_id = "game_id"
    quest_number = 3
    round_number = 4
    num_of_players = 10
    players = [{}] * num_of_players
    round_votes = [{}] * num_of_votes
    repository.get_players.return_value = players
    repository.get_round_votes.return_value = round_votes

    # When
    res = round_service.is_round_vote_completed(game_id, quest_number, round_number)

    # Then
    assert res == is_completed
    repository.get_players.assert_called_once_with(game_id)
    repository.get_round_votes.assert_called_once_with(game_id, quest_number, round_number)


@pytest.mark.parametrize("num_of_approval, is_passed", [(10, True), (6, True), (5, False), (4, False)])
def test_is_proposal_passed(mocker, round_service, repository, num_of_approval, is_passed):
    # Given
    game_id = "game_id"
    quest_number = 3
    round_number = 4
    round_votes = []
    num_of_players = 10
    for i in range(num_of_players):
        vote = mocker.MagicMock(spec=RoundVote)
        vote.is_approved = False
        round_votes.append(vote)
    for i in range(num_of_approval):
        round_votes[i].is_approved = True
    repository.get_round_votes.return_value = round_votes

    # When
    res = round_service.is_proposal_passed(game_id, quest_number, round_number)

    # Then
    assert res == is_passed
    repository.get_round_votes.assert_called_once_with(game_id, quest_number, round_number)


def test_set_round_result(mocker, round_service, repository, comm_service):
    # Given
    game_id = "game_id"
    quest_number = 3
    round_number = 4
    result = VoteResult.Passed
    game_round = mocker.MagicMock(spec=Round)
    repository.get_round.return_value = game_round
    updated_game_round = mocker.MagicMock(spec=Round)
    updated_game_round.result = result
    repository.update_round.return_value = updated_game_round
    round_votes = []
    for i in range(10):
        vote = mocker.MagicMock(spec=RoundVote)
        vote.player_id = f"player_id_{i}"
        vote.is_approved = mocker.MagicMock()
        round_votes.append(vote)
    repository.get_round_votes.return_value = round_votes
    event = mocker.MagicMock(spec=Event)
    repository.put_event.return_value = event

    # When
    res = round_service.set_round_result(game_id, quest_number, round_number, result)

    # Then
    assert res == updated_game_round
    repository.get_round.assert_called_once_with(game_id, quest_number, round_number)
    repository.update_round.assert_called_once_with(game_round)
    votes = {rv.player_id: rv.is_approved for rv in round_votes}
    repository.put_event.assert_called_once_with(game_id, EventType.RoundCompleted.value, [],
                                                 {"quest_number": quest_number, "round_number": round_number,
                                                  "result": result.value, "votes": votes}, mocker.ANY)
    comm_service.broadcast.assert_called_once_with(event)
