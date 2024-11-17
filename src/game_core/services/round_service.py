from datetime import datetime

from game_core.constants.event_type import EventType
from game_core.entities.event import Event
from game_core.entities.round import Round
from game_core.repository import Repository
from game_core.services.comm_service import CommService


class RoundService:

    def __init__(self, repository: Repository, comm_service: CommService):
        self._repository = repository
        self._comm_service = comm_service

    def start_round(self, game_id: str) -> None:
        ...

    def handle_team_proposal_submitted(self, event: Event) -> None:
        pass

    def on_enter_round_voting_state(self, game_id) -> None:
        pass

    def handle_round_vote_cast(self, event: Event) -> None:
        """
        On enter, request for votes
        On event, broadcast player has voted then save the vote
        On exit, broadcast the results - players and their votes
        :param event:
        :return:
        """
        pass

    def is_round_vote_completed(self, game_id) -> bool:
        pass

    def is_proposal_passed(self, game_id) -> bool:
        pass

    def on_exit_round_voting_state(self, game_id):
        pass

    def create_round(self, game_id: str, leader_id: str, quest_number: int) -> Round:
        rounds = self._repository.get_rounds_by_quest(game_id, quest_number)
        rounds = sorted(rounds, key=lambda r: r.round_number)
        round_number = 1 if not rounds else rounds[-1].round_number + 1
        current_round = self._repository.put_round(game_id, quest_number, round_number, leader_id)
        event = self._repository.put_event(game_id, EventType.ROUND_STARTED.value, [],
                                           {"quest_number": quest_number, "round_number": round_number,
                                            "leader_id": leader_id},
                                           int(datetime.now().timestamp()))
        self._comm_service.broadcast(event)
        game = self._repository.get_game(game_id)
        number_of_players = game.config.quest_team_size[quest_number]
        select_team_event = self._repository.put_event(game_id, EventType.SELECT_TEAM.value, [leader_id],
                                                       {"quest_number": quest_number, "round_number": round_number,
                                                        "number_of_players": number_of_players},
                                                       int(datetime.now().timestamp()))
        self._comm_service.notify(leader_id, select_team_event)
        return current_round
