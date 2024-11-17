from dataclasses import dataclass
from typing import Optional

from game_core.constants.voting_result import VotingResult


@dataclass
class Quest:
    id: str
    quest_number: int
    result: Optional[VotingResult] = None
    team_member_ids: Optional[list[str]] = None
