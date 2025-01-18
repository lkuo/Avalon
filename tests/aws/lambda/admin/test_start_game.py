import json

import pytest

from aws.dynamodb_repository import DynamoDBRepository
from aws.lambdas.admin.start_game import lambda_handler

GAME_ID = "game_id"
TABLE_NAME = "table_name"
AWS_REGION = "us-east-1"
ASSASSINATION_ATTEMPTS = 2
PLAYER_IDS = ["player_id1", "player_id2"]


@pytest.fixture(autouse=True)
def os_environ(mocker):
    mocker.patch.dict("os.environ", {"DYNAMODB_TABLE": TABLE_NAME, "AWS_REGION": AWS_REGION})


@pytest.fixture
def repository(mocker):
    return mocker.MagicMock(spec=DynamoDBRepository)


@pytest.fixture(autouse=True)
def dynamodb_repository_class(mocker, repository):
    mocker.patch("aws.lambdas.admin.start_game.DynamoDBRepository", return_value=repository)


@pytest.fixture
def event():
    return {
        "pathParameters": {
            "game_id": GAME_ID
        },
        "body": json.dumps({
            "player_ids": PLAYER_IDS,
            "assassination_attempts": ASSASSINATION_ATTEMPTS,
        })
    }


def test_handle_start_game(mocker, event, repository):
    # Given
    game = mocker.MagicMock()
    game.id = GAME_ID
    repository.get_game.return_value = game

    # When
    res = lambda_handler(event, None)

    # Then
    assert res["statusCode"] == 200
    game.assassination_attempts = ASSASSINATION_ATTEMPTS
    game.player_ids = PLAYER_IDS
    repository.update_game.assert_called_once_with(game)


def test_handle_start_game_error(event, repository):
    # Given
    repository.get_game.side_effect = Exception("error")

    # When
    res = lambda_handler(event, None)

    # Then
    assert res["statusCode"] == 500
    assert res["body"] == json.dumps({
        "error": "error"
    })
