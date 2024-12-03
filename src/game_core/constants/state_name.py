from enum import Enum


class StateName(Enum):
    # todo: not to use all capital
    GAME_SETUP = "GAME_SETUP"
    TEAM_SELECTION = "TEAM_SELECTION"
    ROUND_VOTING = "ROUND_VOTING"
    QUEST_VOTING = "QUEST_VOTING"
    END_GAME = "END_GAME"
