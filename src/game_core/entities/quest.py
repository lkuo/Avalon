from dataclasses import dataclass
from typing import Optional

from game_core.constants.voting_result import VoteResult

# todo: add game id field
@dataclass
class Quest:
    id: str
    quest_number: int
    result: Optional[VoteResult] = None
    team_member_ids: Optional[list[str]] = None
