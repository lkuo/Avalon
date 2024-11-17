from unittest.mock import call

import pytest

from game_core.constants.event_type import EventType
from game_core.entities.game import GameConfig
from game_core.entities.round import Round
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
    repository.put_event.has_call(call(game_id, EventType.ROUND_STARTED.value, [],
                                       {"quest_number": quest_number, "round_number": round_number,
                                        "leader_id": leader_id}, timestamp))
    comm_service.broadcast.assert_called_once_with(round_started_event)
    repository.put_event.has_call(call(game_id, EventType.SELECT_TEAM.value, [leader_id],
                                       {"quest_number": quest_number, "round_number": round_number,
                                        "number_of_players": number_of_players},
                                       timestamp))
    comm_service.notify.assert_called_once_with(leader_id, select_team_event)
    assert res == current_round
