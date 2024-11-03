from game_core.entities.event import Event
from game_core.event_type import EventType
from game_core.services.round_service import RoundService
from game_core.states.state import State, StateName


class RoundVotingState(State):
    """
    Broadcast the team proposal then collect all votes.
    Transitions from LeaderAssignmentState
    Transitions to LeaderAssignmentState or MissionVoting state, depends on the vote results
    On enter, request for votes
    On event, broadcast player has voted then save the vote
    On exit, broadcast the results - players and their votes
    """

    def __init__(self, leader_assignment_state: State, mission_voting_state: State, round_service: RoundService):
        super().__init__(StateName.ROUND_VOTING)
        self._leader_assignment_state = leader_assignment_state
        self._mission_voting_state = mission_voting_state
        self._round_service = round_service

    def handle(self, event: Event) -> State:
        if event.type != EventType.ROUND_VOTE_CASTED:
            raise ValueError(f"RoundVotingState expects only ROUND_VOTE_CASTED, got {event.type.value}")

        payload = event.payload
        if payload is None or not payload.get("mission_number") or not payload.get("round_number") or not payload.get(
                "player_id") or payload.get("vote") is None:
            raise ValueError(
                f"Invalid event, expects payload to have mission_number, round_number, player_id and vote keys, got {payload}")
        payload = event.payload
        mission_number = payload["mission_number"]
        round_number = payload["round_number"]
        player_id = payload["player_id"]
        vote = payload["vote"]

        self._round_service.handle_vote(event.game_id, mission_number, round_number, player_id, vote)
        if not self._round_service.is_round_voted(event.game_id):
            return self

        proposal_passed = self._round_service.is_proposal_passed(event.game_id)
        return self._mission_voting_state if proposal_passed else self._leader_assignment_state

    def on_enter(self, game_id: str) -> None:
        self._round_service.broadcast_round_vote_request(game_id)
