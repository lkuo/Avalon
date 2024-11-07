from game_core.entities.event import Event


class RoundService:
    def start_round(self, game_id: str) -> None:
        ...

    def notify_submit_team_proposal(self, game_id: str) -> None:
        pass

    def handle_team_proposal_submitted(self, game_id: str) -> None:
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

    def is_last_round(self, game_id) -> bool:
        pass
