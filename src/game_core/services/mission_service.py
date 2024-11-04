class MissionService:
    def start_mission(self, game_id: str) -> None:
        ...

    def broadcast_quest_vote_started(self, game_id) -> None:
        pass

    def notify_cast_quest_vote(self, game_id) -> None:
        pass

    def broadcast_quest_vote_result(self, game_id) -> None:
        pass

    def save_mission_vote(self, game_id, mission_number, player_id, vote) -> None:
        pass

    def is_mission_voted(self, game_id):
        pass

    def is_mission_passed(self, game_id):
        pass

    def is_missions_completed(self, game_id) -> bool:
        """
        If any team has won 3 out of 5 missions
        :param game_id:
        :return:
        """
        pass
