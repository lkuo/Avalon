from game_core.constants.action_type import ActionType
from game_core.constants.state_name import StateName
from game_core.constants.vote_result import VoteResult
from game_core.entities.action import Action
from game_core.services.round_service import RoundService
from game_core.states.state import State


class RoundVotingState(State):
    """
    Transitions from LeaderAssignmentState
    Broadcast the team proposal and wait for all votes are cast.
    Transitions to LeaderAssignmentState or MissionVoting state, depends on the vote results

    """

    def __init__(self, round_service: RoundService):
        super().__init__(StateName.RoundVoting)
        self._team_selection_state = None
        self._quest_voting_state = None
        self._round_service = round_service

    def set_states(
        self, team_selection_state: State, quest_voting_state: State
    ) -> None:
        self._team_selection_state = team_selection_state
        self._quest_voting_state = quest_voting_state

    def handle(self, action: Action) -> State:
        if action.type != ActionType.CastRoundVote:
            raise ValueError(
                f"RoundVotingState expects only {ActionType.CastRoundVote}, got {action.type.value}"
            )

        self._round_service.handle_cast_round_vote(action)

        current_round = self._round_service.get_current_round(action.game_id)
        if not current_round.result:
            return self
        elif current_round.result == VoteResult.Pass:
            return self._quest_voting_state
        else:
            return self._team_selection_state
