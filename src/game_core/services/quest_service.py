from datetime import datetime
from typing import Optional, Tuple

from game_core.constants.event_type import EventType
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

    def on_enter_quest_voting_state(self, game_id) -> None:
        """
        On enter broadcast quest voting started by team members, and notify team members to cast vote
        On event saves vote and broadcast player X has voted
        On exit broadcast the quest voting result and updates mission
        :param game_id:
        :return:
        """
        pass

    def on_exit_quest_voting_state(self, game_id) -> None:
        pass

    def handle_quest_vote_cast(self, event: Event) -> None:
        pass

    def is_quest_vote_completed(self, game_id):
        pass

    def is_mission_passed(self, game_id):
        pass

    def has_won_majority(self, game_id) -> bool:
        """
        If any team has won 3 out of 5 missions
        :param game_id:
        :return:
        """
        pass

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
