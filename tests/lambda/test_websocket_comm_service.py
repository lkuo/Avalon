import json

import pytest

from game_core.constants.event_type import EventType
from game_core.entities.event import Event
from lambdas.websocket_comm_service import WebSocketCommService

ENDPOINT_URL = "https://mock_api_gateway_endpoint.com"
TIMESTAMP = "2021-01-01T00:00:00Z"


@pytest.fixture
def api_gateway(mocker):
    return mocker.Mock()


@pytest.fixture
def boto3(mocker, api_gateway):
    mocked_boto3 = mocker.patch("lambdas.websocket_comm_service.boto3")
    mocked_boto3.client.return_value = api_gateway
    return mocked_boto3


@pytest.fixture
def thread_pool_executor(mocker):
    return mocker.Mock()


@pytest.fixture
def thread_pool_executor_class(mocker, thread_pool_executor):
    mocked_thread_pool_executor_class = mocker.patch("lambdas.websocket_comm_service.ThreadPoolExecutor")
    mocked_thread_pool_executor_class.return_value = thread_pool_executor
    return mocked_thread_pool_executor_class


@pytest.fixture
def repository(mocker):
    return mocker.Mock()


@pytest.fixture
def websocket_comm_service(api_gateway, repository, boto3, thread_pool_executor_class):
    return WebSocketCommService(ENDPOINT_URL, repository)


def test_notify(websocket_comm_service, repository, api_gateway):
    # Given
    event = Event(
        id="event_id",
        game_id="game_id",
        type=EventType.PlayerJoined,
        recipients=[],
        payload={"key": "value"},
        timestamp=TIMESTAMP,
    )
    player_id = "player_id"
    repository.get_connection_id.return_value = "connection_id"

    # When
    websocket_comm_service.notify(player_id, event)

    # Then
    repository.get_connection_id.assert_called_once_with("game_id", "player_id")
    api_gateway.post_to_connection.assert_called_once_with(
        ConnectionId="connection_id",
        Data=json.dumps(event.to_dict())
    )


def test_broadcast(websocket_comm_service, repository, api_gateway, thread_pool_executor):
    # Given
    event = Event(
        id="event_id",
        game_id="game_id",
        type=EventType.PlayerJoined,
        recipients=[],
        payload={"key": "value"},
        timestamp=TIMESTAMP,
    )
    repository.get_connection_ids.return_value = ["connection_id_1", "connection_id_2"]

    # When
    websocket_comm_service.broadcast(event)

    # Then
    repository.get_connection_ids.assert_called_once_with("game_id")
    thread_pool_executor.submit.assert_any_call(websocket_comm_service._emit, "connection_id_1", event)
    thread_pool_executor.submit.assert_any_call(websocket_comm_service._emit, "connection_id_2", event)
    thread_pool_executor.shutdown.assert_called_once_with(wait=True)
