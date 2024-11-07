from game_core.entities.event import Event
from game_core.event_type import EventType
from game_core.services.round_service import RoundService
from game_core.states.state import State, StateName


class TeamSelectionState(State):
    """
    Transitions from LeaderAssignmentState
    Broadcast the leader is choosing a team, collect all votes then broadcast proposal
    Transitions to RoundVoting State
    """

    def __init__(self, round_voting_state: State, round_service: RoundService):
        super().__init__(StateName.TEAM_SELECTION)
        self._round_voting_state = round_voting_state
        self._round_service = round_service

    def handle(self, event: Event) -> State:
        if event.type != EventType.TEAM_PROPOSAL_SUBMITTED:
            raise ValueError(f"TeamSelectionState expects only TEAM_PROPOSAL_SUBMITTED, got {event.type.value}")

        self._round_service.handle_team_proposal_submitted(event.game_id)

        return self._round_voting_state

    def on_enter(self, game_id: str) -> None:
        # notify the team leader to submit a team proposal
        self._round_service.notify_submit_team_proposal(game_id)
