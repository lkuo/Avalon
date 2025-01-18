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
from game_core.constants.vote_result import VoteResult
from aws.dynamodb_repository import DynamoDBRepository

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


def test_put_game(mocker, dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    mock_uuid = mocker.patch("aws.dynamodb_repository.uuid")
    mock_uuid.uuid4.return_value.hex = game_id
    quest_team_size = {
        1: 3,
        2: 4,
        3: 4,
        5: 5,
        6: 5,
    }
    roles = {
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
    }
    assassination_attempts = 1

    # When
    game = dynamodb_repository.put_game(quest_team_size, roles, assassination_attempts)

    # Then
    item = dynamodb_table.get_item(Key={"pk": game_id, "sk": "game"})["Item"]
    assert item["pk"] == game_id
    assert item["sk"] == "game"
    assert item["status"] == GameStatus.NotStarted.value
    assert item["state"] == StateName.GameSetup.value
    assert item["config"]["quest_team_size"] == {
        str(k): str(v) for k, v in quest_team_size.items()
    }
    assert item["config"]["roles"] == {
        role: [role for role in roles] for role, roles in roles.items()
    }
    assert item["config"]["assassination_attempts"] == assassination_attempts
    assert item["player_ids"] == []
    assert "assassination_attempts" not in item
    assert "result" not in item
    assert game.id == game_id
    assert game.status == GameStatus.NotStarted
    assert game.state == StateName.GameSetup
    assert game.config.quest_team_size == quest_team_size
    assert game.config.roles == roles
    assert game.config.assassination_attempts == assassination_attempts
    assert game.player_ids == []
    assert game.assassination_attempts is None
    assert game.result is None


def test_get_game(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    status = GameStatus.NotStarted
    state = StateName.GameSetup
    config = {
        "quest_team_size": {1: 3, 2: 4, 3: 4, 4: 5, 5: 6},
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
        "status": status.value,
        "state": state.value,
        "config": {
            "quest_team_size": {
                str(k): str(v) for k, v in config["quest_team_size"].items()
            },
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
    assert game.config.roles == config["roles"]
    assert game.config.assassination_attempts == config["assassination_attempts"]
    assert game.player_ids == player_ids


def test_update_game(dynamodb_repository, dynamodb_table):
    game_id = uuid.uuid4().hex
    status = GameStatus.NotStarted
    state = StateName.GameSetup
    config = {
        "quest_team_size": {1: 3, 2: 4, 3: 4, 4: 5, 5: 6},
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
        "status": status.value,
        "state": state.value,
        "config": {
            "quest_team_size": {
                str(k): str(v) for k, v in config["quest_team_size"].items()
            },
            "roles": {
                role: [role for role in roles]
                for role, roles in config["roles"].items()
            },
            "assassination_attempts": config["assassination_attempts"],
        },
        "player_ids": player_ids,
    }
    dynamodb_table.put_item(Item=item)
    game = dynamodb_repository.get_game(game_id)
    updated_status = GameStatus.InProgress
    updated_state = StateName.TeamSelection
    updated_assassin_attempts = 2
    game.status = updated_status
    game.state = updated_state
    game.config.assassination_attempts = updated_assassin_attempts

    # When
    dynamodb_repository.update_game(game)

    # Then
    game = dynamodb_repository.get_game(game_id)
    assert game.status == updated_status
    assert game.state == updated_state
    assert game.config.assassination_attempts == updated_assassin_attempts


def test_put_event(mocker, dynamodb_repository, dynamodb_table):
    # Given
    event_id = "eventId"
    mock_uuid = mocker.patch("aws.dynamodb_repository.uuid")
    mock_uuid.uuid4.return_value.hex = event_id
    game_id = uuid.uuid4().hex
    event_type = EventType.GameStarted
    recipients = ["player_id1"]
    payload = {"key": "value", "key2": 2, "key3": [1, 2, 3], "key4": False}
    timestamp = "2021-09-01T00:00:00Z"

    # When
    event = dynamodb_repository.put_event(
        game_id, event_type, recipients, payload, timestamp
    )

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


def test_get_events(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    player_id = "player_id1"
    item1 = {
        "pk": game_id,
        "sk": f"event_{uuid.uuid4().hex}",
        "type": EventType.GameStarted.value,
        "recipients": [player_id],
        "payload": {"key": "value", "key2": 2, "key3": [1, 2, 3], "key4": False},
        "timestamp": "2021-09-01T00:00:00Z",
    }
    dynamodb_table.put_item(Item=item1)
    item2 = {
        "pk": game_id,
        "sk": f"event_{uuid.uuid4().hex}",
        "type": EventType.GameStarted.value,
        "recipients": [],
        "payload": {},
        "timestamp": "2021-09-01T00:00:01Z",
    }
    dynamodb_table.put_item(Item=item2)
    item3 = {
        "pk": game_id,
        "sk": f"event_{uuid.uuid4().hex}",
        "type": EventType.GameStarted.value,
        "recipients": ["not_matched_player_id"],
        "payload": {},
        "timestamp": "2021-09-01T00:00:01Z",
    }
    dynamodb_table.put_item(Item=item3)

    # When
    events = dynamodb_repository.get_events(game_id, player_id)

    # Then
    events.sort(key=lambda x: x.timestamp)
    assert len(events) == 2
    assert events[0].id == f"{game_id}_{item1["sk"]}"
    assert events[0].game_id == game_id
    assert events[0].type == EventType(item1["type"])
    assert events[0].recipients == [player_id]
    assert events[0].payload == item1["payload"]
    assert events[0].timestamp == item1["timestamp"]
    assert events[1].id == f"{game_id}_{item2["sk"]}"
    assert events[1].game_id == game_id
    assert events[1].type == EventType(item2["type"])
    assert events[1].recipients == []
    assert events[1].payload == item2["payload"]
    assert events[1].timestamp == item2["timestamp"]


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
    assert player.id == f"{game_id}_player_{player_id}"
    assert player.name == name
    assert player.role == role
    assert player.secret == secret
    assert player.known_player_ids == []


def test_put_player(dynamodb_table, dynamodb_repository):
    # Given
    player_id = uuid.uuid4().hex
    game_id = uuid.uuid4().hex
    name = "player 2"
    secret = uuid.uuid4().hex

    # When
    player = dynamodb_repository.put_player(player_id, game_id, name, secret)

    # Then
    res = dynamodb_table.get_item(
        TableName=TABLE_NAME,
        Key={"pk": game_id, "sk": f"player_{player_id}"},
    )
    actual_player = res["Item"]
    assert actual_player["pk"] == game_id
    assert actual_player["sk"] == f"player_{player_id}"
    assert actual_player["name"] == name
    assert actual_player["secret"] == secret
    assert actual_player["role"] is None
    assert actual_player["known_player_ids"] == []
    assert player.id == f"{game_id}_player_{player_id}"
    assert player.game_id == game_id
    assert player.name == name
    assert player.secret == secret
    assert player.role is None
    assert player.known_player_ids == []


def test_update_player(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    player_id = uuid.uuid4().hex
    name = "player 2"
    secret = uuid.uuid4().hex
    item = {
        "pk": game_id,
        "sk": f"player_{player_id}",
        "name": name,
        "secret": secret,
        "role": None,
        "known_player_ids": None,
    }
    dynamodb_table.put_item(Item=item)
    updated_name = "player2"
    updated_role = Role.Percival
    updated_known_player_ids = ["player_id1", "player_id2"]
    player = dynamodb_repository.get_player(f"{game_id}_player_{player_id}")
    player.name = updated_name
    player.role = updated_role
    player.known_player_ids = updated_known_player_ids

    # When
    updated_player = dynamodb_repository.update_player(player)

    # Then
    res = dynamodb_table.get_item(
        TableName=TABLE_NAME,
        Key={"pk": game_id, "sk": f"player_{player_id}"},
    )
    assert res.get("Item") is not None
    assert updated_player.name == updated_name
    assert updated_player.role == updated_role
    assert updated_player.known_player_ids == updated_known_player_ids
    assert updated_player.secret == secret
    assert res["Item"]["name"] == updated_name, res["Item"]
    assert res["Item"]["role"] == updated_role.value
    assert res["Item"]["known_player_ids"] == updated_known_player_ids
    assert res["Item"]["secret"] == secret
    assert res["Item"]["pk"] == game_id
    assert res["Item"]["sk"] == f"player_{player_id}"


def test_get_players(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    player_ids = ["player_id1", "player_id2", "player_id3"]
    items = [
        {
            "pk": game_id,
            "sk": f"player_{player_id}",
            "name": f"player {i}",
            "secret": uuid.uuid4().hex,
            "role": Role.Merlin.value,
            "known_player_ids": [],
        }
        for i, player_id in enumerate(player_ids, 1)
    ]
    items.append(
        {
            "pk": game_id,
            "sk": "game",
        }
    )
    for item in items:
        dynamodb_table.put_item(Item=item)

    # When
    players = dynamodb_repository.get_players(game_id)

    # Then
    assert len(players) == 3
    for i, player in enumerate(players):
        assert player.id == f"{game_id}_player_{player_ids[i]}"
        assert player.game_id == game_id
        assert player.name == f"player {i + 1}"
        assert player.secret == items[i]["secret"]
        assert player.role == Role.Merlin
        assert player.known_player_ids == []


def test_put_quest(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    quest_number = 1

    # When
    quest = dynamodb_repository.put_quest(game_id, quest_number)

    # Then
    res = dynamodb_table.get_item(
        TableName=TABLE_NAME,
        Key={"pk": game_id, "sk": f"quest_{quest_number}"},
    )
    actual_quest = res["Item"]
    assert actual_quest["pk"] == game_id
    assert actual_quest["sk"] == f"quest_{quest_number}"
    assert int(actual_quest["quest_number"]) == quest_number
    assert actual_quest["result"] is None
    assert actual_quest["team_member_ids"] == []
    assert quest.id == f"{game_id}_quest_{quest_number}"
    assert quest.game_id == game_id
    assert quest.quest_number == quest_number
    assert quest.result is None
    assert quest.team_member_ids == []


def test_get_quests(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    quest_numbers = [1, 2, 3]
    items = [
        {
            "pk": game_id,
            "sk": f"quest_{quest_number}",
            "quest_number": quest_number,
            "result": None,
            "team_member_ids": [],
        }
        for quest_number in quest_numbers
    ]
    items[1]["result"] = VoteResult.Fail.value
    items.append(
        {
            "pk": game_id,
            "sk": "game",
        }
    )
    for item in items:
        dynamodb_table.put_item(Item=item)

    # When
    quests = dynamodb_repository.get_quests(game_id)
    quests.sort(key=lambda q: q.id)

    # Then
    assert len(quests) == 3
    for i, quest in enumerate(quests):
        assert quest.id == f"{game_id}_quest_{quest_numbers[i]}"
        assert quest.game_id == game_id
        assert quest.quest_number == quest_numbers[i]
        assert quest.result == (
            VoteResult(items[i]["result"]) if items[i]["result"] else None
        )
        assert quest.team_member_ids == []


def test_update_quest(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    quest_number = 1
    item = {
        "pk": game_id,
        "sk": f"quest_{quest_number}",
        "quest_number": quest_number,
        "result": None,
        "team_member_ids": [],
    }
    dynamodb_table.put_item(Item=item)
    updated_result = VoteResult.Pass
    updated_team_member_ids = ["player_id1", "player_id2"]
    quest = dynamodb_repository.get_quest(game_id, quest_number)
    quest.result = updated_result
    quest.team_member_ids = updated_team_member_ids

    # When
    updated_quest = dynamodb_repository.update_quest(quest)

    # Then
    res = dynamodb_table.get_item(Key={"pk": game_id, "sk": f"quest_{quest_number}"})
    assert res.get("Item") is not None
    assert updated_quest.id == f"{game_id}_quest_{quest_number}"
    assert updated_quest.game_id == game_id
    assert updated_quest.quest_number == quest_number
    assert updated_quest.result == updated_result
    assert updated_quest.team_member_ids == updated_team_member_ids
    assert res["Item"]["result"] == updated_result.value
    assert res["Item"]["team_member_ids"] == updated_team_member_ids
    assert res["Item"]["pk"] == game_id
    assert res["Item"]["sk"] == f"quest_{quest_number}"
    assert res["Item"]["quest_number"] == quest_number


def test_get_quest(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    quest_number = 4
    team_player_ids = ["player_id1", "player_id2"]
    item = {
        "pk": game_id,
        "sk": f"quest_{quest_number}",
        "quest_number": quest_number,
        "result": VoteResult.Pass.value,
        "team_member_ids": team_player_ids,
    }
    dynamodb_table.put_item(Item=item)

    # When
    quest = dynamodb_repository.get_quest(game_id, quest_number)

    # Then
    assert quest.id == f"{game_id}_quest_{quest_number}"
    assert quest.game_id == game_id
    assert quest.quest_number == quest_number
    assert quest.result == VoteResult.Pass
    assert quest.team_member_ids == team_player_ids


def test_put_quest_vote(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    quest_number = 1
    player_id = "player_id1"
    is_approved = True

    # When
    vote = dynamodb_repository.put_quest_vote(
        game_id, quest_number, player_id, is_approved
    )

    # Then
    res = dynamodb_table.get_item(
        TableName=TABLE_NAME,
        Key={"pk": game_id, "sk": f"vote_quest_{quest_number}_{player_id}"},
    )
    actual_vote = res["Item"]
    assert actual_vote["pk"] == game_id
    assert actual_vote["sk"] == f"vote_quest_{quest_number}_{player_id}"
    assert actual_vote["player_id"] == player_id
    assert actual_vote["quest_number"] == quest_number
    assert actual_vote["result"] == (
        VoteResult.Pass.value if is_approved else VoteResult.Fail.value
    )
    assert vote.id == f"{game_id}_vote_quest_{quest_number}_{player_id}"
    assert vote.game_id == game_id
    assert vote.quest_number == quest_number
    assert vote.player_id == player_id
    assert vote.result == (VoteResult.Pass if is_approved else VoteResult.Fail)


def test_get_quest_votes(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    quest_number = 1
    player_ids = ["player_id1", "player_id2", "player_id3"]
    items = [
        {
            "pk": game_id,
            "sk": f"vote_quest_{quest_number}_{player_id}",
            "player_id": player_id,
            "quest_number": quest_number,
            "result": (VoteResult.Pass.value if i % 2 == 0 else VoteResult.Fail.value),
        }
        for i, player_id in enumerate(player_ids)
    ]
    items.append(
        {
            "pk": game_id,
            "sk": "game",
        }
    )
    for item in items:
        dynamodb_table.put_item(Item=item)

    # When
    votes = dynamodb_repository.get_quest_votes(game_id, quest_number)

    # Then
    assert len(votes) == 3
    votes.sort(key=lambda v: v.id)
    for i, vote in enumerate(votes):
        assert vote.id == f"{game_id}_vote_quest_{quest_number}_{player_ids[i]}"
        assert vote.game_id == game_id
        assert vote.quest_number == quest_number
        assert vote.player_id == player_ids[i]
        assert vote.result == (VoteResult.Pass if i % 2 == 0 else VoteResult.Fail)


def test_get_rounds(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    quest_number = 2
    items = [
        {
            "pk": game_id,
            "sk": f"round_{quest_number}_{1}",
            "quest_number": quest_number,
            "round_number": 1,
            "leader_id": "player_id1",
            "team_member_ids": ["player_id1", "player_id2"],
            "result": VoteResult.Fail.value,
        },
        {
            "pk": game_id,
            "sk": f"round_{quest_number}_{2}",
            "quest_number": quest_number,
            "round_number": 2,
            "leader_id": "player_id3",
            "team_member_ids": ["player_id2", "player_id3"],
        },
    ]
    for item in items:
        dynamodb_table.put_item(Item=item)

    # When
    rounds = dynamodb_repository.get_rounds(game_id)

    # Then
    assert len(rounds) == 2
    rounds.sort(key=lambda r: r.id)
    assert rounds[0].id == f"{game_id}_round_{quest_number}_1"
    assert rounds[0].game_id == game_id
    assert rounds[0].quest_number == quest_number
    assert rounds[0].round_number == items[0]["round_number"]
    assert rounds[0].leader_id == items[0]["leader_id"]
    assert rounds[0].team_member_ids == items[0]["team_member_ids"]
    assert rounds[0].result == VoteResult.Fail
    assert rounds[1].id == f"{game_id}_round_{quest_number}_2"
    assert rounds[1].game_id == game_id
    assert rounds[1].quest_number == quest_number
    assert rounds[1].round_number == items[1]["round_number"]
    assert rounds[1].leader_id == items[1]["leader_id"]
    assert rounds[1].team_member_ids == items[1]["team_member_ids"]
    assert rounds[1].result is None


def test_put_round(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    quest_number = 2
    round_number = 3
    leader_id = "player_id1"

    # When
    game_round = dynamodb_repository.put_round(
        game_id, quest_number, round_number, leader_id
    )

    # Then
    res = dynamodb_table.get_item(
        TableName=TABLE_NAME,
        Key={"pk": game_id, "sk": f"round_{quest_number}_{round_number}"},
    )
    actual_round = res["Item"]
    assert actual_round["pk"] == game_id
    assert actual_round["sk"] == f"round_{quest_number}_{round_number}"
    assert actual_round["quest_number"] == quest_number
    assert actual_round["round_number"] == round_number
    assert actual_round["leader_id"] == leader_id
    assert actual_round["team_member_ids"] == []
    assert actual_round.get("result") is None
    assert game_round.id == f"{game_id}_round_{quest_number}_{round_number}"
    assert game_round.game_id == game_id
    assert game_round.quest_number == quest_number
    assert game_round.round_number == round_number
    assert game_round.leader_id == leader_id
    assert game_round.team_member_ids == []
    assert game_round.result is None


def test_get_round(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    quest_number = 2
    round_number = 3
    leader_id = "player_id1"
    team_member_ids = ["player_id1", "player_id2"]
    item = {
        "pk": game_id,
        "sk": f"round_{quest_number}_{round_number}",
        "quest_number": quest_number,
        "round_number": round_number,
        "leader_id": leader_id,
        "team_member_ids": team_member_ids,
    }
    dynamodb_table.put_item(Item=item)

    # When
    game_round = dynamodb_repository.get_round(game_id, quest_number, round_number)

    # Then
    assert game_round.id == f"{game_id}_round_{quest_number}_{round_number}"
    assert game_round.game_id == game_id
    assert game_round.quest_number == quest_number
    assert game_round.round_number == round_number
    assert game_round.leader_id == leader_id
    assert game_round.team_member_ids == team_member_ids
    assert game_round.result is None


def test_update_round(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    quest_number = 2
    round_number = 3
    item = {
        "pk": game_id,
        "sk": f"round_{quest_number}_{round_number}",
        "quest_number": quest_number,
        "round_number": round_number,
        "leader_id": None,
        "team_member_ids": [],
    }
    dynamodb_table.put_item(Item=item)
    updated_leader_id = "player_id2"
    updated_team_member_ids = ["player_id2", "player_id3"]
    updated_result = VoteResult.Fail
    game_round = dynamodb_repository.get_round(game_id, quest_number, round_number)
    game_round.leader_id = updated_leader_id
    game_round.team_member_ids = updated_team_member_ids
    game_round.result = updated_result

    # When
    updated_round = dynamodb_repository.update_round(game_round)

    # Then
    res = dynamodb_table.get_item(
        TableName=TABLE_NAME,
        Key={"pk": game_id, "sk": f"round_{quest_number}_{round_number}"},
    )
    assert res.get("Item") is not None
    assert updated_round.id == f"{game_id}_round_{quest_number}_{round_number}"
    assert updated_round.game_id == game_id
    assert updated_round.quest_number == quest_number
    assert updated_round.leader_id == updated_leader_id
    assert updated_round.team_member_ids == updated_team_member_ids
    assert updated_round.result == VoteResult.Fail
    assert res["Item"]["leader_id"] == updated_leader_id
    assert res["Item"]["team_member_ids"] == updated_team_member_ids
    assert res["Item"]["result"] == VoteResult.Fail.value
    assert res["Item"]["pk"] == game_id
    assert res["Item"]["sk"] == f"round_{quest_number}_{round_number}"


def test_get_round_votes(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    quest_number = 2
    round_number = 3
    player_ids = ["player_id1", "player_id2", "player_id3"]
    items = [
        {
            "pk": game_id,
            "sk": f"vote_round_{quest_number}_{round_number}_{player_id}",
            "quest_number": quest_number,
            "round_number": round_number,
            "player_id": player_id,
            "result": (VoteResult.Pass.value if i % 2 == 0 else VoteResult.Fail.value),
        }
        for i, player_id in enumerate(player_ids)
    ]
    items.append(
        {
            "pk": game_id,
            "sk": "game",
        }
    )
    for item in items:
        dynamodb_table.put_item(Item=item)

    # When
    votes = dynamodb_repository.get_round_votes(game_id, quest_number, round_number)

    # Then
    assert len(votes) == 3
    votes.sort(key=lambda v: v.id)
    for i, vote in enumerate(votes):
        assert (
            vote.id
            == f"{game_id}_vote_round_{quest_number}_{round_number}_{player_ids[i]}"
        )
        assert vote.game_id == game_id
        assert vote.quest_number == quest_number
        assert vote.round_number == round_number
        assert vote.player_id == player_ids[i]
        assert vote.result == (VoteResult.Pass if i % 2 == 0 else VoteResult.Fail)


def test_put_round_vote(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    quest_number = 2
    round_number = 3
    player_id = "player_id1"
    result = VoteResult.Fail

    # When
    vote = dynamodb_repository.put_round_vote(
        game_id, quest_number, round_number, player_id, result
    )

    # Then
    res = dynamodb_table.get_item(
        TableName=TABLE_NAME,
        Key={
            "pk": game_id,
            "sk": f"vote_round_{quest_number}_{round_number}_{player_id}",
        },
    )
    actual_vote = res["Item"]
    assert actual_vote["pk"] == game_id
    assert actual_vote["sk"] == f"vote_round_{quest_number}_{round_number}_{player_id}"
    assert actual_vote["player_id"] == player_id
    assert actual_vote["quest_number"] == quest_number
    assert actual_vote["round_number"] == round_number
    assert actual_vote["result"] == result.value
    assert vote.id == f"{game_id}_vote_round_{quest_number}_{round_number}_{player_id}"
    assert vote.game_id == game_id
    assert vote.quest_number == quest_number
    assert vote.round_number == round_number
    assert vote.player_id == player_id
    assert vote.result == result


def test_put_connection_id(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    player_id = "player_id1"
    connection_id = "connection_id1"

    # When
    dynamodb_repository.put_connection_id(game_id, player_id, connection_id)

    # Then
    res = dynamodb_table.get_item(
        TableName=TABLE_NAME,
        Key={"pk": game_id, "sk": f"connection_id_{player_id}"},
    )
    actual_connection = res["Item"]
    assert actual_connection["pk"] == game_id
    assert actual_connection["sk"] == f"connection_id_{player_id}"
    assert actual_connection["connection_id"] == connection_id


def test_get_connection_id(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    player_id = "player_id1"
    connection_id = "connection_id1"
    item = {
        "pk": game_id,
        "sk": f"connection_id_{player_id}",
        "connection_id": connection_id,
    }
    dynamodb_table.put_item(Item=item)
    dynamodb_table.put_item(Item={"pk": game_id, "sk": "game"})

    # When
    actual_connection_id = dynamodb_repository.get_connection_id(game_id, player_id)

    # Then
    assert actual_connection_id == connection_id


def test_get_connection_ids(dynamodb_repository, dynamodb_table):
    # Given
    game_id = uuid.uuid4().hex
    player_ids = ["player_id1", "player_id2", "player_id3"]
    connection_ids = ["connection_id1", "connection_id2", "connection_id3"]
    items = [
        {
            "pk": game_id,
            "sk": f"connection_id_{player_id}",
            "connection_id": connection_id,
        }
        for player_id, connection_id in zip(player_ids, connection_ids)
    ]
    items.append(
        {
            "pk": game_id,
            "sk": "game",
        }
    )
    for item in items:
        dynamodb_table.put_item(Item=item)

    # When
    actual_connection_ids = dynamodb_repository.get_connection_ids(game_id)

    # Then
    assert set(actual_connection_ids) == set(connection_ids)
