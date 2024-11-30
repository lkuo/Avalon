from datetime import datetime
from typing import Optional

from game_core.constants.event_type import EventType
from game_core.constants.voting_result import VotingResult
from game_core.entities.event import Event
from game_core.entities.quest import Quest
from game_core.repository import Repository
from game_core.services.comm_service import CommService
from game_core.services.round_service import RoundService


class QuestService:

    def __init__(self, repository: Repository, round_service: RoundService, comm_service: CommService):
        self._repository = repository
        self._round_service = round_service
        self._comm_service = comm_service

    def on_enter_quest_voting_state(self, game_id: str) -> None:
        """
        On enter broadcast quest voting started by team members, and notify team members to cast vote
        :param game_id:
        :return:
        """
        quest = self._get_last_quest(game_id)
        team_member_ids = quest.team_member_ids
        payload = {
            "game_id": game_id,
            "quest_number": quest.quest_number,
            "team_member_ids": team_member_ids
        }
        event = self._repository.put_event(game_id, EventType.QUEST_VOTING_STARTED.value, [], payload,
                                           int(datetime.now().timestamp()))
        self._comm_service.broadcast(event)
        event = self._repository.put_event(game_id, EventType.QUEST_VOTE_REQUESTED.value, team_member_ids, {},
                                           int(datetime.now().timestamp()))
        self._comm_service.broadcast(event, team_member_ids)

    def handle_quest_vote_cast(self, event: Event) -> None:
        """
        On event saves vote and broadcast player X has voted
        :param event:
        :return:
        """
        self._validate_quest_vote_cast_event(event)
        payload = event.payload
        game_id = event.game_id
        player_id = payload.get("player_id")
        is_approved = payload.get("is_approved")
        quest_number = payload.get("quest_number")
        self._repository.put_quest_vote(game_id, quest_number, player_id, is_approved)
        quest_vote_cast_event_payload = {
            "player_id": player_id,
            "quest_number": quest_number
        }
        quest_vote_cast_event = self._repository.put_event(game_id, EventType.QUEST_VOTE_CAST.value, [],
                                                           quest_vote_cast_event_payload,
                                                           int(datetime.now().timestamp()))
        self._comm_service.broadcast(quest_vote_cast_event)

    def _validate_quest_vote_cast_event(self, event: Event) -> None:
        payload = event.payload
        if not payload:
            raise ValueError("Quest vote payload is empty")
        player_id = payload.get("player_id")
        is_approved = payload.get("is_approved")
        quest_number = payload.get("quest_number")
        if not player_id or is_approved is None or not quest_number:
            raise ValueError(f"Invalid QuestVoteCast event {payload}")
        game_id = event.game_id
        player = self._repository.get_player(game_id, player_id)
        if not player:
            raise ValueError(f"Player {player_id} not found")
        quest = self._repository.get_quest(game_id, quest_number)
        if not quest or quest.result:
            raise ValueError(f"Quest not exist or completed {quest}")

    def is_quest_vote_completed(self, game_id: str, quest_number: int) -> bool:
        quest = self._repository.get_quest(game_id, quest_number)
        quest_votes = self._repository.get_quest_votes(game_id, quest_number)
        return len(quest_votes) == len(quest.team_member_ids)

    def is_quest_passed(self, game_id: str, quest_number: int) -> bool:
        quest_votes = self._repository.get_quest_votes(game_id, quest_number)
        disapprove_votes = [qv for qv in quest_votes if not qv.is_approved]

        return len(disapprove_votes) <= (0 if quest_number != 4 else 1)

    def has_majority(self, game_id: str) -> bool:
        """
        If any team has won 3 out of 5 missions
        :param game_id:
        :return:
        """
        quests = self._repository.get_quests(game_id)
        passed_quests = [q for q in quests if q.result == VotingResult.Passed]
        failed_quests = [q for q in quests if q.result == VotingResult.Failed]
        return len(passed_quests) >= 3 or len(failed_quests) >= 3

    def handle_on_enter_team_selection_state(self, game_id: str) -> None:
        current_quest = self._get_last_quest(game_id)
        if self._is_create_quest(current_quest):
            current_quest = self._create_quest(game_id)
        self._create_round(game_id, current_quest)

    @staticmethod
    def _is_create_quest(last_quest: Optional[Quest]) -> bool:
        no_quest = not last_quest
        last_quest_completed = last_quest and last_quest.result
        return no_quest or last_quest_completed

    def _create_quest(self, game_id) -> Quest:
        last_quest = self._get_last_quest(game_id)
        quest_number = 1 if not last_quest else last_quest.quest_number + 1
        event = self._create_quest_started_event(game_id, quest_number)
        quest = self._repository.put_quest(game_id, quest_number)
        self._comm_service.broadcast(event)
        return quest

    def _create_quest_started_event(self, game_id, quest_number):
        payload = {
            "game_id": game_id,
            "quest_number": quest_number,
        }
        return self._repository.put_event(game_id, EventType.QUEST_STARTED.value, [], payload,
                                          int(datetime.now().timestamp()))

    def _get_last_quest(self, game_id) -> Optional[Quest]:
        quests = self._repository.get_quests(game_id)
        sorted_quests = sorted(quests, key=lambda q: q.quest_number)
        return None if not sorted_quests else sorted_quests[-1]

    def _create_round(self, game_id: str, current_quest: Quest) -> None:
        next_leader_id = self._rotate_leader(game_id)
        self._round_service.create_round(game_id, next_leader_id, current_quest.quest_number)

    def _rotate_leader(self, game_id) -> str:
        """
        Rotates the leader to the next player
        :param game_id:
        :return: the next leader id
        """
        game = self._repository.get_game(game_id)
        player_ids = game.player_ids
        idx = player_ids.index(game.leader_id)
        next_leader_id = player_ids[(idx + 1) % len(player_ids)]
        game.leader_id = next_leader_id
        self._repository.put_game(game)
        return next_leader_id

    def set_team_member_ids(self, game_id: str, quest_number: int, team_member_ids: list[str]) -> None:
        quest = self._repository.get_quest(game_id, quest_number)
        quest.team_member_ids = team_member_ids
        self._repository.update_quest(quest)

    def set_quest_result(self, game_id: str, quest_number: int, result: VotingResult) -> Quest:
        quest = self._repository.get_quest(game_id, quest_number)
        quest.result = result
        updated_quest = self._repository.update_quest(quest)
        event = self._repository.put_event(game_id, EventType.QUEST_COMPLETED.value, [],
                                           {"quest_number": quest_number, "result": result.value},
                                           int(datetime.now().timestamp()))
        self._comm_service.broadcast(event)
        return updated_quest
