import json
from unittest.mock import ANY

import pytest

from aws.dynamodb_repository import DynamoDBRepository
from aws.lambdas.admin.start_game import lambda_handler
from aws.websocket_comm_service import WebSocketCommService
from game_core.constants.action_type import ActionType
from game_core.entities.action import Action
from game_core.state_machine import StateMachine

GAME_ID = "game_id"
TABLE_NAME = "table_name"
AWS_REGION = "us-east-1"
WEBSOCKET_ENDPOINT = "wss://<API_ID>.execute-api.us-east-1.amazonaws.com/dev"
ASSASSINATION_ATTEMPTS = 2
PLAYER_IDS = ["player_id1", "player_id2"]


@pytest.fixture(autouse=True)
def os_environ(mocker):
    mocker.patch.dict("os.environ", {"DYNAMODB_TABLE": TABLE_NAME, "AWS_REGION": AWS_REGION,
                                     'WEBSOCKET_ENDPOINT': WEBSOCKET_ENDPOINT})


@pytest.fixture
def repository(mocker):
    return mocker.MagicMock(spec=DynamoDBRepository)


@pytest.fixture(autouse=True)
def dynamodb_repository_class(mocker, repository):
    mocker.patch("aws.lambdas.admin.start_game.DynamoDBRepository", return_value=repository)


@pytest.fixture
def comm_service(mocker):
    return mocker.MagicMock(spec=WebSocketCommService)


@pytest.fixture(autouse=True)
def websocket_comm_service_class(mocker, comm_service):
    mocker.patch('aws.lambdas.admin.start_game.WebSocketCommService', return_value=comm_service)


@pytest.fixture
def state_machine(mocker):
    return mocker.MagicMock(spec=StateMachine)


@pytest.fixture(autouse=True)
def state_machine_class(mocker, state_machine):
    mocker.patch('aws.lambdas.admin.start_game.StateMachine', return_value=state_machine)


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


def test_handle_start_game(mocker, event, state_machine):
    # Given
    # When
    res = lambda_handler(event, None)

    # Then
    assert res["statusCode"] == 200
    state_machine.handle_action.assert_called_once_with(
        Action(
            id=ANY,
            game_id=GAME_ID,
            player_id="admin",
            type=ActionType.StartGame,
            payload={
                "game_id": GAME_ID,
                "player_ids": PLAYER_IDS,
                "assassination_attempts": ASSASSINATION_ATTEMPTS,
            }
        )
    )


def test_handle_start_game_error(event, state_machine):
    # Given
    state_machine.handle_action.side_effect = Exception("error")

    # When
    res = lambda_handler(event, None)

    # Then
    assert res["statusCode"] == 500
    assert res["body"] == json.dumps({
        "error": "error"
    })
