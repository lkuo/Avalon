from game_core.constants.vote_result import VoteResult
from game_core.entities.event import Event
from game_core.constants.event_type import EventType
from game_core.services.quest_service import QuestService
from game_core.states.state import State
from game_core.constants.state_name import StateName


class QuestVotingState(State):
    """
    Transitions from RoundVotingState
    Broadcast the quest voting has started and notify the team members.
    Wait until all quest votes are collected then broadcast the results.
    Transitions to LeaderAssignmentState or GameEndState based on if a team has won the majority of quests.
    """

    def __init__(self, team_selection_state: State, end_game_state: State, quest_service: QuestService):
        super().__init__(StateName.QuestVoting)
        self._team_selection_state = team_selection_state
        self._end_game_state = end_game_state
        self._quest_service = quest_service

    def handle(self, event: Event) -> State:
        if event.type != EventType.QuestVoteCast:
            raise ValueError(f"QuestVotingState expects only {EventType.QuestVoteCast.value}, got {event.type.value}")

        # todo: handle the updating quest result in the quest service
        self._quest_service.handle_quest_vote_cast(event)
        quest_number = event.payload.get("quest_number")
        if not self._quest_service.is_quest_vote_completed(event.game_id, quest_number):
            return self

        # move this to handle_quest_vote_cast method
        voting_result = VoteResult.Approved if self._quest_service.is_quest_passed(
            event.game_id, quest_number) else VoteResult.Rejected
        self._quest_service.set_quest_result(event.game_id, quest_number, voting_result)
        if self._quest_service.has_majority(event.game_id):
            return self._end_game_state
        else:
            return self._team_selection_state

    def on_enter(self, game_id: str) -> None:
        self._quest_service.on_enter_quest_voting_state(game_id)


    # on exit announce the result of the quest voting
