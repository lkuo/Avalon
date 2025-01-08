from unittest.mock import call

import pytest

from game_core.constants.action_type import ActionType
from game_core.constants.vote_result import VoteResult
from game_core.entities.action import Action
from game_core.entities.game import GameConfig
from game_core.entities.player import Player
from game_core.entities.round import Round
from game_core.entities.round_vote import RoundVote
from game_core.repository import Repository
from game_core.services.event_service import EventService
from game_core.services.round_service import RoundService

ACTION_ID = "action_id"
GAME_ID = "game_id"
LEADER_ID = "leader_id"
PLAYER_ID = "player_id"
QUEST_NUMBER = 3
ROUND_NUMBER = 4


@pytest.fixture
def repository(mocker):
    return mocker.MagicMock(spec=Repository)


@pytest.fixture
def event_service(mocker):
    return mocker.MagicMock(spec=EventService)


@pytest.fixture
def round_service(repository, event_service):
    return RoundService(event_service, repository)


@pytest.fixture
def cast_round_vote_action():
    return Action(
        ACTION_ID,
        GAME_ID,
        PLAYER_ID,
        ActionType.CastRoundVote,
        {
            "quest_number": QUEST_NUMBER,
            "round_number": ROUND_NUMBER,
            "player_id": PLAYER_ID,
            "is_approved": True,
        },
    )


@pytest.fixture
def submit_team_proposal_action():
    return Action(
        ACTION_ID,
        GAME_ID,
        PLAYER_ID,
        ActionType.SubmitTeamProposal,
        {
            "quest_number": QUEST_NUMBER,
            "round_number": ROUND_NUMBER,
            "player_ids": [PLAYER_ID],
        },
    )


def test_round_service_create_round(mocker, round_service, repository, event_service):
    # Given
    rounds = []
    for i in [3, 2, 1]:
        rnd = mocker.MagicMock(spec=Round)
        rnd.quest_number = QUEST_NUMBER
        rnd.round_number = i
        rounds.append(rnd)
    repository.get_rounds.return_value = rounds
    game = mocker.MagicMock()
    game_config = mocker.MagicMock(spec=GameConfig)
    number_of_players = 4
    game_config.quest_team_size = {QUEST_NUMBER: number_of_players}
    game.config = game_config
    player_ids = ["player_id1", "player_id2", LEADER_ID]
    game.player_ids = player_ids
    game.leader_id = LEADER_ID
    repository.get_game.return_value = game
    current_round = mocker.MagicMock()
    repository.put_round.return_value = current_round

    # When
    res = round_service.create_round(GAME_ID, QUEST_NUMBER)

    # Then
    repository.put_round.assert_called_once_with(
        GAME_ID, QUEST_NUMBER, ROUND_NUMBER, player_ids[0]
    )
    updated_game = game
    updated_game.leader_id = player_ids[0]
    repository.update_game.assert_called_once_with(updated_game)
    event_service.create_round_started_event.assert_called_once_with(
        GAME_ID, QUEST_NUMBER, ROUND_NUMBER, player_ids[0]
    )
    event_service.create_team_selection_requested_event.assert_called_once_with(
        GAME_ID, QUEST_NUMBER, ROUND_NUMBER, number_of_players
    )
    assert res == current_round


def test_handle_team_proposal_submitted(
    mocker, round_service, repository, event_service
):
    # Given
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
    game_round = mocker.MagicMock(spec=Round)
    repository.get_round.return_value = game_round
    action = Action(
        ACTION_ID,
        GAME_ID,
        team_member_ids[0],
        ActionType.SubmitTeamProposal,
        {
            "quest_number": quest_number,
            "round_number": round_number,
            "team_member_ids": team_member_ids,
        },
    )

    # When
    round_service.handle_submit_team_proposal(action)

    # Then
    event_service.create_team_proposal_submitted_event.assert_called_once_with(
        GAME_ID, quest_number, round_number, team_member_ids
    )
    game_round.team_member_ids = team_member_ids
    repository.update_round.assert_called_once_with(game_round)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"round_number": 4, "team_member_ids": []},
        {"quest_number": 3, "team_member_ids": []},
        {"quest_number": 3, "round_number": 4, "team_member_ids": ["player_id1"]},
        {
            "quest_number": 3,
            "round_number": 4,
            "team_member_ids": ["player_id1", "player_id3"],
        },
    ],
)
def test_handle_team_proposal_submitted_with_invalid_event(
    mocker, round_service, repository, payload
):
    # Given
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
    action = Action(
        ACTION_ID,
        GAME_ID,
        team_member_ids[0],
        ActionType.SubmitTeamProposal,
        payload,
    )

    # When
    with pytest.raises(ValueError):
        round_service.handle_submit_team_proposal(action)


def test_handle_round_vote_cast(
    mocker, round_service, event_service, submit_team_proposal_action, repository
):
    # Given
    quest_number = 3
    round_number = 4
    is_approved = True
    payload = {
        "quest_number": quest_number,
        "round_number": round_number,
        "player_id": PLAYER_ID,
        "is_approved": is_approved,
    }
    submit_team_proposal_action.payload = payload
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
    round_service.handle_cast_round_vote(submit_team_proposal_action)

    # Then
    repository.get_player.assert_called_once_with(PLAYER_ID)
    repository.get_quest.assert_called_once_with(GAME_ID, quest_number)
    repository.get_round.assert_has_calls([call(GAME_ID, quest_number, round_number)])
    repository.put_round_vote.assert_called_once_with(
        GAME_ID, quest_number, round_number, PLAYER_ID, VoteResult.Pass
    )
    repository.get_round_vote.assert_called_once_with(
        GAME_ID, quest_number, round_number, PLAYER_ID
    )
    updated_game_round = game_round
    updated_game_round.team_member_ids = [PLAYER_ID]
    repository.update_round.assert_called_once_with(updated_game_round)
    event_service.create_round_vote_cast_event.assert_called_once_with(
        GAME_ID, quest_number, round_number, PLAYER_ID, VoteResult.Pass
    )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"round_number": 4, "player_id": "player_id", "is_approved": True},
        {"quest_number": 3, "player_id": "player_id", "is_approved": True},
        {"quest_number": 3, "round_number": 4, "is_approved": True},
        {"quest_number": 3, "round_number": 4, "player_id": "player_id"},
        {
            "quest_number": 3,
            "round_number": 4,
            "player_id": "player_id",
            "is_approved": None,
        },
    ],
)
def test_handle_round_vote_cast_with_invalid_event(
    round_service, cast_round_vote_action, payload
):
    # Given
    cast_round_vote_action.payload = payload

    # When
    with pytest.raises(ValueError):
        round_service.handle_cast_round_vote(cast_round_vote_action)


def test_handle_round_vote_cast_with_player_voted(
    mocker, round_service, cast_round_vote_action, event_service, repository
):
    # Given
    quest_number = 3
    round_number = 4
    is_approved = True
    payload = {
        "quest_number": quest_number,
        "round_number": round_number,
        "player_id": PLAYER_ID,
        "is_approved": is_approved,
    }
    cast_round_vote_action.payload = payload
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
        round_service.handle_cast_round_vote(cast_round_vote_action)

    # Then
    repository.put_round_vote.assert_not_called()
    event_service.create_round_vote_cast_event.assert_not_called()


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
    repository.get_round_votes.assert_called_once_with(
        game_id, quest_number, round_number
    )


@pytest.mark.parametrize(
    "num_of_approval, is_passed", [(10, True), (6, True), (5, False), (4, False)]
)
def test_is_proposal_passed(
    mocker, round_service, repository, num_of_approval, is_passed
):
    # Given
    game_id = "game_id"
    quest_number = 3
    round_number = 4
    round_votes = []
    num_of_players = 10
    for i in range(num_of_players):
        vote = mocker.MagicMock(spec=RoundVote)
        vote.result = VoteResult.Fail
        round_votes.append(vote)
    for i in range(num_of_approval):
        round_votes[i].result = VoteResult.Pass
    repository.get_round_votes.return_value = round_votes

    # When
    res = round_service.is_proposal_passed(game_id, quest_number, round_number)

    # Then
    assert res == is_passed
    repository.get_round_votes.assert_called_once_with(
        game_id, quest_number, round_number
    )
