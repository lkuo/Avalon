import json

import pytest

from aws.dynamodb_repository import DynamoDBRepository
from aws.lambdas.admin.get_game import lambda_handler
from game_core.constants.config import KNOWN_ROLES, DEFAULT_QUEST_TEAM_SIZE, DEFAULT_TEAM_SIZE_ROLES

GAME_ID = "game_id"
TABLE_NAME = "table_name"
AWS_REGION = "us-east-1"
ASSASSINATION_ATTEMPTS = 2
PLAYER_IDS = ["player_id1", "player_id2"]
PLAYER_NAMES = ["player_name1", "player_name2"]


@pytest.fixture(autouse=True)
def os_environ(mocker):
    mocker.patch.dict("os.environ", {"DYNAMODB_TABLE": TABLE_NAME, "AWS_REGION": AWS_REGION})


@pytest.fixture
def repository(mocker):
    return mocker.MagicMock(spec=DynamoDBRepository)


@pytest.fixture(autouse=True)
def dynamodb_repository_class(mocker, repository):
    mocker.patch("aws.lambdas.admin.get_game.DynamoDBRepository", return_value=repository)


@pytest.fixture
def event():
    return {
        "pathParameters": {
            "game_id": GAME_ID
        }
    }


def test_handle_get_game(mocker, event, repository):
    # Given
    game = mocker.MagicMock()
    game.id = GAME_ID
    game.config.quest_team_size = DEFAULT_QUEST_TEAM_SIZE
    game.config.known_roles = KNOWN_ROLES
    game.config.roles = DEFAULT_TEAM_SIZE_ROLES
    game.config.assassination_attempts = ASSASSINATION_ATTEMPTS
    repository.get_game.return_value = game
    players = []
    for pid, pname in zip(PLAYER_IDS, PLAYER_NAMES):
        player = mocker.MagicMock()
        player.id = pid
        player.name = pname
        players.append(player)
    repository.get_players.return_value = players

    # When
    res = lambda_handler(event, None)

    # Then
    assert res["statusCode"] == 200, res["body"]
    body = json.loads(res["body"])
    assert body["id"] == GAME_ID
    assert body["roles"] == {str(k): v for k, v in DEFAULT_TEAM_SIZE_ROLES.items()}
    assert body["known_roles"] == KNOWN_ROLES
    assert {int(k): {int(_k): int(_v) for _k, _v in v.items()} for k, v in body["quest_team_size"].items()} == game.config.quest_team_size
    assert body["assassination_attempts"] == ASSASSINATION_ATTEMPTS
    assert body["players"] == [
        {
            "id": PLAYER_IDS[0],
            "name": PLAYER_NAMES[0]
        },
        {
            "id": PLAYER_IDS[1],
            "name": PLAYER_NAMES[1]
        }
    ]


def test_handle_start_get_error(event, repository):
    # Given
    repository.get_game.side_effect = Exception("error")

    # When
    res = lambda_handler(event, None)

    # Then
    assert res["statusCode"] == 500
    assert res["body"] == json.dumps({
        "error": "error"
    })
