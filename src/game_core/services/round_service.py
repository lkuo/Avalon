from typing import Optional

from pydantic import BaseModel

from game_core.constants.vote_result import VoteResult
from game_core.entities.action import Action
from game_core.entities.round import Round
from game_core.repository import Repository
from game_core.services.event_service import EventService


class RoundService:
    def __init__(
        self,
        event_service: EventService,
        repository: Repository,
    ):
        self._event_service = event_service
        self._repository = repository

    def handle_submit_team_proposal(self, action: Action) -> None:
        """
        Validates the team proposal which the leader submitted. Saves the proposal then broadcast the event.
        :param action:
        :return:
        """
        SubmitTeamProposalPayload(**action.payload)
        quest_number = action.payload["quest_number"]
        round_number = action.payload["round_number"]
        team_member_ids = action.payload["team_member_ids"]
        game_id = action.game_id
        self._validate_team_proposal_submitted_action(action)
        game_round = self._repository.get_round(game_id, quest_number, round_number)
        game_round.team_member_ids = team_member_ids
        self._repository.update_round(game_round)
        self._event_service.create_team_proposal_submitted_event(
            game_id, quest_number, round_number, team_member_ids
        )

    def _validate_team_proposal_submitted_action(self, action: Action) -> None:
        game_id = action.game_id
        quest_number = action.payload.get("quest_number")
        team_member_ids = action.payload.get("team_member_ids", [])
        game = self._repository.get_game(game_id)
        quest_team_size = game.config.quest_team_size[quest_number]
        if len(team_member_ids) != quest_team_size:
            raise ValueError(
                f"Team proposal must have {quest_team_size} members, got {team_member_ids}"
            )
        players = self._repository.get_players(game_id)
        player_ids = set([p.id for p in players])
        if any([m_id not in player_ids for m_id in team_member_ids]):
            raise ValueError("Team proposal contains invalid player ids")

    def handle_cast_round_vote(self, action: Action) -> None:
        """
        On event, broadcast player has voted then save the vote
        On exit, broadcast the results - players and their votes
        :param action:
        :return:
        """
        VoteRoundPayload(**action.payload)
        self._validate_round_vote_cast_action(action)
        payload = action.payload
        game_id = action.game_id
        player_id = payload["player_id"]
        result = VoteResult.Pass if payload["is_approved"] else VoteResult.Fail
        quest_number = payload["quest_number"]
        round_number = payload["round_number"]
        self._repository.put_round_vote(
            game_id, quest_number, round_number, player_id, result
        )
        self._event_service.create_round_vote_cast_event(
            game_id, quest_number, round_number, player_id, result
        )

        if not self.is_round_vote_completed(game_id, quest_number, round_number):
            return

        is_proposal_passed = self.is_proposal_passed(
            game_id, quest_number, round_number
        )
        round_result = VoteResult.Pass if is_proposal_passed else VoteResult.Fail
        game_round = self._repository.get_round(game_id, quest_number, round_number)
        game_round.result = round_result
        self._repository.update_round(game_round)
        self._event_service.create_round_completed_event(
            game_id, quest_number, round_number, round_result
        )

    def _validate_round_vote_cast_action(self, action: Action) -> None:
        payload = action.payload
        player_id = payload["player_id"]
        quest_number = payload["quest_number"]
        round_number = payload["round_number"]
        game_id = action.game_id
        player = self._repository.get_player(player_id)
        if not player:
            raise ValueError(f"Player {player_id} not found")
        quest = self._repository.get_quest(game_id, quest_number)
        if not quest:
            raise ValueError(f"Quest not exist or completed{quest}")
        if quest.result:
            raise ValueError(f"Quest {quest_number} already completed {quest}")
        game_round = self._repository.get_round(game_id, quest_number, round_number)
        if not game_round:
            raise ValueError(f"Round not exist {game_round}")
        if game_round.result:
            raise ValueError(f"Round {round_number} already completed {game_round}")
        round_vote = self._repository.get_round_vote(
            game_id, quest_number, round_number, player_id
        )
        if round_vote:
            raise ValueError(
                f"Player {player_id} already voted for quest {quest_number} round {round_number}"
            )

    def is_round_vote_completed(
        self, game_id: str, quest_number: int, round_number: int
    ) -> bool:
        players = self._repository.get_players(game_id)
        round_votes = self._repository.get_round_votes(
            game_id, quest_number, round_number
        )
        return len(players) == len(round_votes)

    def is_proposal_passed(
        self, game_id: str, quest_number: int, round_number: int
    ) -> bool:
        round_votes = self._repository.get_round_votes(
            game_id, quest_number, round_number
        )
        approved_votes = [rv for rv in round_votes if rv.result == VoteResult.Pass]
        return len(approved_votes) > len(round_votes) / 2

    def create_round(self, game_id: str, quest_number: int) -> Round:
        current_round = self.get_current_round(game_id)
        round_number = 1 if not current_round else current_round.round_number + 1
        leader_id = self._rotate_leader(game_id)
        next_round = self._repository.put_round(
            game_id, quest_number, round_number, leader_id
        )
        self._event_service.create_round_started_event(
            game_id, quest_number, round_number, leader_id
        )
        game = self._repository.get_game(game_id)
        number_of_players = game.config.quest_team_size[quest_number]
        self._event_service.create_team_selection_requested_event(
            game_id, quest_number, round_number, number_of_players
        )
        return next_round

    def get_current_round(self, game_id: str) -> Optional[Round]:
        rounds = self._repository.get_rounds(game_id)
        rounds = sorted(rounds, key=lambda r: (r.quest_number, r.round_number))
        return rounds[-1] if rounds else None

    def _rotate_leader(self, game_id) -> str:
        """
        Rotates the leader to the next player
        :param game_id:
        :return: the next leader id
        """
        game = self._repository.get_game(game_id)
        player_ids = game.player_ids
        idx = player_ids.index(game.leader_id)
        next_leader_id = player_ids[(idx + 1) % len(player_ids)]
        game.leader_id = next_leader_id
        self._repository.update_game(game)
        return next_leader_id


class SubmitTeamProposalPayload(BaseModel):
    quest_number: int
    round_number: int
    team_member_ids: list[str]


class VoteRoundPayload(BaseModel):
    player_id: str
    is_approved: bool
    quest_number: int
    round_number: int
