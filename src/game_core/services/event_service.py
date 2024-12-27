from datetime import datetime
from typing import Any

from game_core.constants.event_type import EventType
from game_core.constants.vote_result import VoteResult
from game_core.entities.event import Event
from game_core.entities.player import Player
from game_core.repository import Repository
from game_core.services.comm_service import CommService


class EventService:
    def __init__(self, comm_service: CommService, repository: Repository):
        self._comm_service = comm_service
        self._repository = repository

    def create_player_joined_event(
        self, player_id: str, game_id: str, player_name: str
    ) -> None:
        payload = {"player_id": player_id, "player_name": player_name}
        event = self._create_event(game_id, EventType.PlayerJoined, [], payload)
        self._comm_service.broadcast(event)

    def create_game_started_events(self, game_id: str, players: list[Player]) -> None:
        events_by_player_id: dict[str, Event] = {}
        player_by_id = {player.id: player for player in players}
        for player in players:
            known_players = [
                player_by_id[known_player_id]
                for known_player_id in player.known_player_ids
            ]
            payload = {
                "role": player.role.value,
                "known_players": [
                    {
                        "id": known_player.id,
                        "name": known_player.name,
                    }
                    for known_player in known_players
                ],
            }
            events_by_player_id[player.id] = self._create_event(
                game_id, EventType.GameStarted, [player.id], payload
            )

        for player_id, event in events_by_player_id.items():
            self._comm_service.notify(player_id, event)

    def create_quest_started_event(self, game_id: str, quest_number: int) -> None:
        payload = {
            "quest_number": quest_number,
        }
        event = self._create_event(game_id, EventType.QuestStarted, [], payload)
        self._comm_service.broadcast(event)

    def create_round_started_event(
        self, game_id: str, quest_number: int, round_number: int, leader_id: str
    ) -> None:
        payload = {
            "quest_number": quest_number,
            "round_number": round_number,
            "leader_id": leader_id,
        }
        event = self._create_event(game_id, EventType.RoundStarted, [], payload)
        self._comm_service.broadcast(event)

    def create_team_selection_requested_event(
        self, game_id: str, quest_number: int, round_number: int, number_of_players: int
    ) -> None:
        payload = {
            "quest_number": quest_number,
            "round_number": round_number,
            "number_of_players": number_of_players,
        }
        event = self._create_event(
            game_id, EventType.TeamSelectionRequested, [], payload
        )
        self._comm_service.broadcast(event)

    def create_team_proposal_submitted_event(
        self,
        game_id: str,
        quest_number: int,
        round_number: int,
        team_member_ids: list[str],
    ) -> None:
        payload = {
            "quest_number": quest_number,
            "round_number": round_number,
            "team_member_ids": team_member_ids,
        }
        event = self._create_event(
            game_id, EventType.TeamProposalSubmitted, [], payload
        )
        self._comm_service.broadcast(event)

    def create_round_vote_cast_event(
        self,
        game_id: str,
        quest_number: int,
        round_number: int,
        player_id: str,
        vote_result: VoteResult,
    ) -> None:
        payload = {
            "quest_number": quest_number,
            "round_number": round_number,
            "player_id": player_id,
            "result": vote_result.value,
        }
        event = self._create_event(game_id, EventType.RoundVoteCast, [], payload)
        self._comm_service.broadcast(event)

    def create_round_completed_event(
        self,
        game_id: str,
        quest_number: int,
        round_number: int,
        vote_result: VoteResult,
    ) -> None:
        payload = {
            "quest_number": quest_number,
            "round_number": round_number,
            "result": vote_result.value,
        }
        event = self._create_event(game_id, EventType.RoundCompleted, [], payload)
        self._comm_service.broadcast(event)

    def create_quest_completed_event(
        self, game_id: str, quest_number: int, result: VoteResult
    ) -> None:
        payload = {
            "quest_number": quest_number,
            "result": result.value,
        }
        event = self._create_event(game_id, EventType.QuestCompleted, [], payload)
        self._comm_service.broadcast(event)

    def create_quest_vote_started_event(
        self, game_id: str, quest_number: int, team_member_ids: list[str]
    ) -> None:
        payload = {
            "quest_number": quest_number,
            "team_member_ids": team_member_ids,
        }
        event = self._create_event(game_id, EventType.QuestVoteStarted, [], payload)
        self._comm_service.broadcast(event)

    def create_quest_vote_requested_event(
        self, game_id: str, quest_number: int, team_member_ids: list[str]
    ) -> None:
        payload = {
            "quest_number": quest_number,
            "team_member_ids": team_member_ids,
        }
        event = self._create_event(
            game_id, EventType.QuestVoteRequested, team_member_ids, payload
        )
        for team_member_id in team_member_ids:
            self._comm_service.notify(team_member_id, event)

    def create_quest_vote_cast_event(
        self, game_id: str, quest_number: int, player_id: str, vote_result: VoteResult
    ) -> None:
        payload = {
            "quest_number": quest_number,
            "result": vote_result.value,
            "player_id": player_id,
        }
        event = self._create_event(game_id, EventType.QuestVoteCast, [], payload)
        self._comm_service.broadcast(event)

    def create_assassination_started_event(
        self, game_id: str, assassination_attempts: int
    ) -> None:
        payload = {"assassination_attempts": assassination_attempts}
        event = self._create_event(game_id, EventType.AssassinationStarted, [], payload)
        self._comm_service.broadcast(event)

    def create_assassination_target_requested_event(
        self, game_id: str, assassin_id: str
    ) -> None:
        event = self._create_event(
            game_id, EventType.AssassinationTargetRequested, [assassin_id], {}
        )
        self._comm_service.broadcast(event)

    def create_assassination_event(
        self, game_id: str, target_id: str, is_successful: bool
    ) -> None:
        payload = {
            "target_id": target_id,
            "is_successful": is_successful,
        }
        event_type = (
            EventType.AssassinationSucceeded
            if is_successful
            else EventType.AssassinationFailed
        )
        event = self._create_event(game_id, event_type, [], payload)
        self._comm_service.broadcast(event)

    def create_game_ended_event(
        self, game_id: str, player_roles: dict[str, Any]
    ) -> None:
        payload = {
            "player_roles": player_roles,
        }
        event = self._create_event(game_id, EventType.GameEnded, [], payload)
        self._comm_service.broadcast(event)

    def _create_event(
        self,
        game_id: str,
        event_type: EventType,
        recipients: list[str],
        payload: dict[str, Any],
    ) -> Event:
        return self._repository.put_event(
            game_id, event_type.value, recipients, payload, datetime.now().isoformat()
        )
