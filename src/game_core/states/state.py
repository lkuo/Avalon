from abc import abstractmethod, ABC
from enum import Enum
from typing import Self

from game_core.entities.event import Event


class StateName(Enum):
    GAME_SETUP = "GAME_SETUP"


class State(ABC):

    def __init__(self, name: StateName, next_state: Self):
        self._name = name
        self._next_state = next_state

    @abstractmethod
    def handle(self, event: Event):
        pass
