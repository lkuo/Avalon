import uuid
from typing import Any, Optional

import boto3

from game_core.constants.event_type import EventType
from game_core.constants.game_status import GameStatus
from game_core.constants.role import Role
from game_core.constants.state_name import StateName
from game_core.constants.vote_result import VoteResult
from game_core.entities.event import Event
from game_core.entities.game import Game, GameConfig
from game_core.entities.player import Player
from game_core.entities.quest import Quest
from game_core.entities.quest_vote import QuestVote
from game_core.entities.round import Round
from game_core.entities.round_vote import RoundVote
from game_core.repository import Repository


class DynamoDBRepository(Repository):

    def __init__(self, table: str, region: str, endpoint_url: Optional[str] = None):
        self._table = table
        self._dynamodb = boto3.resource(
            "dynamodb", region_name=region, endpoint_url=endpoint_url
        )
        self._table = self._dynamodb.Table(table)

    def get_game(self, game_id: str) -> Game:
        response = self._table.get_item(Key={"pk": game_id, "sk": "game"})
        if "Item" not in response:
            raise ValueError(f"Game {game_id} not found")
        item = response["Item"]
        game_config = GameConfig(
            quest_team_size={int(k): int(v) for k, v in item["config"]["quest_team_size"].items()},
            max_round=item["config"]["max_round"],
            roles=item["config"]["roles"],
            assassination_attempts=item["config"]["assassination_attempts"],
        )
        return Game(
            id=item["pk"],
            status=GameStatus(item["status"]),
            state=StateName(item["state"]),
            config=game_config,
            player_ids=item.get("player_ids"),
            assassination_attempts=item.get("assassination_attempts"),
            result=item.get("result"),
        )

    def update_game(self, game: Game) -> Game:
        key = {
            "pk": game.id,
            "sk": "game",
        }
        update_expression = "SET #status = :status, #state = :state, #config = :config, #player_ids = :player_ids, #assassination_attempts = :assassination_attempts, #result = :result"
        expression_attribute_names = {
            "#status": "status",
            "#state": "state",
            "#config": "config",
            "#player_ids": "player_ids",
            "#assassination_attempts": "assassination_attempts",
            "#result": "result",
        }
        expression_attribute_values = {
            ":status": game.status.value,
            ":state": game.state.value,
            ":config": {
                "quest_team_size": {
                    str(k): str(v) for k, v in game.config.quest_team_size.items()
                },
                "max_round": game.config.max_round,
                "roles": {
                    role: [role for role in roles]
                    for role, roles in game.config.roles.items()
                },
                "assassination_attempts": game.config.assassination_attempts,
            },
            ":player_ids": game.player_ids,
            ":assassination_attempts": game.assassination_attempts,
            ":result": game.result,
        }
        self._table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
        )
        return game

    def put_event(
        self,
        game_id: str,
        event_type: EventType,
        recipients: list[str],
        payload: dict[str, Any],
        timestamp: str,
    ) -> Event:
        event_id = uuid.uuid4().hex
        item = {
            "pk": game_id,
            "sk": f"event_{event_id}",
            "type": event_type.value,
            "recipients": recipients,
            "payload": payload,
            "timestamp": timestamp,
        }
        self._table.put_item(Item=item)
        return Event(
            id=event_id,
            game_id=game_id,
            type=event_type,
            recipients=recipients,
            payload=payload,
            timestamp=timestamp,
        )

    def get_player(self, player_id: str) -> Player:
        # player_id = gameId_player_playerId
        game_id, sk = player_id.split("_", 1)
        response = self._table.get_item(Key={"pk": game_id, "sk": sk})
        if "Item" not in response:
            raise ValueError(f"Player {player_id} not found")
        item = response["Item"]
        return Player(
            id=player_id,
            game_id=game_id,
            name=item["name"],
            secret=item["secret"],
            role=Role(item["role"]) if item.get("role") else None,
            known_player_ids=item.get("known_player_ids", []),
        )

    def put_player(self, game_id: str, name: str, secret: str) -> Player:
        player_uuid = uuid.uuid4().hex
        item = {
            "pk": game_id,
            "sk": f"player_{player_uuid}",
            "name": name,
            "secret": secret,
            "role": None,
            "known_player_ids": [],
        }
        self._table.put_item(Item=item)
        return Player(
            id=f"{game_id}_player_{player_uuid}",
            game_id=game_id,
            name=name,
            secret=secret,
            role=None,
            known_player_ids=[],
        )

    def update_player(self, player: Player) -> Player:
        key = {
            "pk": player.game_id,
            "sk": player.id.split("_", 1)[1],
        }
        update_expression = "SET #name=:name, #secret=:secret, #role=:role, #known_player_ids=:known_player_ids"
        expression_attribute_names = {
            "#name": "name",
            "#secret": "secret",
            "#role": "role",
            "#known_player_ids": "known_player_ids",
        }
        expression_attribute_values = {
            ":name": player.name,
            ":secret": player.secret,
            ":role": player.role.value if player.role else None,
            ":known_player_ids": player.known_player_ids,
        }

        res = self._table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="UPDATED_NEW"
        )
        attributes = res["Attributes"]
        return Player(
            id=player.id,
            game_id=player.game_id,
            name=attributes["name"],
            secret=attributes["secret"],
            role=Role(attributes["role"]) if attributes.get("role") else None,
            known_player_ids=attributes.get("known_player_ids", []),
        )

    def get_players(self, game_id: str) -> list[Player]:
        key_condition_expression = "pk = :pk AND begins_with(sk, :sk_prefix)"
        expression_attribute_values = {":pk": game_id, ":sk_prefix": "player_"}
        response = self._table.query(
            KeyConditionExpression=key_condition_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
        items = response["Items"]
        return [
            Player(
                id=f"{game_id}_{item['sk']}",
                game_id=game_id,
                name=item["name"],
                secret=item["secret"],
                role=Role(item["role"]) if item.get("role") else None,
                known_player_ids=item.get("known_player_ids", []),
            )
            for item in items
        ]

    def put_quest(self, game_id: str, quest_number: int) -> Quest:
        pk = game_id
        sk = f"quest_{quest_number}"
        item = {
            "pk": pk,
            "sk": sk,
            "quest_number": quest_number,
            "result": None,
            "team_member_ids": [],
        }
        self._table.put_item(Item=item)
        return Quest(
            id=f"{pk}_{sk}",
            game_id=game_id,
            quest_number=quest_number,
            result=None,
            team_member_ids=[],
        )

    def get_quests(self, game_id: str) -> list[Quest]:
        key_condition_expression = "pk = :pk AND begins_with(sk, :sk_prefix)"
        expression_attribute_values = {":pk": game_id, ":sk_prefix": "quest_"}
        response = self._table.query(
            KeyConditionExpression=key_condition_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
        items = response["Items"]
        return [
            Quest(
                id=f"{game_id}_{item['sk']}",
                game_id=game_id,
                quest_number=int(item["quest_number"]),
                result=VoteResult(item["result"]) if item.get("result") else None,
                team_member_ids=item["team_member_ids"],
            )
            for item in items
        ]

    def update_quest(self, quest: Quest) -> Quest:
        key = {
            "pk": quest.game_id,
            "sk": quest.id.split("_", 1)[1],
        }
        update_expression = "SET #quest_number=:quest_number, #result=:result, #team_member_ids=:team_member_ids"
        expression_attribute_names = {
            "#quest_number": "quest_number",
            "#result": "result",
            "#team_member_ids": "team_member_ids",
        }
        expression_attribute_values = {
            ":quest_number": quest.quest_number,
            ":result": quest.result and quest.result.value,
            ":team_member_ids": quest.team_member_ids,
        }

        res = self._table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="UPDATED_NEW"
        )
        attributes = res["Attributes"]
        return Quest(
            id=quest.id,
            game_id=quest.game_id,
            quest_number=attributes["quest_number"],
            result=VoteResult(attributes["result"]) if attributes.get("result") else None,
            team_member_ids=attributes["team_member_ids"],
        )

    def get_quest(self, game_id: str, quest_number: int) -> Quest:
        response = self._table.get_item(Key={"pk": game_id, "sk": f"quest_{quest_number}"})
        if "Item" not in response:
            raise ValueError(f"Quest {game_id}_{quest_number} not found")
        item = response["Item"]
        return Quest(
            id=f"{game_id}_quest_{quest_number}",
            game_id=game_id,
            quest_number=quest_number,
            result=VoteResult(item["result"]) if item.get("result") else None,
            team_member_ids=item["team_member_ids"],
        )

    def put_quest_vote(
            self, game_id: str, quest_number: int, player_id: str, is_approved: bool
    ) -> QuestVote:
        item = {
            "pk": game_id,
            "sk": f"vote_quest_{quest_number}_{player_id}",
            "player_id": player_id,
            "quest_number": quest_number,
            "result": (VoteResult.Pass.value if is_approved else VoteResult.Fail.value),
        }
        self._table.put_item(Item=item)
        return QuestVote(
            id=f"{game_id}_vote_quest_{quest_number}_{player_id}",
            game_id=game_id,
            player_id=player_id,
            quest_number=quest_number,
            result=(VoteResult.Pass if is_approved else VoteResult.Fail),
        )

    def get_quest_votes(self, game_id: str, quest_number: int) -> list[QuestVote]:
        key_condition_expression = "pk = :pk AND begins_with(sk, :sk_prefix)"
        expression_attribute_values = {":pk": game_id, ":sk_prefix": f"vote_quest_{quest_number}_"}
        response = self._table.query(
            KeyConditionExpression=key_condition_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
        items = response["Items"]
        return [
            QuestVote(
                id=f"{game_id}_{item['sk']}",
                game_id=game_id,
                player_id=item["player_id"],
                quest_number=int(item["quest_number"]),
                result=VoteResult(item["result"]),
            )
            for item in items
        ]

    def get_rounds(self, game_id: str) -> list[Round]:
        key_condition_expression = "pk = :pk AND begins_with(sk, :sk_prefix)"
        expression_attribute_values = {":pk": game_id, ":sk_prefix": "round_"}
        response = self._table.query(
            KeyConditionExpression=key_condition_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
        items = response["Items"]
        return [
            Round(
                id=f"{game_id}_{item['sk']}",
                game_id=game_id,
                quest_number=int(item["quest_number"]),
                round_number=int(item["round_number"]),
                leader_id=item["leader_id"],
                team_member_ids=item["team_member_ids"],
                result=(VoteResult(item["result"]) if item.get("result") else None),
            )
            for item in items
        ]

    def put_round(
        self, game_id: str, quest_number: int, round_number: int, leader_id: str
    ) -> Round:
        item = {
            "pk": game_id,
            "sk": f"round_{quest_number}_{round_number}",
            "quest_number": quest_number,
            "round_number": round_number,
            "leader_id": leader_id,
            "team_member_ids": [],
        }
        self._table.put_item(Item=item)
        return Round(
            id=f"{game_id}_round_{quest_number}_{round_number}",
            game_id=game_id,
            quest_number=quest_number,
            round_number=round_number,
            leader_id=leader_id,
            team_member_ids=[],
        )

    def get_round(self, game_id: str, quest_number: int, round_number: int) -> Round:
        response = self._table.get_item(Key={"pk": game_id, "sk": f"round_{quest_number}_{round_number}"})
        if "Item" not in response:
            raise ValueError(f"Round {game_id}_{quest_number}_{round_number} not found")
        item = response["Item"]
        return Round(
            id=f"{game_id}_round_{quest_number}_{round_number}",
            game_id=game_id,
            quest_number=quest_number,
            round_number=round_number,
            leader_id=item["leader_id"],
            team_member_ids=item["team_member_ids"],
            result=(VoteResult(item["result"]) if item.get("result") else None)
        )

    def update_round(self, game_round: Round) -> Round:
        key = {
            "pk": game_round.game_id,
            "sk": game_round.id.split("_", 1)[1],
        }
        update_expression = "SET #quest_number=:quest_number, #round_number=:round_number, #leader_id=:leader_id, #team_member_ids=:team_member_ids, #result=:result"
        expression_attribute_names = {
            "#quest_number": "quest_number",
            "#round_number": "round_number",
            "#leader_id": "leader_id",
            "#team_member_ids": "team_member_ids",
            "#result": "result",
        }
        expression_attribute_values = {
            ":quest_number": game_round.quest_number,
            ":round_number": game_round.round_number,
            ":leader_id": game_round.leader_id,
            ":team_member_ids": game_round.team_member_ids,
            ":result": game_round.result and game_round.result.value,
        }

        res = self._table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="UPDATED_NEW"
        )
        attributes = res["Attributes"]
        return Round(
            id=game_round.id,
            game_id=game_round.game_id,
            quest_number=attributes["quest_number"],
            round_number=attributes["round_number"],
            leader_id=attributes["leader_id"],
            team_member_ids=attributes["team_member_ids"],
            result=VoteResult(attributes["result"]) if attributes.get("result") else None,
        )

    def put_round_vote(
        self,
        game_id: str,
        quest_number: int,
        round_number: int,
        player_id: str,
        vote_result: VoteResult,
    ) -> RoundVote:
        item = {
            "pk": game_id,
            "sk": f"vote_round_{quest_number}_{round_number}_{player_id}",
            "player_id": player_id,
            "quest_number": quest_number,
            "round_number": round_number,
            "result": vote_result.value,
        }
        self._table.put_item(Item=item)
        return RoundVote(
            id=f"{game_id}_vote_round_{quest_number}_{round_number}_{player_id}",
            game_id=game_id,
            quest_number=quest_number,
            round_number=round_number,
            player_id=player_id,
            result=vote_result,
        )

    def get_round_vote(
        self, game_id: str, quest_number: int, round_number: int, player_id: str
    ) -> RoundVote:
        key = {
            "pk": game_id,
            "sk": f"vote_round_{quest_number}_{round_number}_{player_id}",
        }
        response = self._table.get_item(Key=key)
        if "Item" not in response:
            raise ValueError(f"Round vote {game_id}_{quest_number}_{round_number}_{player_id} not found")
        item = response["Item"]
        return RoundVote(
            id=f"{game_id}_vote_round_{quest_number}_{round_number}_{player_id}",
            game_id=game_id,
            quest_number=quest_number,
            round_number=round_number,
            player_id=player_id,
            result=VoteResult(item["result"]),
        )

    def get_round_votes(
        self, game_id: str, quest_number: int, round_number: int
    ) -> list[RoundVote]:
        key_condition_expression = "pk = :pk AND begins_with(sk, :sk_prefix)"
        expression_attribute_values = {":pk": game_id, ":sk_prefix": f"vote_round_{quest_number}_{round_number}_"}
        response = self._table.query(
            KeyConditionExpression=key_condition_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
        items = response["Items"]
        return [
            RoundVote(
                id=f"{game_id}_{item['sk']}",
                game_id=game_id,
                quest_number=int(item["quest_number"]),
                round_number=int(item["round_number"]),
                player_id=item["player_id"],
                result=VoteResult(item["result"]),
            )
            for item in items
        ]
