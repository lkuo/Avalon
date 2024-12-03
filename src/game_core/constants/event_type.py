from enum import Enum


class EventType(Enum):
    """
    Enum class for event types.
    """
    # todo: not to use all capital
    ASSASSINATION_FAILED = "ASSASSINATION_FAILED"
    ASSASSINATION_STARTED = "ASSASSINATION_TARGET_STARTED"
    ASSASSINATION_SUCCEEDED = "ASSASSINATION_SUCCEEDED"
    ASSASSINATION_TARGET_REQUESTED = "ASSASSINATION_TARGET_REQUESTED"
    ASSASSINATION_TARGET_SUBMITTED = "ASSASSINATION_TARGET_SUBMITTED"
    GAME_ENDED = "GAME_ENDED"
    GAME_STARTED = "GAME_STARTED"
    PLAYER_JOINED = "PLAYER_JOINED"
    QUEST_COMPLETED = "QUEST_COMPLETED"
    QUEST_STARTED = "QUEST_STARTED"
    QUEST_VOTE_CAST = "QUEST_VOTE_CAST"
    QUEST_VOTE_REQUESTED = "QUEST_VOTE_REQUESTED"
    QUEST_VOTING_STARTED = "QUEST_VOTING_STARTED"
    ROUND_COMPLETED = "ROUND_COMPLETED"
    ROUND_STARTED = "ROUND_STARTED"
    ROUND_VOTE_CAST = "ROUND_VOTE_CAST"
    SELECT_TEAM = "SELECT_TEAM"
    TEAM_PROPOSAL_SUBMITTED = "TEAM_PROPOSAL_SUBMITTED"
    TEAM_REJECTED = "TEAM_REJECTED"
