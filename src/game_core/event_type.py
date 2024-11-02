from enum import Enum


class EventType(Enum):
    """
    Enum class for event types.
    """
    GAME_STARTED = "GAME_STARTED"
    TEAM_REJECTED = "TEAM_REJECTED"
    QUEST_COMPLETED = "QUEST_COMPLETED"
    TEAM_PROPOSAL_SUBMITTED = "TEAM_PROPOSAL_SUBMITTED"

    MISSION_STARTED = "MISSION_STARTED"
