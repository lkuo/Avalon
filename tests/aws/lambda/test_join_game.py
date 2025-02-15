import json
from unittest.mock import ANY

import pytest

from game_core.constants.action_type import ActionType
from game_core.entities.action import Action
from game_core.state_machine import StateMachine
from aws.dynamodb_repository import DynamoDBRepository
from aws.lambdas.join_game import lambda_handler
from aws.websocket_comm_service import WebSocketCommService

GAME_ID = "game_id"
TABLE_NAME = "table_name"
AWS_REGION = "us-east-1"
WEBSOCKET_ENDPOINT = "wss://<API_ID>.execute-api.us-east-1.amazonaws.com/dev"
PLAYER_ID = "player_id"
PLAYER_NAME = "player_name"


@pytest.fixture(autouse=True)
def os_environ(mocker):
    mocker.patch.dict('os.environ', {'DYNAMODB_TABLE': TABLE_NAME, 'AWS_REGION': AWS_REGION,
                                     'WEBSOCKET_ENDPOINT': WEBSOCKET_ENDPOINT})


@pytest.fixture
def repository(mocker):
    return mocker.MagicMock(spec=DynamoDBRepository)


@pytest.fixture(autouse=True)
def dynamodb_repository_class(mocker, repository):
    mocker.patch('aws.lambdas.admin.create_game.DynamoDBRepository', return_value=repository)


@pytest.fixture
def comm_service(mocker):
    return mocker.MagicMock(spec=WebSocketCommService)


@pytest.fixture(autouse=True)
def websocket_comm_service_class(mocker, comm_service):
    mocker.patch('aws.lambdas.join_game.WebSocketCommService', return_value=comm_service)


@pytest.fixture
def state_machine(mocker):
    return mocker.MagicMock(spec=StateMachine)


@pytest.fixture(autouse=True)
def state_machine_class(mocker, state_machine):
    mocker.patch('aws.lambdas.join_game.StateMachine', return_value=state_machine)


@pytest.fixture
def event():
    body = {
        "name": PLAYER_NAME,
    }
    return {
        'body': json.dumps(body),
        'pathParameters':  {
            'game_id': GAME_ID
        }
    }


def test_lambda_handler(mocker, event, repository, comm_service, state_machine):
    # Given
    mocked_uuid = mocker.patch("aws.lambdas.join_game.uuid")
    mocked_uuid.uuid4.return_value.hex = PLAYER_ID

    # When
    res = lambda_handler(event, None)

    # Then
    assert res['body'] == json.dumps({
        'game_id': GAME_ID,
        'player_id': f"{GAME_ID}_player_{PLAYER_ID}",
        "websocket_endpoint": WEBSOCKET_ENDPOINT,
    })
    assert res['statusCode'] == 200
    state_machine.handle_action.assert_called_once_with(
        Action(
            id=ANY,
            game_id=GAME_ID,
            player_id=PLAYER_ID,
            type=ActionType.JoinGame,
            payload={
                "name": PLAYER_NAME,
            }
        )
    )
