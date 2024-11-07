from game_core.entities.event import Event


class QuestService:
    def start_mission(self, game_id: str) -> None:
        ...

    def on_enter_quest_voting_state(self, game_id) -> None:
        """
        On enter broadcast quest voting started by team members, and notify team members to cast vote
        On event saves vote and broadcast player X has voted
        On exit broadcast the quest voting result and updates mission
        :param game_id:
        :return:
        """
        pass

    def on_exit_quest_voting_state(self, game_id) -> None:
        pass

    def handle_quest_vote_cast(self, event: Event) -> None:
        pass

    def is_quest_vote_completed(self, game_id):
        pass

    def is_mission_passed(self, game_id):
        pass

    def has_won_majority(self, game_id) -> bool:
        """
        If any team has won 3 out of 5 missions
        :param game_id:
        :return:
        """
        pass

    def handle_on_enter_team_selection_state(self, game_id: str) -> None:
        pass
