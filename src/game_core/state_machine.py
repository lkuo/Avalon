from game_core.constants.state_name import StateName
from game_core.entities.event import Event
from game_core.repository import Repository
from game_core.services.comm_service import CommService
from game_core.services.game_service import GameService
from game_core.services.player_service import PlayerService
from game_core.services.quest_service import QuestService
from game_core.services.round_service import RoundService
from game_core.states.end_game_state import EndGameState
from game_core.states.game_setup_state import GameSetupState
from game_core.states.quest_voting_state import QuestVotingState
from game_core.states.round_voting_state import RoundVotingState
from game_core.states.team_selection_state import TeamSelectionState

STATE_NAME_MAP = {
    StateName.GameSetup.value: GameSetupState,
    StateName.TeamSelection.value: TeamSelectionState,
    StateName.QuestVoting.value: QuestVotingState,
    StateName.RoundVoting.value: RoundVotingState,
    StateName.EndGame.value: EndGameState
}


class StateMachine:

    def __init__(self, comm_service: CommService, repository: Repository):
        self._comm_service = comm_service
        self._repository = repository
        self._current_state = None

    def _setup_states(self, game_id: str) -> None:
        self._player_service = PlayerService(self._comm_service, self._repository)
        self._game_service = GameService(self._comm_service, self._repository, self._player_service)
        self._round_service = RoundService(self._comm_service, self._repository)
        self._quest_service = QuestService(self._comm_service, self._repository, self._round_service)
        game = self._repository.get_game(game_id)
        game_setup_state = GameSetupState()
        team_selection_state = TeamSelectionState()
        round_voting_state = RoundVotingState()
        quest_voting_state = QuestVotingState()
        end_game_state = EndGameState()

        self._current_state = STATE_NAME_MAP[game.state]

        if not self._current_state:
            raise ValueError(f"Invalid state {game.state}")

    def handle_event(self, event: Event) -> None:
        game_id = event.game_id
        self._setup_states(game_id)

        next_state = self._current_state.handle(event)
        if next_state != self._current_state:
            self._current_state.on_exit()
            self._current_state = next_state.on_enter() or next_state
