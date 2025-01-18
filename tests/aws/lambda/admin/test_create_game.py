import json

import pytest

from game_core.constants.role import Role
from aws.lambdas.admin.create_game import lambda_handler
from aws.dynamodb_repository import DynamoDBRepository

GAME_ID = "game_id"
TABLE_NAME = "table_name"
AWS_REGION = "us-east-1"
QUEST_TEAM_SIZE = {
    1: 3,
    2: 4,
    3: 4,
    4: 5,
    5: 5
}


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
    body = {
        "quest_team_size": QUEST_TEAM_SIZE,
        "roles": {
            Role.Merlin.value: [Role.Morgana.value, Role.Assassin.value, Role.Oberon.value],
            Role.Percival.value: [Role.Merlin.value, Role.Morgana.value],
            Role.Villager.value: [],
            Role.Mordred.value: [
                Role.Morgana.value,
                Role.Assassin.value,
                Role.Oberon.value,
            ],
            Role.Morgana.value: [
                Role.Mordred.value,
                Role.Assassin.value,
                Role.Oberon.value,
            ],
            Role.Assassin.value: [
                Role.Mordred.value,
                Role.Morgana.value,
                Role.Oberon.value,
            ],
            Role.Oberon.value: [],
        },
        "assassination_attempts": 1
    }
    return {
        'body': json.dumps(body)
    }


def test_handle_create_game(mocker, event, repository):
    # Given
    game = mocker.MagicMock()
    game.id = GAME_ID
    repository.put_game.return_value = game

    # When
    res = lambda_handler(event, None)

    # Then
    assert res['statusCode'] == 200
    assert res['body'] == json.dumps({
        'game_id': GAME_ID
    })
    event_body = json.loads(event['body'])
    repository.put_game.assert_called_once_with(
        QUEST_TEAM_SIZE,
        event_body['roles'],
        event_body['assassination_attempts']
    )


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
