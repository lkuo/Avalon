from pydantic import BaseModel

from game_core.constants.action_type import ActionType
from game_core.constants.state_name import StateName
from game_core.entities.action import Action
from game_core.services.event_service import EventService
from game_core.services.game_service import GameService
from game_core.services.player_service import PlayerService
from game_core.services.round_service import RoundService
from game_core.states.state import State, InvalidActionTypeException, InvalidInputException


class TeamSelectionState(State):
    """
    Transitions from GameSetupState, RoundVotingState, QuestVotingState
    Broadcast the leader is choosing a team, collect all votes then broadcast proposal
    Transitions to RoundVoting State
    """

    def __init__(self, game_service: GameService, player_service: PlayerService, round_service: RoundService,
                 event_service: EventService):
        super().__init__(StateName.TeamSelection)
        self._game_service = game_service
        self._player_service = player_service
        self._round_service = round_service
        self._event_service = event_service

    def handle(self, action: Action) -> None:
        if action.type != ActionType.SubmitTeamProposal:
            raise InvalidActionTypeException([ActionType.SubmitTeamProposal], action.type)

        game_id = action.game_id
        payload = SubmitTeamProposalPayload(**action.payload)
        game = self._game_service.get_game(game_id)
        game_round = self._round_service.get_current_round(game_id)
        team_size = game.quest_team_size[game_round.quest_number]
        if len(payload.team_member_ids) != team_size:
            raise InvalidInputException("")
        players = self._player_service.get_players(game_id)
        player_ids = set([p.id for p in players])
        if any([tm_id not in player_ids for tm_id in payload.team_member_ids]):
            raise InvalidInputException("invalid team_member_ids")
        game_round = self._round_service.get_current_round(game_id)
        game_round.team_member_ids = payload.team_member_ids
        self._round_service.update_round(game_round)
        game.state = StateName.RoundVoting
        self._game_service.update_game(game)
        self._event_service.create_team_proposal_submitted_event(game_id, game_round.quest_number,
                                                                 game_round.round_number, payload.team_member_ids)


class SubmitTeamProposalPayload(BaseModel):
    team_member_ids: list[str]
