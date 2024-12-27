from typing import Optional

from game_core.constants.action_type import ActionType
from game_core.constants.state_name import StateName
from game_core.constants.vote_result import VoteResult
from game_core.entities.action import Action
from game_core.services.quest_service import QuestService
from game_core.services.round_service import RoundService
from game_core.states.state import State


class TeamSelectionState(State):
    """
    Transitions from GameSetupState, RoundVotingState, QuestVotingState
    Broadcast the leader is choosing a team, collect all votes then broadcast proposal
    Transitions to RoundVoting State
    """

    def __init__(self, quest_service: QuestService, round_service: RoundService):
        super().__init__(StateName.TeamSelection)
        self._round_voting_state = None
        self._end_game_state = None
        self._quest_service = quest_service
        self._round_service = round_service

    def set_states(self, round_voting_state: State, end_game_state: State) -> None:
        self._round_voting_state = round_voting_state
        self._end_game_state = end_game_state

    def handle(self, action: Action) -> State:
        if action.type != ActionType.SubmitTeamProposal:
            raise ValueError(
                f"TeamSelectionState expects only SubmitTeamProposal, got {action.type.value}"
            )

        self._round_service.handle_submit_team_proposal(action)

        return self._round_voting_state

    def on_enter(self, game_id: str) -> Optional[State]:
        """
        Verifies the previous state, then creates a round ana a quest if needed.
        Rotates the leader
        :param game_id:
        :return:
        """
        if self._quest_service.is_final_proposal_failed(game_id):
            self._quest_service.complete_current_quest(game_id, VoteResult.Fail)
        if self._quest_service.has_majority(game_id):
            return self._end_game_state
        self._quest_service.handle_on_enter_team_selection_state(game_id)
