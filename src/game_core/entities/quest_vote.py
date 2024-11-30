from dataclasses import dataclass


@dataclass
class QuestVote:
    id: str
    player_id: str
    quest_number: int
    is_approved: bool
