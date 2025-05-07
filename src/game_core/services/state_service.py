from game_core.constants.state_name import StateName
from game_core.constants.vote_result import VoteResult
from game_core.entities.game import Game
from game_core.entities.player import Player
from game_core.entities.round import Round
from game_core.services.event_service import EventService
from game_core.services.game_service import GameService
from game_core.services.player_service import PlayerService
from game_core.services.quest_service import QuestService
from game_core.services.round_service import RoundService


class StateService:
    def __init__(
            self,
            game_service: GameService,
            player_service: PlayerService,
            quest_service: QuestService,
            round_service: RoundService,
            event_service: EventService,
    ):
        self._game_service = game_service
        self._player_service = player_service
        self._quest_service = quest_service
        self._round_service = round_service
        self._event_service = event_service

    def start_game(self, game_id: str, players: list[Player]) -> None:
        self._event_service.create_game_started_events(game_id, players)
        self.start_quest(game_id)

    def start_quest(self, game_id: str) -> None:
        next_quest_number = self._get_next_quest_number(game_id)
        quest = self._quest_service.add_quest(game_id, next_quest_number)
        self._event_service.create_quest_started_event(game_id, quest.quest_number)
        self.start_round(game_id, quest.quest_number)

    def start_round(self, game_id: str, quest_number: int) -> None:
        game = self._game_service.get_game(game_id)
        next_leader_id = self._get_next_leader_id(game)
        next_round_number = self._get_next_round_number(game_id, quest_number)
        game_round = self._round_service.add_round(game_id, quest_number, next_round_number, next_leader_id)
        self._event_service.create_round_started_event(game_id,
                                                       quest_number,
                                                       game_round.round_number,
                                                       game_round.leader_id)
        self.request_team_selection(game, quest_number, next_round_number, next_leader_id)

    def request_team_selection(self, game: Game, quest_number: int, round_number: int, leader_id: str) -> None:
        number_of_players = game.quest_team_size[quest_number]
        game.state = StateName.TeamSelection
        self._game_service.update_game(game)
        self._event_service.create_team_selection_requested_event(
            game.id,
            leader_id,
            quest_number,
            round_number,
            number_of_players
        )

    def end_round(self, current_round: Round) -> None:
        game_id = current_round.game_id
        round_result, player_votes = self._get_round_result(
            game_id,
            current_round.quest_number,
            current_round.round_number
        )
        current_round.result = round_result
        self._round_service.update_round(current_round)
        self._event_service.create_round_completed_event(
            game_id,
            current_round.quest_number,
            current_round.round_number,
            player_votes,
            current_round.result
        )

        if round_result == VoteResult.Pass:
            self.request_quest_vote(game_id, current_round.quest_number, current_round.team_member_ids)
        elif round_result == VoteResult.Fail:
            if 0 < current_round.round_number < 5:
                self.start_round(game_id, current_round.quest_number)
            elif current_round.round_number == 5:
                self.end_quest(game_id, VoteResult.Fail)
            else:
                raise RuntimeError(f"Invalid round number {current_round.round_number}")
        else:
            raise RuntimeError(f"Invalid round result {round_result}")

    def request_quest_vote(self, game_id: str, quest_number: int, team_member_ids: list[str]) -> None:
        current_quest = self._quest_service.get_current_quest(game_id)
        current_quest.team_member_ids = team_member_ids
        self._quest_service.update_quest(current_quest)
        game = self._game_service.get_game(game_id)
        game.state = StateName.QuestVoting
        self._game_service.update_game(game)
        self._event_service.create_quest_vote_started_event(game_id, quest_number, team_member_ids)
        self._event_service.create_quest_vote_requested_event(game_id, quest_number, team_member_ids)

    def end_quest(self, game_id: str, result: VoteResult | None = None) -> None:
        current_quest = self._quest_service.get_current_quest(game_id)
        num_failed_votes = 0
        if not result:
            result, num_failed_votes = self._get_quest_result(current_quest, game_id)
        current_quest.result = result
        self._quest_service.update_quest(current_quest)
        quests = self._quest_service.get_quests(game_id)
        num_passed_quests = sum(1 for q in quests if q.result == VoteResult.Pass)
        num_failed_quests = sum(1 for q in quests if q.result == VoteResult.Fail)
        self._event_service.create_quest_completed_event(game_id, current_quest.quest_number, current_quest.result,
                                                         num_failed_votes)
        if num_passed_quests >= 3:
            self.start_assassination(game_id)
        elif num_failed_quests >= 3:
            self.end_game(game_id, "Evil")
        else:
            self.start_quest(game_id)

    def start_assassination(self, game_id: str) -> None:
        game = self._game_service.get_game(game_id)
        game.assassination_attempts -= 1
        self._game_service.update_game(game)
        assassin = self._player_service.get_assassin(game_id)
        self._event_service.create_assassination_started_event(game_id, game.assassination_attempts, assassin.id)
        self.request_assassination_target(game_id, assassin.id)

    def request_assassination_target(self, game_id: str, assassin_id: str) -> None:
        self._event_service.create_assassination_target_requested_event(game_id, assassin_id)
        game = self._game_service.get_game(game_id)
        game.state = StateName.EndGame
        self._game_service.update_game(game)

    def end_game(self, game_id: str, result: str) -> None:
        game = self._game_service.get_game(game_id)
        game.result = result
        self._game_service.update_game(game)
        player_roles = self._player_service.get_player_roles(game_id)
        self._event_service.create_game_ended_event(game_id, player_roles)

    def _get_quest_result(self, current_quest, game_id) -> tuple[VoteResult, int]:
        quest_votes = self._quest_service.get_quest_votes(game_id, current_quest.quest_number)
        failed_threshold = 1 if current_quest.quest_number == 4 else 0
        num_failed_votes = sum(1 for qv in quest_votes if qv.result == VoteResult.Fail)
        quest_result = VoteResult.Fail if num_failed_votes > failed_threshold else VoteResult.Pass
        return quest_result, num_failed_votes

    def _get_round_result(self,
                          game_id: str,
                          quest_number: int,
                          round_number: int) -> tuple[VoteResult, dict[str, VoteResult]]:
        round_votes = self._round_service.get_round_votes(game_id, quest_number, round_number)
        player_votes = {rv.player_id: rv.result for rv in round_votes}
        num_approved_votes = sum(1 for rv in round_votes if rv.result == VoteResult.Pass)
        is_proposal_passed = num_approved_votes > len(round_votes) / 2
        round_result = VoteResult.Pass if is_proposal_passed else VoteResult.Fail
        return round_result, player_votes

    def _get_next_quest_number(self, game_id):
        quests = self._quest_service.get_quests(game_id)
        quests = sorted(quests, key=lambda q: q.quest_number)
        current_quest_number = quests[-1].quest_number if quests else 0
        next_quest_number = current_quest_number + 1
        return next_quest_number

    def _get_next_round_number(self, game_id: str, quest_number: int) -> int:
        rounds_by_quest = self._round_service.get_rounds_by_quest(game_id, quest_number)
        last_round_number = rounds_by_quest[-1].round_number if rounds_by_quest else 0
        next_round_number = last_round_number + 1
        return next_round_number

    def _get_next_leader_id(self, game) -> str:
        game_id = game.id
        player_ids = game.player_ids
        last_round = self._round_service.get_last_round(game_id)
        if not last_round:
            return player_ids[0]
        current_leader_id = last_round.leader_id
        return player_ids[(player_ids.index(current_leader_id) + 1) % len(player_ids)]
