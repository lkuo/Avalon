from game_core.entities.event import Event
from game_core.event_type import EventType
from game_core.services.round_service import RoundService
from game_core.states.state import State, StateName


class RoundVotingState(State):
    """
    Transitions from LeaderAssignmentState
    Broadcast the team proposal and wait for all votes are cast.
    Transitions to LeaderAssignmentState or MissionVoting state, depends on the vote results

    """

    def __init__(self, team_selection_state: State, quest_voting_state: State, round_service: RoundService):
        super().__init__(StateName.ROUND_VOTING)
        self._team_selection_state = team_selection_state
        self._quest_voting_state = quest_voting_state
        self._round_service = round_service

    def handle(self, event: Event) -> State:
        if event.type != EventType.ROUND_VOTE_CAST:
            raise ValueError(f"RoundVotingState expects only {EventType.ROUND_VOTE_CAST.value}, got {event.type.value}")

        self._round_service.handle_round_vote_cast(event)

        game_id = event.game_id
        if not self._round_service.is_round_vote_completed(game_id):
            return self
        elif self._round_service.is_proposal_passed(game_id):
            return self._quest_voting_state
        else:
            return self._team_selection_state

    def on_enter(self, game_id: str) -> None:
        self._round_service.on_enter_round_voting_state(game_id)

    def on_exit(self, game_id: str) -> None:
        self._round_service.on_exit_round_voting_state(game_id)
