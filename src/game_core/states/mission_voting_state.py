from typing import Self

from game_core.entities.event import Event
from game_core.states.state import State, StateName


class MissionVotingState(State):
    def __init__(self):
        super().__init__(StateName.MISSION_VOTING)

    def handle(self, event: Event) -> Self:
        pass
