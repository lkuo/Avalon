from typing import Self

from game_core.entities.event import Event
from game_core.event_type import EventType
from game_core.services.mission_service import MissionService
from game_core.states.state import State, StateName


class QuestVotingState(State):
    """
    Handles QUEST_VOTE_CASTED event
    Transitions from RoundVotingState
    Transitions to LeaderAssignmentState or GameEndState
    On enter broadcast quest voting started by team members, and notify team members to cast vote
    On event saves vote and broadcast player X has voted
    On exit broadcast the quest voting result and updates mission
    """

    def __init__(self, leader_assignment_state: State, game_end_state: State, mission_service: MissionService):
        super().__init__(StateName.QUEST_VOTING)
        self._leader_assignment_state = leader_assignment_state
        self._game_end_state = game_end_state
        self._mission_service = mission_service

    def handle(self, event: Event) -> State:
        if event.type != EventType.QUEST_VOTE_CASTED:
            raise ValueError(f"QuestVotingState expects only QUEST_VOTE_CASTED, got {event.type.value}")

        # TODO replace this naive validation with a package and be more strict
        payload = event.payload
        if payload is None or not payload.get("mission_number") or not payload.get("player_id") or payload.get(
                "vote") is None:
            raise ValueError(
                f"Invalid event, expects payload to have mission_number, player_id and vote keys, got {payload}")
        payload = event.payload
        mission_number = payload["mission_number"]
        player_id = payload["player_id"]
        vote = payload["vote"]

        self._mission_service.save_mission_vote(event.game_id, mission_number, player_id, vote)
        if not self._mission_service.is_mission_voted(event.game_id):
            return self

        missions_completed = self._mission_service.is_missions_completed(event.game_id)
        return self._game_end_state if missions_completed else self._leader_assignment_state

    def on_enter(self, game_id: str) -> None:
        self._mission_service.broadcast_quest_vote_started(game_id)
        self._mission_service.notify_cast_quest_vote(game_id)

    def on_exit(self, game_id: str) -> None:
        self._mission_service.broadcast_quest_vote_result(game_id)
