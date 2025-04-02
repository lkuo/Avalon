import uuid
from collections import defaultdict, deque
from typing import Generator

import boto3
import docker
import pytest
from botocore.client import BaseClient
from botocore.exceptions import EndpointConnectionError, ClientError
from tenacity import retry, stop_after_attempt, wait_fixed

from aws.dynamodb_repository import DynamoDBRepository
from game_core.comm_service import CommService
from game_core.constants.action_type import ActionType
from game_core.constants.event_type import EventType
from game_core.constants.role import Role
from game_core.constants.vote_result import VoteResult
from game_core.entities.action import Action
from game_core.entities.event import Event
from game_core.state_machine import StateMachine

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
def dynamodb_repository(dynamodb_table):
    return DynamoDBRepository(
        TABLE_NAME, REGION, endpoint_url=f"http://localhost:{DYNAMODB_HOST_PORT}"
    )


class TestCommService(CommService):

    def __init__(self, repository: DynamoDBRepository):
        self.records = defaultdict(deque)
        self._repository = repository

    def broadcast(self, event: Event) -> None:
        connection_ids = self._repository.get_connection_ids(event.game_id)
        for cid in connection_ids:
            self.records[cid].append(event)

    def notify(self, player_id: str, event: Event) -> None:
        connection_id = self._repository.get_connection_id(event.game_id, player_id)
        self.records[connection_id].append(event)


@pytest.fixture
def comm_service(dynamodb_repository):
    return TestCommService(dynamodb_repository)


@pytest.fixture
def game(dynamodb_repository):
    game = dynamodb_repository.put_game()
    return game


@pytest.fixture
def players(dynamodb_repository, game):
    players = [dynamodb_repository.put_player(
        f"{game.id}_player_{uuid.uuid4().hex}",
        f"player_{i}",
        f"secret_{i}") for i in range(10)]
    for p in players:
        dynamodb_repository.put_connection_id(game.id, p.id, p.id)
    return players


def test_game_core(dynamodb_repository, comm_service, game, players):
    # Given
    sm = StateMachine(comm_service, dynamodb_repository, game.id)

    # Start Game
    start_game_action = Action(
        id=uuid.uuid4().hex,
        game_id=game.id,
        player_id=players[0].id,
        type=ActionType.StartGame,
        payload={"player_ids": [player.id for player in players]},
    )
    sm.handle_action(start_game_action)

    role_to_players = defaultdict(list)
    for player in players:
        event = comm_service.records[player.id].popleft()
        assert event.type == EventType.GameStarted, event
        role = Role(event.payload["role"])
        role_to_players[role].append(player.id)
        event = comm_service.records[player.id].popleft()
        assert event.type == EventType.QuestStarted, event
        assert event.payload["quest_number"] == 1
        event = comm_service.records[player.id].popleft()
        assert event.type == EventType.RoundStarted
        assert event.payload["round_number"] == 1

    assert len(role_to_players[Role.Merlin]) == 1
    assert len(role_to_players[Role.Percival]) == 1
    assert len(role_to_players[Role.Mordred]) == 1
    assert len(role_to_players[Role.Morgana]) == 1
    assert len(role_to_players[Role.Assassin]) == 1
    assert len(role_to_players[Role.Oberon]) == 1
    assert len(role_to_players[Role.Villager]) == 4

    event = comm_service.records[players[0].id].popleft()
    assert event.type == EventType.TeamSelectionRequested, event
    assert event.payload["number_of_players"] == 3
    assert event.payload["quest_number"] == 1
    assert event.payload["round_number"] == 1

    # Team Selection
    # Quest 1 Round 1
    sm = StateMachine(comm_service, dynamodb_repository, game.id)
    team_selection_action = Action(
        id=uuid.uuid4().hex,
        game_id=game.id,
        player_id=players[0].id,
        type=ActionType.SubmitTeamProposal,
        payload={
            "team_member_ids": [players[0].id, players[1].id, players[2].id],
        },
    )
    sm.handle_action(team_selection_action)
    for player in players:
        event = comm_service.records[player.id].popleft()
        assert event.type == EventType.TeamProposalSubmitted, event
        assert event.payload["team_member_ids"] == [players[0].id, players[1].id, players[2].id]

    # Round Voting
    for player in players[:7]:
        action = Action(
            id=uuid.uuid4().hex,
            game_id=game.id,
            player_id=player.id,
            type=ActionType.CastRoundVote,
            payload={
                "player_id": player.id,
                "is_approved": False
            },
        )
        sm = StateMachine(comm_service, dynamodb_repository, game.id)
        sm.handle_action(action)

    for p in players:
        for _p in players[:7]:
            event = comm_service.records[p.id].popleft()
            assert event.type == EventType.RoundVoteCast, event
            assert event.payload["player_id"] == _p.id
            assert event.payload["quest_number"] == 1
            assert event.payload["round_number"] == 1

    for player in players[7:]:
        action = Action(
            id=uuid.uuid4().hex,
            game_id=game.id,
            player_id=player.id,
            type=ActionType.CastRoundVote,
            payload={
                "player_id": player.id,
                "is_approved": True
            },
        )
        sm = StateMachine(comm_service, dynamodb_repository, game.id)
        sm.handle_action(action)

    for p in players:
        for _p in players[7:]:
            event = comm_service.records[p.id].popleft()
            assert event.type == EventType.RoundVoteCast, event
            assert event.payload["player_id"] == _p.id
            assert event.payload["quest_number"] == 1
            assert event.payload["round_number"] == 1

    player_votes = {p.id: VoteResult.Fail.value if i < 7 else VoteResult.Pass.value for i, p in enumerate(players)}
    for p in players:
        event = comm_service.records[p.id].popleft()
        assert event.type == EventType.RoundCompleted, event
        assert event.payload["quest_number"] == 1
        assert event.payload["round_number"] == 1
        assert event.payload["player_votes"] == player_votes
        event = comm_service.records[p.id].popleft()
        assert event.type == EventType.RoundStarted, event
    event = comm_service.records[players[1].id].popleft()
    assert event.type == EventType.TeamSelectionRequested, event

    action = Action(
        id=uuid.uuid4().hex,
        game_id=game.id,
        player_id=players[1].id,
        type=ActionType.SubmitTeamProposal,
        payload={
            "team_member_ids": [players[1].id, players[2].id, players[3].id],
        },
    )
    sm = StateMachine(comm_service, dynamodb_repository, game.id)
    sm.handle_action(action)
    for p in players:
        event = comm_service.records[p.id].popleft()
        assert event.type == EventType.TeamProposalSubmitted, event
        assert event.payload["team_member_ids"] == [players[1].id, players[2].id, players[3].id]
        action = Action(
            id=uuid.uuid4().hex,
            game_id=game.id,
            player_id=p.id,
            type=ActionType.CastRoundVote,
            payload={
                "player_id": p.id,
                "is_approved": True
            },
        )
        sm = StateMachine(comm_service, dynamodb_repository, game.id)
        sm.handle_action(action)
    for p in players:
        for _p in players:
            event = comm_service.records[p.id].popleft()
            assert event.type == EventType.RoundVoteCast, event
            assert event.payload["player_id"] == _p.id
            assert event.payload["quest_number"] == 1
            assert event.payload["round_number"] == 2
        event = comm_service.records[p.id].popleft()
        assert event.type == EventType.RoundCompleted, event
        event = comm_service.records[p.id].popleft()
        assert event.type == EventType.QuestVoteStarted, event
        assert event.payload["quest_number"] == 1

    for i in [1, 2, 3]:
        event = comm_service.records[players[i].id].popleft()
        assert event.type == EventType.QuestVoteRequested, event
        assert event.payload["quest_number"] == 1

    for i in [1, 2, 3]:
        action = Action(
            id=uuid.uuid4().hex,
            game_id=game.id,
            player_id=players[i].id,
            type=ActionType.CastQuestVote,
            payload={
                "player_id": players[i].id,
                "quest_number": 1,
                "is_approved": True
            },
        )
        sm = StateMachine(comm_service, dynamodb_repository, game.id)
        sm.handle_action(action)
    for p in players:
        for i in [1, 2, 3]:
            event = comm_service.records[p.id].popleft()
            assert event.type == EventType.QuestVoteCast, event
            assert event.payload["player_id"] == players[i].id
            assert event.payload["quest_number"] == 1
    for p in players:
        event = comm_service.records[p.id].popleft()
        assert event.type == EventType.QuestCompleted, event
        assert event.payload["quest_number"] == 1
        assert event.payload["result"] == VoteResult.Pass.value
        event = comm_service.records[p.id].popleft()
        assert event.type == EventType.QuestStarted, event
        event = comm_service.records[p.id].popleft()
        assert event.type == EventType.RoundStarted, event

    event = comm_service.records[players[2].id].popleft()
    assert event.type == EventType.TeamSelectionRequested, event
