from game_core.entities.event import Event
from game_core.event_type import EventType
from game_core.services.round_service import RoundService
from game_core.states.state import State, StateName


class TeamSelectionState(State):
    """
    Handles TEAM_PROPOSAL_SUBMITTED event
    Transitions from LeaderAssignmentState
    Transitions to RoundVoting State
    On enter, notify the team leader to submit a team proposal
    """

    def __init__(self, round_voting: State, round_service: RoundService):
        super().__init__(StateName.TEAM_SELECTION)
        self._round_voting = round_voting
        self._round_service = round_service

    def handle(self, event: Event) -> State:
        if event.type != EventType.TEAM_PROPOSAL_SUBMITTED:
            raise ValueError(f"TeamSelectionState expects only TEAM_PROPOSAL_SUBMITTED, got {event.type.value}")

        self._round_service.broadcast_team_proposal(event.game_id)

        return self._round_voting

    def on_enter(self, game_id: str) -> None:
        # notify the team leader to submit a team proposal
        self._round_service.notify_submit_team_proposal(game_id)
