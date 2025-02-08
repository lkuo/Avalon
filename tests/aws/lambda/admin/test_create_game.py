import json

import pytest

from aws.dynamodb_repository import DynamoDBRepository
from aws.lambdas.admin.create_game import lambda_handler
from game_core.constants.config import DEFAULT_QUEST_TEAM_SIZE, KNOWN_ROLES, DEFAULT_ASSASSINATION_ATTEMPTS, \
    DEFAULT_TEAM_SIZE_ROLES
from game_core.entities.game import GameConfig

GAME_ID = "game_id"
TABLE_NAME = "table_name"
AWS_REGION = "us-east-1"
TEAM_SIZE = 10


@pytest.fixture(autouse=True)
def os_environ(mocker):
    mocker.patch.dict('os.environ', {'DYNAMODB_TABLE': TABLE_NAME, 'AWS_REGION': AWS_REGION})


@pytest.fixture
def repository(mocker):
    return mocker.MagicMock(spec=DynamoDBRepository)


@pytest.fixture(autouse=True)
def dynamodb_repository_class(mocker, repository):
    mocker.patch('aws.lambdas.admin.create_game.DynamoDBRepository', return_value=repository)


@pytest.fixture
def event():
    return {
        'body': json.dumps({
            "team_size": TEAM_SIZE,
        })
    }


def test_handle_create_game(mocker, event, repository):
    # Given
    game = mocker.MagicMock()
    game.id = GAME_ID
    repository.put_game.return_value = game

    # When
    res = lambda_handler(event, None)

    # Then
    assert res['statusCode'] == 200, res['body']
    assert res['body'] == json.dumps({
        'game_id': GAME_ID
    })
    repository.put_game.assert_called_once_with()


def test_handle_create_game_error(event, repository):
    # Given
    repository.put_game.side_effect = Exception('error')

    # When
    res = lambda_handler(event, None)

    # Then
    assert res['statusCode'] == 500
    assert res['body'] == json.dumps({
        'error': 'error'
    })
