import json

import pytest

from lambdas.dynamodb_repository import DynamoDBRepository
from lambdas.get_events import lambda_handler

GAME_ID = "game_id"
PLAYER_ID = "player_id"
PLAYER_SECRET = "player_secret"
TABLE_NAME = "table_name"
AWS_REGION = "us-east-1"


@pytest.fixture(autouse=True)
def os_environ(mocker):
    mocker.patch.dict('os.environ', {'DYNAMODB_TABLE': TABLE_NAME, 'AWS_REGION': AWS_REGION})


@pytest.fixture
def repository(mocker):
    return mocker.MagicMock(spec=DynamoDBRepository)


@pytest.fixture(autouse=True)
def dynamodb_repository_class(mocker, repository):
    mocker.patch('lambdas.get_events.DynamoDBRepository', return_value=repository)


@pytest.fixture
def event():
    return {
        "pathParameters": {
            "game_id": GAME_ID,
            "player_id": PLAYER_ID
        },
        "headers": {
            "player_secret": PLAYER_SECRET
        }
    }


def test_handle_get_events(mocker, event, repository):
    # Given
    player = mocker.MagicMock()
    player.secret = PLAYER_SECRET
    repository.get_player.return_value = player
    events = ["event1", "event2"]
    event1 = mocker.MagicMock()
    event1.to_dict.return_value = events[0]
    event2 = mocker.MagicMock()
    event2.to_dict.return_value = events[1]
    repository.get_events.return_value = [event1, event2]

    # When
    res = lambda_handler(event, None)

    # Then
    assert res["body"] == json.dumps(events)
    assert res["statusCode"] == 200
    repository.get_player.assert_called_with(PLAYER_ID)
    repository.get_events.assert_called_with(GAME_ID, PLAYER_ID)


def test_handle_get_events_with_error(mocker, event, repository):
    # Given
    error_message = "error message"
    repository.get_player.side_effect = Exception(error_message)

    # When
    res = lambda_handler(event, None)

    # Then
    assert res["statusCode"] == 500
    assert res["body"] == json.dumps({"error": error_message})
    repository.get_player.assert_called_with(PLAYER_ID)
    repository.get_events.assert_not_called()


def test_handle_get_events_with_missing_path_parameter(event, repository):
    # Given
    event["pathParameters"]["game_id"] = None

    # When
    res = lambda_handler(event, None)

    # Then
    assert res["statusCode"] == 400
    assert res["body"] == json.dumps({"error": "Missing required parameters"})
    repository.get_events.assert_not_called()
