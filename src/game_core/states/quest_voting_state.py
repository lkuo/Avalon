from typing import Self

from game_core.entities.event import Event
from game_core.event_type import EventType
from game_core.services.mission_service import QuestService
from game_core.states.state import State, StateName


class QuestVotingState(State):
    """
    Transitions from RoundVotingState
    Broadcast the quest voting has started and notify the team members.
    Wait until all quest votes are collected then broadcast the results.
    Transitions to LeaderAssignmentState or GameEndState based on if a team has won the majority of quests.
    """

    def __init__(self, leader_assignment_state: State, game_end_state: State, quest_service: QuestService):
        super().__init__(StateName.QUEST_VOTING)
        self._leader_assignment_state = leader_assignment_state
        self._game_end_state = game_end_state
        self._quest_service = quest_service

    def handle(self, event: Event) -> State:
        if event.type != EventType.QUEST_VOTE_CAST:
            raise ValueError(f"QuestVotingState expects only {EventType.QUEST_VOTE_CAST.value}, got {event.type.value}")

        self._quest_service.handle_quest_vote_cast(event)
        if not self._quest_service.is_quest_vote_completed(event.game_id):
            return self
        elif self._quest_service.has_won_majority(event.game_id):
            return self._game_end_state
        else:
            return self._leader_assignment_state

    def on_enter(self, game_id: str) -> None:
        self._quest_service.on_enter_quest_voting_state(game_id)

    def on_exit(self, game_id: str) -> None:
        self._quest_service.on_exit_quest_voting_state(game_id)
