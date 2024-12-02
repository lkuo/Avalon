import pytest

from game_core.entities.event import Event
from game_core.constants.event_type import EventType
from game_core.services.game_service import GameService
from game_core.states.end_game_state import EndGameState
from game_core.constants.state_name import StateName


@pytest.fixture
def game_service(mocker):
    return mocker.MagicMock(spec=GameService)


def test_end_game_state_when_game_not_ended(game_service):
    # Given
    state = EndGameState(game_service)
    event = Event(game_id="game_id", type=EventType.ASSASSINATION_TARGET_SUBMITTED, recipients=[],
                  payload={})
    game_service.is_game_finished.return_value = False

    # When
    next_state = state.handle(event)

    # Then
    assert state.name == StateName.END_GAME
    assert next_state == state
    game_service.handle_assassination_target_submitted.assert_called_once_with(event)


def test_end_game_state_when_game_ended(game_service):
    # Given
    state = EndGameState(game_service)
    event = Event(game_id="game_id", type=EventType.ASSASSINATION_TARGET_SUBMITTED, recipients=[],
                  payload={})
    game_service.is_game_finished.return_value = True

    # When
    next_state = state.handle(event)

    # Then
    assert next_state is None
    game_service.handle_assassination_target_submitted.assert_called_once_with(event)


def test_end_game_state_with_invalid_event(game_service):
    # Given
    state = EndGameState(game_service)
    invalid_event = Event(game_id="game_id", type=EventType.QUEST_STARTED, recipients=[], payload={})

    # When
    with pytest.raises(ValueError):
        state.handle(invalid_event)

    # Then
    assert state.name == StateName.END_GAME


def test_end_game_state_on_enter_with_assassination_attempts(game_service):
    # Given
    state = EndGameState(game_service)
    game_service.get_assassination_attempts.return_value = 1
    game_id = "game_id"

    # When
    state.on_enter(game_id)

    # Then
    game_service.get_assassination_attempts.assert_called_once_with(game_id)
    game_service.on_enter_end_game_state.assert_called_once()
    game_service.handle_game_ended.assert_not_called()


def test_end_game_state_on_enter_without_assassination_attempts(game_service):
    # Given
    state = EndGameState(game_service)
    game_service.get_assassination_attempts.return_value = 0
    game_id = "game_id"

    # When
    state.on_enter(game_id)

    # Then
    game_service.get_assassination_attempts.assert_called_once_with(game_id)
    game_service.on_enter_end_game_state.assert_not_called()
    game_service.handle_game_ended.assert_called_once_with(game_id)
