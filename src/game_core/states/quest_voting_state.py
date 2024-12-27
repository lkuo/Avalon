from game_core.constants.action_type import ActionType
from game_core.constants.state_name import StateName
from game_core.entities.action import Action
from game_core.services.quest_service import QuestService
from game_core.states.state import State


class QuestVotingState(State):
    """
    Transitions from RoundVotingState
    Broadcast the quest voting has started and notify the team members.
    Wait until all quest votes are collected then broadcast the results.
    Transitions to LeaderAssignmentState or GameEndState based on if a team has won the majority of quests.
    """

    def __init__(
        self,
        quest_service: QuestService,
    ):
        super().__init__(StateName.QuestVoting)
        self._team_selection_state = None
        self._end_game_state = None
        self._quest_service = quest_service

    def set_states(self, team_selection_state: State, end_game_state: State) -> None:
        self._team_selection_state = team_selection_state
        self._end_game_state = end_game_state

    def handle(self, action: Action) -> State:
        if action.type != ActionType.CastQuestVote:
            raise ValueError(
                f"QuestVotingState expects only {ActionType.CastQuestVote.value}, got {action.type.value}"
            )
        self._quest_service.handle_cast_quest_vote(action)
        quest_number = action.payload.get("quest_number")
        if not self._quest_service.is_quest_vote_completed(
            action.game_id, quest_number
        ):
            return self
        elif self._quest_service.has_majority(action.game_id):
            return self._end_game_state
        else:
            return self._team_selection_state

    def on_enter(self, game_id: str) -> None:
        self._quest_service.on_enter_quest_voting_state(game_id)
