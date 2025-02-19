import logging

from game_core.constants.state_name import StateName
from game_core.entities.action import Action
from game_core.repository import Repository
from game_core.comm_service import CommService
from game_core.services.event_service import EventService
from game_core.services.game_service import GameService
from game_core.services.player_service import PlayerService
from game_core.services.quest_service import QuestService
from game_core.services.round_service import RoundService
from game_core.states.end_game_state import EndGameState
from game_core.states.game_setup_state import GameSetupState
from game_core.states.quest_voting_state import QuestVotingState
from game_core.states.round_voting_state import RoundVotingState
from game_core.states.team_selection_state import TeamSelectionState

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class StateMachine:

    def __init__(self, comm_service: CommService, repository: Repository, game_id: str):
        self._game_id = game_id
        self._repository = repository
        self._event_service = EventService(comm_service, repository)
        self._player_service = PlayerService(self._event_service, repository)
        self._round_service = RoundService(self._event_service, repository)
        self._game_service = GameService(
            self._player_service, self._event_service, repository
        )
        self._quest_service = QuestService(
            self._round_service, self._event_service, self._player_service, repository
        )
        self._current_state = None
        self.state_name_map = {}
        self._setup_states()

    def _setup_states(self) -> None:
        game = self._repository.get_game(self._game_id)

        game_setup_state = GameSetupState(self._game_service, self._player_service)
        team_selection_state = TeamSelectionState(
            self._quest_service, self._round_service
        )
        round_voting_state = RoundVotingState(self._round_service)
        quest_voting_state = QuestVotingState(self._quest_service)
        end_game_state = EndGameState(self._game_service)

        game_setup_state.set_states(team_selection_state)
        team_selection_state.set_states(round_voting_state, quest_voting_state)
        round_voting_state.set_states(team_selection_state, quest_voting_state)
        quest_voting_state.set_states(team_selection_state, end_game_state)

        self.state_name_map = {
            StateName.GameSetup: game_setup_state,
            StateName.TeamSelection: team_selection_state,
            StateName.RoundVoting: round_voting_state,
            StateName.QuestVoting: quest_voting_state,
            StateName.EndGame: end_game_state,
        }
        self._current_state = self.state_name_map.get(game.state)

        if not self._current_state:
            raise ValueError(f"Invalid state {game.state}")

    def handle_action(self, action: Action) -> None:
        if action.payload is None:
            raise ValueError("Action payload is None")
        next_state = self._current_state.handle(action)
        if next_state != self._current_state:
            self._current_state.on_exit(self._game_id)
            self._current_state = next_state.on_enter(self._game_id) or next_state

        game = self._repository.get_game(self._game_id)
        logger.info(f"Game {game}")
        game.state = self._current_state.name
        self._repository.update_game(game)
