from datetime import datetime

from game_core.constants.event_type import EventType
from game_core.constants.voting_result import VotingResult
from game_core.entities.event import Event
from game_core.entities.round import Round
from game_core.repository import Repository
from game_core.services.comm_service import CommService


class RoundService:

    def __init__(self, repository: Repository, comm_service: CommService):
        self._repository = repository
        self._comm_service = comm_service

    def handle_team_proposal_submitted(self, event: Event) -> None:
        """
        Validates the team proposal which the leader submitted. Saves the proposal then broadcast the event.
        :param event:
        :return:
        """
        self._validate_team_proposal_submitted_event(event)
        team_member_ids = event.payload["team_member_ids"]
        quest_number = event.payload["quest_number"]
        round_number = event.payload["round_number"]
        payload = {
            "quest_number": quest_number,
            "round_number": round_number,
            "team_member_ids": team_member_ids
        }
        game_id = event.game_id
        game_round = self._repository.get_round(game_id, quest_number, round_number)
        game_round.team_member_ids = team_member_ids
        self._repository.update_round(game_round)
        event = self._repository.put_event(game_id, EventType.TeamProposalSubmitted.value, [],
                                           payload, int(datetime.now().timestamp()))
        self._comm_service.broadcast(event)

    def _validate_team_proposal_submitted_event(self, event) -> None:
        game_id = event.game_id
        payload = event.payload
        if not payload:
            raise ValueError("Team proposal is empty")
        quest_number = payload.get("quest_number")
        round_number = payload.get("round_number")
        if not quest_number or not round_number:
            raise ValueError("quest_number or round_number are required")
        team_member_ids = payload.get("team_member_ids", [])
        game = self._repository.get_game(game_id)
        quest_team_size = game.config.quest_team_size[quest_number]
        if len(team_member_ids) != quest_team_size:
            raise ValueError(f"Team proposal must have {quest_team_size} members, got {team_member_ids}")
        players = self._repository.get_players(game_id)
        player_ids = set([p.id for p in players])
        if any([m_id not in player_ids for m_id in team_member_ids]):
            raise ValueError("Team proposal contains invalid player ids")

    def on_enter_round_voting_state(self, game_id) -> None:
        pass

    def handle_round_vote_cast(self, event: Event) -> None:
        """
        On event, broadcast player has voted then save the vote
        On exit, broadcast the results - players and their votes
        :param event:
        :return:
        """
        self._validate_round_vote_cast_event(event)
        payload = event.payload
        player_id = payload.get("player_id")
        is_approved = payload.get("is_approved")
        quest_number = payload.get("quest_number")
        round_number = payload.get("round_number")
        self._repository.put_round_vote(event.game_id, quest_number, round_number, player_id, is_approved)
        round_vote_cast_event_payload = {
            "player_id": player_id,
            "quest_number": quest_number,
            "round_number": round_number
        }
        round_vote_cast_event = Event(event.game_id, EventType.RoundVoteCast.value, [], round_vote_cast_event_payload)
        self._comm_service.broadcast(round_vote_cast_event)

    def _validate_round_vote_cast_event(self, event):
        payload = event.payload
        if not payload:
            raise ValueError("Round vote payload is empty")
        player_id = payload.get("player_id")
        is_approved = payload.get("is_approved")
        quest_number = payload.get("quest_number")
        round_number = payload.get("round_number")
        if not player_id or is_approved is None or not quest_number or not round_number:
            raise ValueError(f"Invalid RoundVoteCast event {payload}")
        game_id = event.game_id
        player = self._repository.get_player(game_id, player_id)
        if not player:
            raise ValueError(f"Player {player_id} not found")
        quest = self._repository.get_quest(game_id, quest_number)
        if not quest or quest.result:
            raise ValueError(f"Quest not exist or completed {quest}")
        game_round = self._repository.get_round(game_id, quest_number, round_number)
        if not game_round or game_round.result:
            raise ValueError(f"Round not exist or completed {game_round}")
        round_vote = self._repository.get_round_vote(game_id, quest_number, round_number, player_id)
        if round_vote:
            raise ValueError(f"Player {player_id} already voted for quest {quest_number} round {round_number}")

    def is_round_vote_completed(self, game_id: str, quest_number: int, round_number: int) -> bool:
        players = self._repository.get_players(game_id)
        round_votes = self._repository.get_round_votes(game_id, quest_number, round_number)
        return len(players) == len(round_votes)

    def is_proposal_passed(self, game_id: str, quest_number: int, round_number: int) -> bool:
        round_votes = self._repository.get_round_votes(game_id, quest_number, round_number)
        approved_votes = [rv for rv in round_votes if rv.is_approved]
        return len(approved_votes) > len(round_votes) / 2

    def on_exit_round_voting_state(self, game_id):
        pass

    def create_round(self, game_id: str, leader_id: str, quest_number: int) -> Round:
        rounds = self._repository.get_rounds_by_quest(game_id, quest_number)
        rounds = sorted(rounds, key=lambda r: r.round_number)
        round_number = 1 if not rounds else rounds[-1].round_number + 1
        current_round = self._repository.put_round(game_id, quest_number, round_number, leader_id)
        event = self._repository.put_event(game_id, EventType.RoundStarted.value, [],
                                           {"quest_number": quest_number, "round_number": round_number,
                                            "leader_id": leader_id},
                                           int(datetime.now().timestamp()))
        self._comm_service.broadcast(event)
        game = self._repository.get_game(game_id)
        number_of_players = game.config.quest_team_size[quest_number]
        select_team_event = self._repository.put_event(game_id, EventType.SelectTeam.value, [leader_id],
                                                       {"quest_number": quest_number, "round_number": round_number,
                                                        "number_of_players": number_of_players},
                                                       int(datetime.now().timestamp()))
        self._comm_service.notify(leader_id, select_team_event)
        return current_round

    def set_round_result(self, game_id: str, quest_number: int, round_number: int, result: VotingResult) -> Round:
        game_round = self._repository.get_round(game_id, quest_number, round_number)
        game_round.result = result
        updated_game_round = self._repository.update_round(game_round)

        round_votes = self._repository.get_round_votes(game_id, quest_number, round_number)
        votes = {rv.player_id: rv.is_approved for rv in round_votes}
        event = self._repository.put_event(game_id, EventType.RoundCompleted.value, [],
                                           {"quest_number": quest_number, "round_number": round_number,
                                            "result": result.value, "votes": votes},
                                           int(datetime.now().timestamp()))
        self._comm_service.broadcast(event)
        return updated_game_round
