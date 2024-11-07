from game_core.entities.event import Event
from game_core.event_type import EventType
from game_core.services.mission_service import QuestService
from game_core.services.round_service import RoundService
from game_core.states.state import State, StateName


class LeaderAssignmentState(State):
    """
    Handles GAME_STARTED, QUESTION_COMPLETED, TEAM_REJECTED events.
    Transitions from GameSetup, RoundVoting and QuestVoting states.
    Transitions to RoundVoting state.
    On exit, start a mission if needed, then start a round.
    """
    EXPECTED_EVENT_TYPES = [EventType.GAME_STARTED, EventType.QUEST_COMPLETED, EventType.TEAM_REJECTED]

    def __init__(self, team_selection_state: State, mission_service: QuestService, round_service: RoundService):
        super().__init__(StateName.LEADER_ASSIGNMENT)
        self._team_selection_state = team_selection_state
        self._mission_service = mission_service
        self._round_service = round_service

    def handle(self, event: Event) -> State:
        if event.type not in self.EXPECTED_EVENT_TYPES:
            raise ValueError(f"LeaderAssignmentState expects {self.EXPECTED_EVENT_TYPES} got {event.type.value}")

        if event.type in [EventType.GAME_STARTED, EventType.QUEST_COMPLETED]:
            self._mission_service.start_mission(event.game_id)
        self._round_service.start_round(event.game_id)

        return self._team_selection_state
