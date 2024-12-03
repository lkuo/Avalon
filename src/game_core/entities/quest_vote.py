from dataclasses import dataclass

# todo: add game id field, refactor is_approved from boolean value to VotingResult
@dataclass
class QuestVote:
    id: str
    player_id: str
    quest_number: int
    is_approved: bool
