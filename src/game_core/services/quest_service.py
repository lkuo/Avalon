from typing import Optional

from game_core.constants.vote_result import VoteResult
from game_core.entities.quest import Quest
from game_core.entities.quest_vote import QuestVote
from game_core.repository import Repository
from game_core.services.event_service import EventService
from game_core.services.player_service import PlayerService
from game_core.services.round_service import RoundService


class QuestService:
    def __init__(
            self,
            round_service: RoundService,
            event_service: EventService,
            player_service: PlayerService,
            repository: Repository,
    ):
        self._round_service = round_service
        self._event_service = event_service
        self._player_service = player_service
        self._repository = repository

    def add_quest(self, game_id: str, quest_number: int) -> Quest:
        return self._repository.put_quest(game_id, quest_number)

    def get_quests(self, game_id: str) -> list[Quest]:
        return self._repository.get_quests(game_id)

    def get_last_quest(self, game_id: str) -> Optional[Quest]:
        quests = self._repository.get_quests(game_id)
        quests = sorted(quests, key=lambda q: q.quest_number)
        return quests[-1] if quests else None

    def create_quest(self, game_id: str) -> Quest:
        current_quest = self.get_current_quest(game_id)
        quest_number = 1 if not current_quest else current_quest.quest_number + 1
        quest = self._repository.put_quest(game_id, quest_number)
        self._event_service.create_quest_started_event(game_id, quest_number)
        return quest

    def create_quest_vote(self, game_id: str, quest_number: int, player_id: str, is_approved: bool) -> QuestVote:
        return self._repository.put_quest_vote(game_id, quest_number, player_id, is_approved)

    def update_quest(self, quest: Quest) -> Quest:
        return self._repository.update_quest(quest)

    def get_quest_votes(self, game_id: str, quest_number: int) -> list[QuestVote]:
        return self._repository.get_quest_votes(game_id, quest_number)

    def get_quests(self, game_id: str) -> list[Quest]:
        return self._repository.get_quests(game_id)

    def is_quest_passed(self, game_id: str, quest_number: int) -> bool:
        quest_votes = self._repository.get_quest_votes(game_id, quest_number)
        disapprove_votes = [qv for qv in quest_votes if not qv.result]

        return len(disapprove_votes) <= (0 if quest_number != 4 else 1)

    def get_current_quest(self, game_id: str) -> Optional[Quest]:
        quests = self._repository.get_quests(game_id)
        quests = sorted(quests, key=lambda q: q.quest_number)
        return None if not quests else quests[-1]

    def set_team_member_ids(
            self, game_id: str, quest_number: int, team_member_ids: list[str]
    ) -> None:
        quest = self._repository.get_quest(game_id, quest_number)
        quest.team_member_ids = team_member_ids
        self._repository.update_quest(quest)

    def complete_quest(self, game_id: str, quest: Quest, result: VoteResult) -> Quest:
        quest.result = result
        updated_quest = self._repository.update_quest(quest)
        self._event_service.create_quest_completed_event(
            game_id, quest.quest_number, result
        )
        return updated_quest

    def complete_current_quest(self, game_id: str, result: VoteResult) -> Quest:
        quest = self.get_current_quest(game_id)
        return self.complete_quest(game_id, quest, result)
