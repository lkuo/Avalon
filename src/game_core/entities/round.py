from dataclasses import dataclass
from typing import Optional

from game_core.constants.voting_result import VotingResult


@dataclass
class Round:
    id: str
    quest_number: int
    round_number: int
    leader_id: str
    team_member_ids: Optional[list[str]]
    result: Optional[VotingResult] = None
