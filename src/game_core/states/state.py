from abc import abstractmethod, ABC
from typing import Self, Optional

from game_core.constants.state_name import StateName
from game_core.entities.action import Action


class State(ABC):

    def __init__(self, name: StateName):
        self._name = name

    @property
    def name(self) -> StateName:
        return self._name

    @abstractmethod
    def handle(self, action: Action) -> Optional[Self]:
        pass

    def on_enter(self, game_id: str) -> Optional[Self]:
        pass

    def on_exit(self, game_id: str) -> None:
        pass
