import uuid
from typing import Any, Optional

import boto3

from game_core.constants.event_type import EventType
from game_core.constants.role import Role
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
            status=item["status"],
            state=item["state"],
            config=game_config,
            player_ids=item.get("player_ids"),
            assassination_attempts=item.get("assassination_attempts"),
            result=item.get("result"),
        )

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
        game_id, player_id = player_id.split("_", 1)
        response = self._table.get_item(Key={"pk": game_id, "sk": player_id})
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
        pass

    def update_player(self, player: Player) -> Player:
        pass

    def get_players(self, game_id: str) -> list[Player]:
        pass

    def put_game(self, game: Game) -> Game:
        pass

    def put_quest(self, game_id: str, quest_number: int) -> Quest:
        pass

    def get_quests(self, game_id: str) -> list[Quest]:
        pass

    def get_rounds(self, game_id: str) -> list[Round]:
        pass

    def put_round(
        self, game_id: str, quest_number: int, round_number: int, leader_id: str
    ) -> Round:
        pass

    def update_round(self, game_round: Round) -> Round:
        pass

    def get_quest(self, game_id: str, quest_number: int) -> Quest:
        pass

    def get_round(self, game_id: str, quest_number: int, round_number: int) -> Round:
        pass

    def put_round_vote(
        self,
        game_id: str,
        quest_number: int,
        round_number: int,
        player_id: str,
        vote_result: VoteResult,
    ) -> RoundVote:
        pass

    def get_round_vote(
        self, game_id: str, quest_number: int, round_number: int, player_id: str
    ) -> RoundVote:
        pass

    def get_round_votes(
        self, game_id: str, quest_number: int, round_number: int
    ) -> list[RoundVote]:
        pass

    def update_quest(self, quest: Quest) -> Quest:
        pass

    def put_quest_vote(
        self, game_id: str, quest_number: int, player_id: str, is_approved: bool
    ) -> QuestVote:
        pass

    def get_quest_votes(self, game_id: str, quest_number: int) -> list[QuestVote]:
        pass

    def update_game(self, game: Game) -> Game:
        pass
