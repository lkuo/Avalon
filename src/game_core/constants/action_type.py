from enum import Enum


class ActionType(Enum):
    StartGame = "StartGame"
    JoinGame = "JoinGame"
    SubmitTeamProposal = "SubmitTeamProposal"
    CastRoundVote = "CastRoundVote"
    CastQuestVote = "CastQuestVote"
    SubmitAssassinationTarget = "SubmitAssassinationTarget"
