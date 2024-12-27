from typing import Optional

from pydantic import BaseModel

from game_core.constants.vote_result import VoteResult
from game_core.entities.action import Action
from game_core.entities.quest import Quest
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

    def on_enter_quest_voting_state(self, game_id: str) -> None:
        """
        On enter broadcast quest voting started by team members, and notify team members to cast vote
        :param game_id:
        :return:
        """
        quest = self.get_current_quest(game_id)
        current_round = self._round_service.get_current_round(game_id)
        team_member_ids = current_round.team_member_ids

        self._event_service.create_quest_vote_started_event(
            game_id, quest.quest_number, team_member_ids
        )
        self._event_service.create_quest_vote_requested_event(
            game_id, quest.quest_number, team_member_ids
        )

    def handle_cast_quest_vote(self, action: Action) -> None:
        """
        On event saves vote and broadcast player X has voted
        :param action:
        :return:
        """
        self._validate_quest_vote_cast_event(action)
        payload = action.payload
        game_id = action.game_id
        player_id = payload.get("player_id")
        is_approved = payload.get("is_approved")
        quest_number = payload.get("quest_number")
        vote_result = VoteResult.Pass if is_approved else VoteResult.Fail
        self._repository.put_quest_vote(game_id, quest_number, player_id, is_approved)
        self._event_service.create_quest_vote_cast_event(
            game_id, quest_number, player_id, vote_result
        )

        if not self.is_quest_vote_completed(game_id, quest_number):
            return
        result = (
            VoteResult.Pass
            if self.is_quest_passed(action.game_id, quest_number)
            else VoteResult.Fail
        )
        self.complete_quest(action.game_id, quest_number, result)

    def _validate_quest_vote_cast_event(self, action: Action) -> None:
        CastQuestVotePayload(**action.payload)
        payload = action.payload
        player_id = payload.get("player_id")
        quest_number = payload.get("quest_number")
        game_id = action.game_id
        self._player_service.get_player(player_id)
        self.get_quest(game_id, quest_number)

    def is_quest_vote_completed(self, game_id: str, quest_number: int) -> bool:
        quest = self._repository.get_quest(game_id, quest_number)
        quest_votes = self._repository.get_quest_votes(game_id, quest_number)
        return len(quest_votes) == len(quest.team_member_ids)

    def is_quest_passed(self, game_id: str, quest_number: int) -> bool:
        quest_votes = self._repository.get_quest_votes(game_id, quest_number)
        disapprove_votes = [qv for qv in quest_votes if not qv.result]

        return len(disapprove_votes) <= (0 if quest_number != 4 else 1)

    def has_majority(self, game_id: str) -> bool:
        """
        If any team has won 3 out of 5 missions
        :param game_id:
        :return:
        """
        quests = self._repository.get_quests(game_id)
        passed_quests = [q for q in quests if q.result == VoteResult.Pass]
        failed_quests = [q for q in quests if q.result == VoteResult.Fail]
        return len(passed_quests) >= 3 or len(failed_quests) >= 3

    def handle_on_enter_team_selection_state(self, game_id: str) -> None:
        current_quest = self.get_current_quest(game_id)
        if not current_quest or current_quest.result:
            current_quest = self.create_quest(game_id)
        self._round_service.create_round(game_id, current_quest.quest_number)

    def is_final_proposal_failed(self, game_id: str) -> bool:
        current_quest = self.get_current_quest(game_id)
        current_round = self._round_service.get_current_round(game_id)
        return (
            current_round
            and current_round.round_number == 5
            and not current_quest.result
        )

    def create_quest(self, game_id: str) -> Quest:
        current_quest = self.get_current_quest(game_id)
        quest_number = 1 if not current_quest else current_quest.quest_number + 1
        quest = self._repository.put_quest(game_id, quest_number)
        self._event_service.create_quest_started_event(game_id, quest_number)
        return quest

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

    def get_quest(self, game_id: str, quest_number: int) -> Quest:
        quest = self._repository.get_quest(game_id, quest_number)
        if not quest:
            raise ValueError(f"Quest {quest_number} not found")
        return quest


class CastQuestVotePayload(BaseModel):
    player_id: str
    is_approved: bool
    quest_number: int
