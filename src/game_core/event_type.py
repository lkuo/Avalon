from enum import Enum


class EventType(Enum):
    """
    Enum class for event types.
    """
    GAME_STARTED = "GAME_STARTED"
    PLAYER_JOINED = "PLAYER_JOINED"
    TEAM_REJECTED = "TEAM_REJECTED"
    QUEST_COMPLETED = "QUEST_COMPLETED"
    TEAM_PROPOSAL_SUBMITTED = "TEAM_PROPOSAL_SUBMITTED"
    ROUND_VOTE_CAST = "ROUND_VOTE_CAST"
    QUEST_VOTE_CAST = "QUEST_VOTE_CAST"
    ASSASSINATION_TARGET_SUBMITTED = "ASSASSINATION_TARGET_SUBMITTED"

    QUEST_STARTED = "QUEST_STARTED"
