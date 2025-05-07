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
    def sm():
        return StateMachine(comm_service, dynamodb_repository, game.id)
    game.assassination_attempts = 1
    dynamodb_repository.update_game(game)

    # Start Game
    start_game_action = Action(
        id=uuid.uuid4().hex,
        game_id=game.id,
        player_id=players[0].id,
        type=ActionType.StartGame,
        payload={"player_ids": [player.id for player in players]},
    )
    sm().handle_action(start_game_action)

    role_to_players = defaultdict(list)
    for player in players:
        event = comm_service.records[player.id].popleft()
        assert event.type == EventType.GameStarted, event
        role = Role(event.payload["role"])
        role_to_players[role].append(player)

    assert_quest_started_event(comm_service, players, 1)
    assert_round_started_event(comm_service, players, 1)

    assert len(role_to_players[Role.Merlin]) == 1
    assert len(role_to_players[Role.Percival]) == 1
    assert len(role_to_players[Role.Mordred]) == 1
    assert len(role_to_players[Role.Morgana]) == 1
    assert len(role_to_players[Role.Assassin]) == 1
    assert len(role_to_players[Role.Oberon]) == 1
    assert len(role_to_players[Role.Villager]) == 4

    # Quest 1
    # Round 1
    leader = players[0]
    assert_team_selection_requested_event(comm_service, leader, 1, 1, 3)
    submit_team_proposal(game.id, leader, players[:3], sm())
    assert_team_proposal_submitted_event(comm_service, players, players[:3])
    vote_team_proposal(game.id, players[:3], players[3:], sm())
    assert_round_vote_cast_event(comm_service, players, 1, 1)
    player_votes = {p.id: VoteResult.Pass for p in players[:3]} | {p.id: VoteResult.Fail for p in players[3:]}
    assert_round_completed_event(comm_service, players, 1, 1, VoteResult.Fail, player_votes)
    assert_event(comm_service, players, EventType.RoundStarted)

    # Round 2
    leader = players[1]
    assert_team_selection_requested_event(comm_service, leader, 1, 2, 3)
    submit_team_proposal(game.id, leader, players[1:4], sm())
    assert_team_proposal_submitted_event(comm_service, players, players[1:4])
    vote_team_proposal(game.id, players, [], sm())
    assert_round_vote_cast_event(comm_service, players, 1, 2)
    assert_round_completed_event(comm_service, players, 1, 2, VoteResult.Pass, {p.id: VoteResult.Pass for p in players})
    assert_quest_vote_started_event(comm_service, players, 1)
    assert_quest_vote_requested_event(comm_service, players[1:4], 1)

    # Vote Quest 1
    vote_quest(game.id, 1, players[1:4], [], sm())
    assert_quest_vote_cast_event(comm_service, players, players[1:4], 1)
    assert_quest_completed_event(comm_service, players, 1, VoteResult.Pass)

    # Quest 2
    # Round 1
    leader = players[2]
    assert_event(comm_service, players, EventType.QuestStarted)
    assert_event(comm_service, players, EventType.RoundStarted)
    assert_team_selection_requested_event(comm_service, leader, 2, 1, 4)
    submit_team_proposal(game.id, players[2], players[1:5], sm())
    vote_team_proposal(game.id, players, [], sm())
    clear_comm_service(comm_service)
    vote_quest(game.id, 2, players[1:5], [], sm())
    assert_quest_vote_cast_event(comm_service, players, players[1:5], 2)
    assert_quest_completed_event(comm_service, players, 2, VoteResult.Pass)

    # Quest 3
    # Round 1
    round_number = 1
    for leader in players[3:8]:
        submit_team_proposal(game.id, leader, players[2:6], sm())
        clear_comm_service(comm_service)
        vote_team_proposal(game.id, [], players, sm())
        assert_round_vote_cast_event(comm_service, players, 3, round_number)
        assert_round_completed_event(comm_service, players, 3, round_number, VoteResult.Fail,
                                     {p.id: VoteResult.Fail for p in players})
        round_number += 1
    assert_quest_completed_event(comm_service, players, 3, VoteResult.Fail)

    # Quest 4
    # Round 1
    leader = players[8]
    submit_team_proposal(game.id, leader, players[3:8], sm())
    vote_team_proposal(game.id, players, [], sm())
    clear_comm_service(comm_service)
    vote_quest(game.id, 4, players[3:7], [players[7]], sm())
    assert_quest_vote_cast_event(comm_service, players, players[3:8], 4)
    assert_quest_completed_event(comm_service, players, 4, VoteResult.Pass)

    # Assassination
    assert_assassination_started_event(comm_service, players)
    assassin = role_to_players[Role.Assassin][0]
    merlin = role_to_players[Role.Merlin][0]
    assert_event(comm_service, [assassin], EventType.AssassinationTargetRequested)
    submit_assassination_target(game.id, assassin, merlin, sm())
    assert_event(comm_service, players, EventType.AssassinationSucceeded)
    assert_event(comm_service, players, EventType.GameEnded)
    game = dynamodb_repository.get_game(game.id)
    assert game.result == "Evil"


def submit_assassination_target(game_id, assassin, target, sm):
    action = Action(
        id=uuid.uuid4().hex,
        game_id=game_id,
        player_id=assassin.id,
        type=ActionType.SubmitAssassinationTarget,
        payload={"target_id": target.id},
    )
    sm.handle_action(action)


def assert_assassination_started_event(comm_service, players):
    for p in players:
        event = comm_service.records[p.id].popleft()
        assert event.type == EventType.AssassinationStarted, event
        assert event.payload["assassination_attempts"] == 0


def assert_quest_completed_event(comm_service, players, quest_number, result):
    for p in players:
        event = comm_service.records[p.id].popleft()
        assert event.type == EventType.QuestCompleted, event
        assert event.payload["quest_number"] == quest_number
        assert event.payload["result"] == result.value


def assert_team_selection_requested_event(comm_service, leader, quest_number, round_number, num_of_players):
    event = comm_service.records[leader.id].popleft()
    assert event.type == EventType.TeamSelectionRequested, event
    assert event.payload["number_of_players"] == num_of_players
    assert event.payload["quest_number"] == quest_number
    assert event.payload["round_number"] == round_number


def assert_team_proposal_submitted_event(comm_service, players, team_members):
    for p in players:
        event = comm_service.records[p.id].popleft()
        assert event.type == EventType.TeamProposalSubmitted, event
        assert event.payload["team_member_ids"] == [m.id for m in team_members]


def assert_quest_vote_requested_event(comm_service, team_members, quest_number):
    for m in team_members:
        event = comm_service.records[m.id].popleft()
        assert event.type == EventType.QuestVoteRequested, event
        assert event.payload["quest_number"] == quest_number


def assert_round_completed_event(comm_service, players, quest_number, round_number, result, player_votes):
    for p in players:
        event = comm_service.records[p.id].popleft()
        assert event.type == EventType.RoundCompleted, event
        assert event.payload["quest_number"] == quest_number
        assert event.payload["round_number"] == round_number
        assert event.payload["player_votes"] == {k: v.value for k, v in player_votes.items()}
        assert event.payload["result"] == result.value


def assert_event(comm_service, players, event_type):
    for p in players:
        event = comm_service.records[p.id].popleft()
        assert event.type == event_type, event


def assert_quest_started_event(comm_service, players, quest_number):
    for p in players:
        event = comm_service.records[p.id].popleft()
        assert event.type == EventType.QuestStarted, event
        assert event.payload["quest_number"] == quest_number


def assert_round_started_event(comm_service, players, round_number):
    for p in players:
        event = comm_service.records[p.id].popleft()
        assert event.type == EventType.RoundStarted, event
        assert event.payload["round_number"] == round_number


def vote_team_proposal(game_id, approves, rejects, statemachine):
    payloads = [(p.id, True) for p in approves] + [(p.id, False) for p in rejects]
    for pid, is_approved in payloads:
        action = Action(
            id=uuid.uuid4().hex,
            game_id=game_id,
            player_id=pid,
            type=ActionType.CastRoundVote,
            payload={
                "player_id": pid,
                "is_approved": is_approved
            },
        )
        statemachine.handle_action(action)


def assert_round_vote_cast_event(comm_service, players, quest_number, round_number):
    for p in players:
        for _p in players:
            event = comm_service.records[p.id].popleft()
            assert event.type == EventType.RoundVoteCast, event
            assert event.payload["player_id"] == _p.id
            assert event.payload["quest_number"] == quest_number
            assert event.payload["round_number"] == round_number


def assert_quest_vote_started_event(comm_service, players, quest_number):
    for p in players:
        event = comm_service.records[p.id].popleft()
        assert event.type == EventType.QuestVoteStarted, event
        assert event.payload["quest_number"] == quest_number


def assert_quest_vote_cast_event(comm_service, players, team_members, quest_number):
    for p in players:
        for m in team_members:
            event = comm_service.records[p.id].popleft()
            assert event.type == EventType.QuestVoteCast, event
            assert event.payload["player_id"] == m.id
            assert event.payload["quest_number"] == quest_number


def assert_game_ended_event(comm_service, players, result):
    player_roles = {p.id: p.role.value for p in players}
    for p in players:
        event = comm_service.records[p.id].popleft()
        assert event.type == EventType.GameEnded, event
        assert event.payload["result"] == result.value
        assert event.payload["player_roles"] == player_roles


def vote_quest(game_id, quest_number, approves, rejects, statemachine):
    payloads = [(p.id, True) for p in approves] + [(p.id, False) for p in rejects]
    for pid, is_approved in payloads:
        action = Action(
            id=uuid.uuid4().hex,
            game_id=game_id,
            player_id=pid,
            type=ActionType.CastQuestVote,
            payload={
                "player_id": pid,
                "quest_number": quest_number,
                "is_approved": is_approved
            },
        )
        statemachine.handle_action(action)


def submit_team_proposal(game_id, leader, team_members, statemachine):
    team_member_ids = [p.id for p in team_members]
    action = Action(
        id=uuid.uuid4().hex,
        game_id=game_id,
        player_id=leader.id,
        type=ActionType.SubmitTeamProposal,
        payload={
            "team_member_ids": team_member_ids,
        },
    )
    statemachine.handle_action(action)


def clear_comm_service(comm_service):
    for k in comm_service.records.keys():
        comm_service.records[k].clear()
