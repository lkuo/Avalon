from dataclasses import dataclass

# todo: add game id field
@dataclass
class RoundVote:
    id: str
    player_id: str
    quest_number: int
    round_number: int
    is_approved: bool
