from abc import ABC, abstractmethod
from typing import Any

from game_core.constants.event_type import EventType
from game_core.constants.vote_result import VoteResult
from game_core.entities.event import Event
from game_core.entities.game import Game
from game_core.entities.player import Player
from game_core.entities.quest import Quest
from game_core.entities.quest_vote import QuestVote
from game_core.entities.round import Round
from game_core.entities.round_vote import RoundVote


class Repository(ABC):

    @abstractmethod
    def put_game(
        self,
        quest_team_size: dict[int, int],
        roles: dict[str, list[str]],
        assassination_attempts: int
    ) -> Game:
        pass

    @abstractmethod
    def get_game(self, game_id: str) -> Game:
        pass

    @abstractmethod
    def put_event(
        self,
        game_id: str,
        event_type: EventType,
        recipients: list[str],
        payload: dict[str, Any],
        timestamp: str,
    ) -> Event:
        pass

    @abstractmethod
    def put_player(self, player_id: str, game_id: str, name: str, secret: str) -> Player:
        pass

    @abstractmethod
    def update_player(self, player: Player) -> Player:
        pass

    @abstractmethod
    def get_players(self, game_id: str) -> list[Player]:
        pass

    @abstractmethod
    def put_quest(self, game_id: str, quest_number: int) -> Quest:
        pass

    @abstractmethod
    def get_quests(self, game_id: str) -> list[Quest]:
        pass

    @abstractmethod
    def get_rounds(self, game_id: str) -> list[Round]:
        pass

    @abstractmethod
    def put_round(
        self, game_id: str, quest_number: int, round_number: int, leader_id: str
    ) -> Round:
        pass

    @abstractmethod
    def update_round(self, game_round: Round) -> Round:
        pass

    @abstractmethod
    def get_player(self, player_id: str) -> Player:
        pass

    @abstractmethod
    def get_quest(self, game_id: str, quest_number: int) -> Quest:
        pass

    @abstractmethod
    def get_round(self, game_id: str, quest_number: int, round_number: int) -> Round:
        pass

    @abstractmethod
    def put_round_vote(
        self,
        game_id: str,
        quest_number: int,
        round_number: int,
        player_id: str,
        vote_result: VoteResult,
    ) -> RoundVote:
        pass

    @abstractmethod
    def get_round_votes(
        self, game_id: str, quest_number: int, round_number: int
    ) -> list[RoundVote]:
        pass

    @abstractmethod
    def update_quest(self, quest: Quest) -> Quest:
        pass

    @abstractmethod
    def put_quest_vote(
        self, game_id: str, quest_number: int, player_id: str, is_approved: bool
    ) -> QuestVote:
        pass

    @abstractmethod
    def get_quest_votes(self, game_id: str, quest_number: int) -> list[QuestVote]:
        pass

    @abstractmethod
    def update_game(self, game: Game) -> Game:
        pass
