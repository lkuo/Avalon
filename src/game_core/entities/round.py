from dataclasses import dataclass
from typing import Optional

from game_core.constants.vote_result import VoteResult


@dataclass
class Round:
    id: str
    game_id: str
    quest_number: int
    round_number: int
    leader_id: str
    team_member_ids: Optional[list[str]]
    result: Optional[VoteResult] = None
