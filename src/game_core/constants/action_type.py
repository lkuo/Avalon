from enum import Enum


class ActionType(Enum):
    StartGame = "StartGame"
    JoinGame = "JoinGame"
    SubmitTeamProposal = "SubmitTeamProposal"
    CastRoundVote = "SubmitRoundVote"
    CastQuestVote = "SubmitQuestVote"
    SubmitAssassinationTarget = "SubmitAssassinationTarget"
