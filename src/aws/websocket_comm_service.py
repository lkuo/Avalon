import json
import logging
from concurrent.futures import ThreadPoolExecutor

import boto3

from game_core.entities.event import Event
from game_core.comm_service import CommService
from aws.dynamodb_repository import DynamoDBRepository

log = logging.getLogger(__name__)


class WebSocketCommService(CommService):
    def __init__(self, endpoint_url: str, repository: DynamoDBRepository):
        self._endpoint_url = endpoint_url
        self._repository = repository
        self._api_gateway = boto3.client("apigatewaymanagementapi", endpoint_url=endpoint_url)

    def broadcast(self, event: Event) -> None:
        connection_ids = self._repository.get_connection_ids(event.game_id)
        executor = ThreadPoolExecutor(max_workers=len(connection_ids))
        for connection_id in connection_ids:
            executor.submit(self._emit, connection_id, event)
        executor.shutdown(wait=True)

    def notify(self, player_id: str, event: Event) -> None:
        connection_id = self._repository.get_connection_id(event.game_id, player_id)
        self._emit(connection_id, event)

    def _emit(self, connection_id: str, event: Event) -> None:
        try:
            data = json.dumps(event.to_dict())
            self._api_gateway.post_to_connection(
                ConnectionId=connection_id,
                Data=data
            )
        except Exception as e:
            log.error(f"Failed to send event to connection {connection_id}", exc_info=e)
            raise e
