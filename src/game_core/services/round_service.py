class RoundService:
    def start_round(self, game_id: str) -> None:
        ...

    def notify_submit_team_proposal(self, game_id: str) -> None:
        pass

    def broadcast_team_proposal(self, game_id: str) -> None:
        pass
