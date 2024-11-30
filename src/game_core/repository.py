from abc import ABC
from typing import Any

from game_core.entities.event import Event
from game_core.entities.game import Game
from game_core.entities.player import Player
from game_core.entities.quest import Quest
from game_core.entities.quest_vote import QuestVote
from game_core.entities.round import Round
from game_core.entities.round_vote import RoundVote


class Repository(ABC):

    def get_game(self, game_id: str) -> Game:
        ...

    def put_event(self, game_id: str, event_type: str, recipients: list[str], payload: dict[str, Any],
                  timestamp: int) -> Event:
        pass

    def put_player(self, game_id: str, name: str, secret: str) -> Player:
        pass

    def put_players(self, game_id, players: list[Player]) -> list[Player]:
        pass

    def get_players(self, game_id: str) -> list[Player]:
        pass

    def put_events(self, events: list[Event]) -> list[Event]:
        pass

    def put_game(self, game) -> Game:
        pass

    def put_quest(self, game_id: str, quest_number: int) -> Quest:
        pass

    def get_quests(self, game_id) -> list[Quest]:
        pass

    def get_rounds_by_quest(self, game_id, quest_number) -> list[Round]:
        pass

    def put_round(self, game_id: str, quest_number: int, round_number: int, leader_id: str) -> Round:
        pass

    def update_round(self, game_round: Round) -> Round:
        pass

    def get_player(self, game_id: str, player_id: str) -> Player:
        pass

    def get_quest(self, game_id: str, quest_number: int) -> Quest:
        pass

    def get_round(self, game_id: str, quest_number: int, round_number: int) -> Round:
        pass

    def put_round_vote(self, game_id, quest_number, round_number, player_id, is_approved):
        pass

    def get_round_vote(self, game_id, quest_number, round_number, player_id) -> RoundVote:
        pass

    def get_round_votes(self, game_id: str, quest_number: int, round_number: int) -> list[RoundVote]:
        pass

    def update_quest(self, quest: Quest) -> Quest:
        pass

    def put_quest_vote(self, game_id, quest_number, player_id, is_approved):
        pass

    def get_quest_votes(self, game_id, quest_number) -> list[QuestVote]:
        pass
