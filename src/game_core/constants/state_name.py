from enum import Enum


class StateName(Enum):
    GameSetup = "GameSetup"
    TeamSelection = "TeamSelection"
    RoundVoting = "RoundVoting"
    QuestVoting = "QuestVoting"
    EndGame = "EndGame"
