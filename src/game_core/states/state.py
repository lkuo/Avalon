from abc import abstractmethod, ABC
from enum import Enum
from typing import Self

from game_core.entities.event import Event


class StateName(Enum):
    GAME_SETUP = "GAME_SETUP"
    LEADER_ASSIGNMENT = "LEADER_ASSIGNMENT"
    TEAM_SELECTION = "TEAM_SELECTION"
    ROUND_VOTING = "ROUND_VOTING"
    MISSION_VOTING = "MISSION_VOTING"


class State(ABC):

    def __init__(self, name: StateName):
        self._name = name

    @property
    def name(self) -> StateName:
        return self._name

    @abstractmethod
    def handle(self, event: Event) -> Self:
        pass

    def on_enter(self, game_id: str) -> None:
        pass

    def on_exit(self):
        pass
