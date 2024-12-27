import pytest

from game_core.constants.action_type import ActionType
from game_core.entities.action import Action
from game_core.services.game_service import GameService
from game_core.states.end_game_state import EndGameState
from game_core.constants.state_name import StateName

ACTION_ID = "action_id"
GAME_ID = "game_id"
PLAYER_ID = "player_id"
SUBMIT_ASSASSINATION_TARGET_PAYLOAD = {}


@pytest.fixture
def game_service(mocker):
    return mocker.MagicMock(spec=GameService)


@pytest.fixture
def end_game_state(game_service):
    return EndGameState(game_service)


@pytest.fixture
def submit_assassination_target_action():
    return Action(
        ACTION_ID,
        GAME_ID,
        PLAYER_ID,
        ActionType.SubmitAssassinationTarget,
        SUBMIT_ASSASSINATION_TARGET_PAYLOAD,
    )


def test_end_game_state_when_game_not_ended(
    end_game_state, game_service, submit_assassination_target_action
):
    # Given
    game_service.is_game_finished.return_value = False
    game_service.get_assassination_attempts.return_value = 1

    # When
    next_state = end_game_state.handle(submit_assassination_target_action)

    # Then
    assert end_game_state.name == StateName.EndGame
    assert next_state == end_game_state
    game_service.handle_submit_assassination_target.assert_called_once_with(
        submit_assassination_target_action
    )


def test_end_game_state_when_game_ended(
    end_game_state, game_service, submit_assassination_target_action
):
    # Given
    game_service.get_assassination_attempts.return_value = 0
    game_service.is_game_finished.return_value = True

    # When
    next_state = end_game_state.handle(submit_assassination_target_action)

    # Then
    assert next_state is None
    game_service.handle_submit_assassination_target.assert_called_once_with(
        submit_assassination_target_action
    )


def test_end_game_state_with_invalid_event(
    end_game_state, game_service, submit_assassination_target_action
):
    # Given
    invalid_event = Action(
        ACTION_ID,
        GAME_ID,
        PLAYER_ID,
        ActionType.CastRoundVote,
        SUBMIT_ASSASSINATION_TARGET_PAYLOAD,
    )

    # When
    with pytest.raises(ValueError):
        end_game_state.handle(invalid_event)

    # Then
    game_service.handle_submit_assassination_target.assert_not_called()


def test_end_game_state_on_enter_with_assassination_attempts(
    end_game_state, game_service, submit_assassination_target_action
):
    # Given
    game_service.get_assassination_attempts.return_value = 1

    # When
    end_game_state.on_enter(GAME_ID)

    # Then
    game_service.get_assassination_attempts.assert_called_once_with(GAME_ID)
    game_service.on_enter_end_game_state.assert_called_once_with(GAME_ID)
    game_service.handle_game_ended.assert_not_called()


def test_end_game_state_on_enter_without_assassination_attempts(
    end_game_state, game_service, submit_assassination_target_action
):
    # Given
    game_service.get_assassination_attempts.return_value = 0

    # When
    end_game_state.on_enter(GAME_ID)

    # Then
    game_service.get_assassination_attempts.assert_called_once_with(GAME_ID)
    game_service.handle_game_ended.assert_called_once_with(GAME_ID)
    game_service.on_enter_end_game_state.assert_not_called()
