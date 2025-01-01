import uuid
from typing import Generator

import boto3
import docker
import pytest
from botocore.client import BaseClient
from botocore.exceptions import EndpointConnectionError, ClientError
from tenacity import retry, stop_after_attempt, wait_fixed

from game_core.constants.event_type import EventType
from game_core.constants.game_status import GameStatus
from game_core.constants.role import Role
from game_core.constants.state_name import StateName
from lambdas.dynamodb_repository import DynamoDBRepository

DYNAMODB_HOST_PORT = "8000"
TABLE_NAME = "avalon_test"
REGION = "us-east-1"


@pytest.fixture(scope="session")
def dynamodb_table() -> Generator[BaseClient, None, None]:
    client = docker.from_env()
    container = client.containers.run(
        "amazon/dynamodb-local",
        ports={"8000/tcp": DYNAMODB_HOST_PORT},
        detach=True,
        remove=True,
    )

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(5))
    def get_dynamodb_client():
        dynamodb_client = boto3.client(
            "dynamodb",
            endpoint_url=f"http://localhost:{DYNAMODB_HOST_PORT}",
            region_name=REGION,
        )
        dynamodb_client.list_tables()
        return dynamodb_client

    try:
        get_dynamodb_client()
        dynamodb = boto3.resource(
            "dynamodb",
            region_name=REGION,
            endpoint_url=f"http://localhost:{DYNAMODB_HOST_PORT}",
        )
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        table.wait_until_exists()
        yield table
    except EndpointConnectionError as e:
        pytest.fail(f"DynamoDB is not connected: {e}")
    except ClientError as e:
        pytest.fail(f"Unable to create table {TABLE_NAME}: {e}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred: {e}")

    container.stop()


@pytest.fixture
def dynamodb_repository():
    return DynamoDBRepository(
        TABLE_NAME, REGION, endpoint_url=f"http://localhost:{DYNAMODB_HOST_PORT}"
    )


def test_get_game(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    status = GameStatus.NotStarted.value
    state = StateName.GameSetup.value
    config = {
        "quest_team_size": {1: 3, 2: 4, 3: 4, 4: 5, 5: 6},
        "max_round": 5,
        "roles": {
            Role.Merlin.value: [Role.Percival.value, Role.Morgana.value],
            Role.Assassin.value: [Role.Mordred.value],
            Role.Oberon.value: [Role.Mordred.value],
            Role.Morgana.value: [Role.Assassin.value],
            Role.Mordred.value: [Role.Morgana.value],
            Role.Percival.value: [Role.Merlin.value],
        },
        "assassination_attempts": 1,
    }
    player_ids = ["player_id1", "player_id2", "player_id3"]
    item = {
        "pk": game_id,
        "sk": "game",
        "status": status,
        "state": state,
        "config": {
            "quest_team_size": {
                str(k): str(v) for k, v in config["quest_team_size"].items()
            },
            "max_round": config["max_round"],
            "roles": {
                role: [role for role in roles]
                for role, roles in config["roles"].items()
            },
            "assassination_attempts": config["assassination_attempts"],
        },
        "player_ids": player_ids,
    }
    dynamodb_table.put_item(Item=item)

    # When
    game = dynamodb_repository.get_game(game_id)

    # Then
    assert game.id == game_id
    assert game.status == status
    assert game.state == state
    assert game.config.quest_team_size == config["quest_team_size"]
    assert game.config.max_round == config["max_round"]
    assert game.config.roles == config["roles"]
    assert game.config.assassination_attempts == config["assassination_attempts"]
    assert game.player_ids == player_ids


def test_put_event(mocker, dynamodb_repository, dynamodb_table):
    # Given
    event_id = "eventId"
    mock_uuid = mocker.patch("lambdas.dynamodb_repository.uuid")
    mock_uuid.uuid4.return_value.hex = event_id
    game_id = uuid.uuid4().hex
    event_type = EventType.GameStarted
    recipients = ["player_id1"]
    payload = {"key": "value", "key2": 2, "key3": [1, 2, 3], "key4": False}
    timestamp = "2021-09-01T00:00:00Z"

    # When
    event = dynamodb_repository.put_event(game_id, event_type, recipients, payload, timestamp)

    # Then
    res = dynamodb_table.get_item(
        TableName=TABLE_NAME,
        Key={"pk": game_id, "sk": f"event_{event_id}"},
    )
    actual_event = res["Item"]
    assert actual_event["sk"].split("_")[1] == event_id, actual_event["sk"]
    assert actual_event["pk"] == game_id
    assert actual_event["type"] == event_type.value
    assert actual_event["recipients"] == recipients
    assert actual_event["payload"] == payload
    assert actual_event["timestamp"] == timestamp
    assert event.id == event_id
    assert event.game_id == game_id
    assert event.type == event_type
    assert event.recipients == recipients
    assert event.payload == payload
    assert event.timestamp == timestamp

def test_get_player(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    player_id = uuid.uuid4().hex
    secret = uuid.uuid4().hex
    name = "玩家1"
    role = Role.Merlin
    item = {
        "pk": game_id,
        "sk": f"player_{player_id}",
        "name": name,
        "role": role.value,
        "secret": secret,
    }
    dynamodb_table.put_item(Item=item)

    # When
    player = dynamodb_repository.get_player(f"{game_id}_player_{player_id}")

    # Then
    assert player.game_id == game_id
    assert player.id == f"player_{player_id}"
    assert player.name == name
    assert player.role == role
    assert player.secret == secret
    assert player.known_player_ids == []
