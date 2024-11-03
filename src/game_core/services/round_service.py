class RoundService:
    def start_round(self, game_id: str) -> None:
        ...

    def notify_submit_team_proposal(self, game_id: str) -> None:
        pass

    def broadcast_team_proposal(self, game_id: str) -> None:
        pass

    def broadcast_round_vote_request(self, game_id) -> None:
        pass

    def handle_vote(self, game_id, mission_number, round_number, player_id, vote) -> None:
        pass

    def is_round_voted(self, game_id) -> bool:
        pass

    def is_proposal_passed(self, game_id) -> bool:
        pass
