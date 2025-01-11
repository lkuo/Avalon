import pytest

from game_core.constants.action_type import ActionType
from game_core.constants.vote_result import VoteResult
from game_core.entities.action import Action
from game_core.entities.quest import Quest
from game_core.entities.quest_vote import QuestVote
from game_core.repository import Repository
from game_core.services.event_service import EventService
from game_core.services.player_service import PlayerService
from game_core.services.quest_service import QuestService
from game_core.services.round_service import RoundService

GAME_ID = "game_id"
ACTION_ID = "action_id"
PLAYER_ID = "player_id"
QUEST_NUMBER = 1
IS_APPROVED = True


@pytest.fixture
def repository(mocker):
    return mocker.MagicMock(spec=Repository)


@pytest.fixture
def round_service(mocker):
    return mocker.MagicMock(spec=RoundService)


@pytest.fixture
def player_service(mocker):
    return mocker.MagicMock(spec=PlayerService)


@pytest.fixture
def event_service(mocker):
    return mocker.MagicMock(spec=EventService)


@pytest.fixture
def quest_service(repository, round_service, player_service, event_service):
    return QuestService(round_service, event_service, player_service, repository)


@pytest.fixture
def cast_quest_vote_action():
    return Action(
        ACTION_ID,
        GAME_ID,
        PLAYER_ID,
        ActionType.CastQuestVote,
        {
            "player_id": PLAYER_ID,
            "quest_number": QUEST_NUMBER,
            "is_approved": IS_APPROVED,
        },
    )


@pytest.mark.parametrize(
    "quests",
    [
        [
            Quest("quest_id1", "game_id", 1, result=VoteResult.Pass),
            Quest("quest_id2", "game_id", 2, result=VoteResult.Fail),
        ],
        [],
    ],
)
def test_handle_on_enter_team_selection_state_create_quest(
    mocker, quest_service, repository, round_service, event_service, quests
):
    # Given
    repository.get_quests.return_value = quests
    current_quest = mocker.MagicMock()
    current_quest.quest_number = len(quests) + 1
    repository.put_quest.return_value = current_quest

    # When
    quest_service.handle_on_enter_team_selection_state(GAME_ID)

    # then
    repository.get_quests.assert_called_with(GAME_ID)
    repository.put_quest.assert_called_once_with(GAME_ID, current_quest.quest_number)
    round_service.create_round.assert_called_once_with(
        GAME_ID, current_quest.quest_number
    )
    event_service.create_quest_started_event.assert_called_once_with(
        GAME_ID, len(quests) + 1
    )


def test_handle_on_enter_team_selection_state_no_create_quest(
    quest_service, repository, round_service, event_service
):
    # Given
    quests = [
        Quest("quest_id1", "game_id", 1, result=VoteResult.Pass),
        Quest("quest_id2", "game_id", 2),
    ]
    repository.get_quests.return_value = quests

    # When
    quest_service.handle_on_enter_team_selection_state(GAME_ID)

    # then
    repository.get_quests.assert_called_with(GAME_ID)
    repository.put_quest.assert_not_called()
    round_service.create_round.assert_called_once_with(GAME_ID, quests[-1].quest_number)


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


def test_on_enter_quest_voting_state(
    mocker, event_service, quest_service, round_service, repository
):
    # Given
    team_member_ids = ["player_id1", "player_id2"]
    quests = [
        Quest("quest_id1", GAME_ID, 1, VoteResult.Pass),
        Quest("quest_id2", GAME_ID, 2),
    ]
    repository.get_quests.return_value = quests
    current_round = mocker.MagicMock()
    current_round.team_member_ids = team_member_ids
    round_service.get_current_round.return_value = current_round

    # When
    quest_service.on_enter_quest_voting_state(GAME_ID)

    # Then
    event_service.create_quest_vote_started_event.assert_called_once_with(
        GAME_ID, 2, team_member_ids
    )
    event_service.create_quest_vote_requested_event.assert_called_once_with(
        GAME_ID, 2, team_member_ids
    )


def test_handle_quest_vote_cast(
    mocker, quest_service, event_service, repository, cast_quest_vote_action
):
    # Given
    quest = mocker.MagicMock(spec=Quest)
    quest.result = None
    team_member_ids = ["player_id1", "player_id2"]
    repository.get_quest.return_value = quest
    quest_votes = []
    for _ in range(len(team_member_ids)):
        quest_vote = mocker.MagicMock()
        quest_vote.result = VoteResult.Pass
        quest_votes.append(quest_vote)
    repository.get_quest_votes.return_value = quest_votes

    # When
    quest_service.handle_cast_quest_vote(cast_quest_vote_action)

    # Then
    repository.put_quest_vote.assert_called_once_with(
        GAME_ID, QUEST_NUMBER, PLAYER_ID, IS_APPROVED
    )
    event_service.create_quest_vote_cast_event.assert_called_once_with(
        GAME_ID, QUEST_NUMBER, PLAYER_ID, VoteResult.Pass
    )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"quest_number": 1, "is_approved": True},
        {"player_id": "player_id", "is_approved": False},
        {"player_id": "player_id", "quest_number": 2},
    ],
)
def test_handle_quest_vote_cast_with_invalid_event(quest_service, repository, payload):
    # Given
    action = Action(ACTION_ID, GAME_ID, PLAYER_ID, ActionType.CastQuestVote, payload)

    # When
    with pytest.raises(ValueError):
        quest_service.handle_cast_quest_vote(action)

    # Then
    repository.put_quest_vote.assert_not_called()


def test_handle_quest_vote_cast_with_player_not_found(
    quest_service, player_service, cast_quest_vote_action, repository
):
    # Given
    player_service.get_player.side_effect = ValueError()

    # When
    with pytest.raises(ValueError):
        quest_service.handle_cast_quest_vote(cast_quest_vote_action)

    # Then
    repository.put_quest_vote.assert_not_called()


def test_handle_quest_vote_cast_with_quest_not_found(
    quest_service, player_service, cast_quest_vote_action, repository
):
    # Given
    repository.get_quest.side_effect = ValueError()

    # When
    with pytest.raises(ValueError):
        quest_service.handle_cast_quest_vote(cast_quest_vote_action)

    # Then
    repository.put_quest_vote.assert_not_called()


def test_handle_quest_vote_cast_with_player_voted(
    quest_service, player_service, cast_quest_vote_action, repository
):
    # Given
    repository.get_quest_votes.return_value = [QuestVote("id", GAME_ID, PLAYER_ID, QUEST_NUMBER, VoteResult.Fail)]

    # When
    with pytest.raises(ValueError):
        quest_service.handle_cast_quest_vote(cast_quest_vote_action)

    # Then
    repository.put_quest_vote.assert_not_called()


@pytest.mark.parametrize(
    "team_member_ids, quest_votes, is_completed",
    [(["id1", "id2"], [{}], False), (["id1", "id2"], [{}, {}], True)],
)
def test_is_quest_vote_completed(
    mocker, quest_service, repository, team_member_ids, quest_votes, is_completed
):
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


@pytest.mark.parametrize(
    "votes, quest_number, is_passed",
    [
        ([True, True], 2, True),
        ([True, False], 3, False),
        ([True, False], 4, True),
        ([False, False], 4, False),
    ],
)
def test_is_quest_passed(
    mocker, quest_service, repository, votes, quest_number, is_passed
):
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


def test_set_quest_result(mocker, quest_service, event_service, repository):
    # Given
    result = VoteResult.Pass
    quest = mocker.MagicMock(spec=Quest)
    quest.quest_number = QUEST_NUMBER
    expected_res = mocker.MagicMock(spec=Quest)
    repository.update_quest.return_value = expected_res

    # When
    res = quest_service.complete_quest(GAME_ID, quest, result)

    # Then
    updated_quest = quest
    updated_quest.result = result
    repository.update_quest.assert_called_once_with(updated_quest)
    assert res == expected_res
    event_service.create_quest_completed_event.assert_called_once_with(
        GAME_ID, quest.quest_number, result
    )


@pytest.mark.parametrize(
    "votes, result",
    [
        ([True, True, True], True),
        ([False, False, False], True),
        ([True, True, False, False], False),
    ],
)
def test_has_majority(mocker, quest_service, repository, votes, result):
    # Given
    game_id = "game_id"
    quests = []
    for vote in votes:
        quest = mocker.MagicMock(spec=Quest)
        quest.result = VoteResult.Pass if vote else VoteResult.Fail
        quests.append(quest)
    repository.get_quests.return_value = quests

    # When
    res = quest_service.has_majority(game_id)

    # Then
    assert res == result
