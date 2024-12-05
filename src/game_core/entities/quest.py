from dataclasses import dataclass
from typing import Optional

from game_core.constants.vote_result import VoteResult


@dataclass
class Quest:
    id: str
    game_id: str
    quest_number: int
    result: Optional[VoteResult] = None
    team_member_ids: Optional[list[str]] = None
