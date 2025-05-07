from game_core.constants.vote_result import VoteResult
from game_core.entities.game import Game
from game_core.entities.round import Round
from game_core.entities.round_vote import RoundVote
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

    def add_round(self, game_id: str, quest_number: int, round_number: int, leader_id: str) -> Round:
        return self._repository.put_round(game_id, quest_number, round_number, leader_id)

    def get_rounds_by_game(self, game_id: str) -> list[round]:
        rounds = self._repository.get_rounds(game_id)
        return sorted(rounds, key=lambda r: (r.quest_number, r.round_number))

    def get_rounds_by_quest(self, game_id: str, quest_number: int) -> list[Round]:
        rounds = self.get_rounds_by_game(game_id)
        return [r for r in rounds if r.quest_number == quest_number]

    def get_last_round(self, game_id: str) -> Round | None:
        rounds = self.get_rounds_by_game(game_id)
        return rounds[-1] if rounds else None

    def get_round_votes(self, game_id: str, quest_number: int, round_number: int) -> list[RoundVote]:
        return self._repository.get_round_votes(game_id, quest_number, round_number)

    def create_round(self, game: Game, quest_number: int) -> Round:
        game_id = game.id
        rounds = self._repository.get_rounds(game_id)
        current_round = self._get_last_round(rounds)
        round_number = 1 if not current_round or current_round.quest_number != quest_number else current_round.round_number + 1
        leader_id = self._get_leader_id(rounds, game.player_ids)
        next_round = self._repository.put_round(game_id, quest_number, round_number, leader_id)
        self._event_service.create_round_started_event(game_id, quest_number, round_number, leader_id)
        return next_round

    def get_current_round(self, game_id: str) -> Round | None:
        rounds = self._repository.get_rounds(game_id)
        return self._get_last_round(rounds)

    @staticmethod
    def _get_last_round(rounds: list[Round]) -> Round | None:
        rounds = sorted(rounds, key=lambda r: (r.quest_number, r.round_number))
        return rounds[-1] if rounds else None

    @staticmethod
    def _get_leader_id(rounds: list[Round], player_ids: list[str]) -> str:
        rounds.sort(key=lambda r: (r.quest_number, r.round_number))
        leader_id = rounds[-1].leader_id if rounds else player_ids[-1]
        idx = player_ids.index(leader_id)
        next_leader_id = player_ids[(idx + 1) % len(player_ids)]
        return next_leader_id

    def update_round(self, game_round: Round) -> Round:
        return self._repository.update_round(game_round)

    def create_round_vote(self,
                          game_id: str,
                          quest_number: int,
                          round_number: int,
                          player_id: str,
                          vote_result: VoteResult):
        return self._repository.put_round_vote(
            game_id,
            quest_number,
            round_number,
            player_id,
            vote_result
        )
