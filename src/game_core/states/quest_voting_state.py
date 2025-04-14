from pydantic import BaseModel

from game_core.constants.action_type import ActionType
from game_core.constants.game_status import GameStatus
from game_core.constants.role import Role
from game_core.constants.state_name import StateName
from game_core.constants.vote_result import VoteResult
from game_core.entities.action import Action
from game_core.services.event_service import EventService
from game_core.services.game_service import GameService
from game_core.services.player_service import PlayerService
from game_core.services.quest_service import QuestService
from game_core.services.round_service import RoundService
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
            game_service: GameService,
            player_service: PlayerService,
            quest_service: QuestService,
            round_service: RoundService,
            event_service: EventService,
    ):
        super().__init__(StateName.QuestVoting)
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
        num_fail_votes = len([qv for qv in quest_votes if qv.result == VoteResult.Fail])
        is_fail = num_fail_votes > 0 or (current_quest.quest_number == 4 and num_fail_votes > 1)
        current_quest.result = VoteResult.Fail if is_fail else VoteResult.Pass
        self._quest_service.update_quest(current_quest)
        self._event_service.create_quest_completed_event(
            action.game_id,
            current_quest.quest_number,
            current_quest.result
        )
        quests = self._quest_service.get_quests(action.game_id)
        passed_quests = [q for q in quests if q.result == VoteResult.Pass]
        failed_quests = [q for q in quests if q.result == VoteResult.Fail]
        is_game = len(passed_quests) >= 3 or len(failed_quests) >= 3
        game = self._game_service.get_game(action.game_id)
        if not is_game:
            quest = self._quest_service.create_quest(action.game_id)
            game_round = self._round_service.create_round(game, quest.quest_number)
            number_of_players = game.quest_team_size[quest.quest_number]
            game.state = StateName.TeamSelection
            self._game_service.update_game(game)
            self._event_service.create_team_selection_requested_event(
                action.game_id,
                game_round.leader_id,
                quest.quest_number,
                game_round.round_number,
                number_of_players
            )
            return

        players = self._player_service.get_players(action.game_id)
        if game.assassination_attempts:
            game.state = StateName.EndGame
            self._game_service.update_game(game)
            assassin = [p for p in players if p.role == Role.Assassin][0]
            self._event_service.create_assassination_started_event(action.game_id, game.assassination_attempts)
            self._event_service.create_assassination_target_requested_event(action.game_id, assassin.id)
            return

        game.status = GameStatus.Finished
        self._game_service.update_game(game)
        player_roles = {player.id: player.role.value for player in players}
        self._event_service.create_game_ended_event(action.game_id, player_roles)


class CastQuestVotePayload(BaseModel):
    player_id: str
    is_approved: bool
    quest_number: int
