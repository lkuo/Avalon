import pytest

from aws.dynamodb_repository import DynamoDBRepository
from aws.lambdas.on_connect import lambda_handler

GAME_ID = "game_id"
TABLE_NAME = "table_name"
AWS_REGION = "us-east-1"
PLAYER_ID = "player_id"
CONNECTION_ID = "connection_id"


@pytest.fixture(autouse=True)
def os_environ(mocker):
    mocker.patch.dict('os.environ', {'DYNAMODB_TABLE': TABLE_NAME, 'AWS_REGION': AWS_REGION})


@pytest.fixture
def repository(mocker):
    return mocker.MagicMock(spec=DynamoDBRepository)


@pytest.fixture(autouse=True)
def dynamodb_repository_class(mocker, repository):
    mocker.patch('aws.lambdas.on_connect.DynamoDBRepository', return_value=repository)


@pytest.fixture
def event():
    return {
        'requestContext': {
            "connectionId":  CONNECTION_ID,
        },
        'queryStringParameters':  {
            'game_id': GAME_ID,
            'player_id': PLAYER_ID,
        }
    }


def test_lambda_handler(event, repository):
    # Given
    # When
    res = lambda_handler(event, None)

    # Then
    assert res['body'] == "Connected"
    assert res['statusCode'] == 200
    repository.put_connection_id.assert_called_once_with(GAME_ID, PLAYER_ID, CONNECTION_ID)
