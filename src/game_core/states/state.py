from abc import abstractmethod, ABC

from game_core.constants.action_type import ActionType
from game_core.constants.state_name import StateName
from game_core.entities.action import Action


class State(ABC):

    def __init__(self, name: StateName):
        self._name = name

    @property
    def name(self) -> StateName:
        return self._name

    @abstractmethod
    def handle(self, action: Action) -> None:
        pass


class InvalidInputException(Exception):
    error_code = 400


class InvalidActionTypeException(InvalidInputException):
    def __init__(self, expected: list[ActionType], actual: ActionType):
        self.message = f"Invalid action type: {actual}, expected one of {expected}"
        super().__init__(self.message)
