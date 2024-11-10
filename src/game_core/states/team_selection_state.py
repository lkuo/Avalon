from game_core.entities.event import Event
from game_core.constants.event_type import EventType
from game_core.services.quest_service import QuestService
from game_core.services.round_service import RoundService
from game_core.states.state import State
from game_core.constants.state_name import StateName


class TeamSelectionState(State):
    """
    Transitions from LeaderAssignmentState
    Broadcast the leader is choosing a team, collect all votes then broadcast proposal
    Transitions to RoundVoting State
    """

    def __init__(self, round_voting_state: State, quest_service: QuestService, round_service: RoundService):
        super().__init__(StateName.TEAM_SELECTION)
        self._round_voting_state = round_voting_state
        self._quest_service = quest_service
        self._round_service = round_service

    def handle(self, event: Event) -> State:
        if event.type != EventType.TEAM_PROPOSAL_SUBMITTED:
            raise ValueError(f"TeamSelectionState expects only TEAM_PROPOSAL_SUBMITTED, got {event.type.value}")

        self._round_service.handle_team_proposal_submitted(event)

        return self._round_voting_state

    def on_enter(self, game_id: str) -> None:
        self._quest_service.handle_on_enter_team_selection_state(game_id)
