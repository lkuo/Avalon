from pydantic import BaseModel

from game_core.constants.action_type import ActionType
from game_core.constants.state_name import StateName
from game_core.constants.vote_result import VoteResult
from game_core.entities.action import Action
from game_core.services.event_service import EventService
from game_core.services.game_service import GameService
from game_core.services.quest_service import QuestService
from game_core.services.round_service import RoundService
from game_core.states.state import State, InvalidActionTypeException, InvalidInputException


class RoundVotingState(State):
    """
    Transitions from LeaderAssignmentState
    Broadcast the team proposal and wait for all votes are cast.
    Transitions to LeaderAssignmentState or MissionVoting state, depends on the vote results

    """

    def __init__(
            self,
            game_service: GameService,
            quest_service: QuestService,
            round_service: RoundService,
            event_service: EventService):
        super().__init__(StateName.RoundVoting)
        self._game_service = game_service
        self._quest_service = quest_service
        self._round_service = round_service
        self._event_service = event_service

    def handle(self, action: Action) -> None:
        if action.type != ActionType.CastRoundVote:
            raise InvalidActionTypeException([ActionType.CastRoundVote], action.type)
        payload = VoteRoundPayload(**action.payload)
        current_round = self._round_service.get_current_round(action.game_id)
        round_votes = self._round_service.get_round_votes(
            action.game_id,
            current_round.quest_number,
            current_round.round_number
        )
        if any([payload.player_id == round_vote.player_id for round_vote in round_votes]):
            raise InvalidInputException("Player has already voted")

        game = self._game_service.get_game(action.game_id)
        vote_result = VoteResult.Pass if payload.is_approved else VoteResult.Fail
        self._round_service.create_round_vote(
            action.game_id,
            current_round.quest_number,
            current_round.round_number,
            payload.player_id,
            vote_result
        )
        self._event_service.create_round_vote_cast_event(
            action.game_id,
            current_round.quest_number,
            current_round.round_number,
            payload.player_id
        )
        if len(round_votes) + 1 < len(game.player_ids):
            return

        round_votes = self._round_service.get_round_votes(
            action.game_id,
            current_round.quest_number,
            current_round.round_number
        )
        player_votes = {rv.player_id: rv.result.value for rv in round_votes}
        approved_votes = [rv for rv in round_votes if rv.result == VoteResult.Pass]
        is_proposal_passed = len(approved_votes) > len(round_votes) / 2
        current_round.result = VoteResult.Pass if is_proposal_passed else VoteResult.Fail
        self._round_service.update_round(current_round)
        self._event_service.create_round_completed_event(
            action.game_id,
            current_round.quest_number,
            current_round.round_number,
            player_votes,
            current_round.result
        )
        rounds = self._round_service.get_quest_rounds(action.game_id, current_round.quest_number)
        if current_round.result == VoteResult.Pass or len(rounds) == 5:
            game.state = StateName.QuestVoting.value
            current_quest = self._quest_service.get_current_quest(action.game_id)
            current_quest.team_member_ids = current_round.team_member_ids
            self._quest_service.update_quest(current_quest)
            self._event_service.create_quest_vote_started_event(
                action.game_id,
                current_round.quest_number,
                current_round.team_member_ids
            )
            self._event_service.create_quest_vote_requested_event(
                action.game_id,
                current_round.quest_number,
                current_round.team_member_ids
            )
        else:
            game.state = StateName.TeamSelection.value
            game_round = self._round_service.create_round(game, current_round.quest_number)
            self._event_service.create_team_selection_requested_event(
                action.game_id,
                game_round.leader_id,
                game_round.quest_number,
                game_round.round_number,
                game.quest_team_size[game_round.quest_number]
            )
        self._game_service.update_game(game)


class VoteRoundPayload(BaseModel):
    player_id: str
    is_approved: bool
