from dataclasses import dataclass

from game_core.constants.vote_result import VoteResult


@dataclass
class RoundVote:
    id: str
    game_id: str
    player_id: str
    quest_number: int
    round_number: int
    result: VoteResult
