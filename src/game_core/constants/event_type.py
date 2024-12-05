from enum import Enum


class EventType(Enum):
    """
    Enum class for event types.
    """
    AssassinationFailed = "AssassinationFailed"
    AssassinationStarted = "AssassinationStarted"
    AssassinationSucceeded = "AssassinationSucceeded"
    AssassinationTargetRequested = "AssassinationTargetRequested"
    AssassinationTargetSubmitted = "AssassinationTargetSubmitted"
    GameEnded = "GameEnded"
    GameStarted = "GameStarted"
    PlayerJoined = "PlayerJoined"
    QuestCompleted = "QuestCompleted"
    QuestStarted = "QuestStarted"
    QuestVoteStarted = "QuestVoteStarted"
    QuestVoteCast = "QuestVoteCast"
    QuestVoteRequested = "QuestVoteRequested"
    QuestVoteSubmitted = "QuestVoteSubmitted"
    RoundCompleted = "RoundCompleted"
    RoundStarted = "RoundStarted"
    RoundVoteCast = "RoundVoteCast"
    SelectTeam = "SelectTeam"
    TeamProposalSubmitted = "TeamProposalSubmitted"
    TeamRejected = "TeamRejected"
