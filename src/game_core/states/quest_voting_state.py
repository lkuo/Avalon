from pydantic import BaseModel

from game_core.constants.action_type import ActionType
from game_core.constants.state_name import StateName
from game_core.entities.action import Action
from game_core.services.event_service import EventService
from game_core.services.game_service import GameService
from game_core.services.player_service import PlayerService
from game_core.services.quest_service import QuestService
from game_core.services.round_service import RoundService
from game_core.services.state_service import StateService
from game_core.states.state import State, InvalidActionTypeException, InvalidInputException


class QuestVotingState(State):
    """
    Transitions from RoundVotingState
    Broadcast the quest voting has started and notify the team members.
    Wait until all quest votes are collected then broadcast the results.
    Transitions to LeaderAssignmentState or GameEndState based on if a team has won the majority of quests.
    """

    def __init__(
            self,
            state_service: StateService,
            game_service: GameService,
            player_service: PlayerService,
            quest_service: QuestService,
            round_service: RoundService,
            event_service: EventService,
    ):
        super().__init__(StateName.QuestVoting)
        self._state_service = state_service
        self._game_service = game_service
        self._player_service = player_service
        self._quest_service = quest_service
        self._round_service = round_service
        self._event_service = event_service

    def handle(self, action: Action) -> None:
        if action.type != ActionType.CastQuestVote:
            raise InvalidActionTypeException([ActionType.CastQuestVote], action.type)
        payload = CastQuestVotePayload(**action.payload)
        current_quest = self._quest_service.get_current_quest(action.game_id)
        if current_quest.result:
            raise InvalidInputException("Quest already finished")
        if current_quest.quest_number != payload.quest_number:
            raise InvalidInputException(
                f"Invalid quest number, expect {current_quest.quest_number}, got {payload.quest_number}")
        if payload.player_id not in current_quest.team_member_ids:
            raise InvalidInputException(f"Player {payload.player_id} is not in the team")

        self._quest_service.create_quest_vote(
            action.game_id,
            payload.quest_number,
            payload.player_id,
            payload.is_approved,
        )
        self._event_service.create_quest_vote_cast_event(
            action.game_id,
            payload.quest_number,
            payload.player_id
        )
        quest_votes = self._quest_service.get_quest_votes(
            action.game_id,
            payload.quest_number
        )
        if len(quest_votes) < len(current_quest.team_member_ids):
            return
        self._state_service.end_quest(action.game_id)
        return


class CastQuestVotePayload(BaseModel):
    player_id: str
    is_approved: bool
    quest_number: int
