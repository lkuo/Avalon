import json
import logging
import os
import uuid

from game_core.constants.action_type import ActionType
from game_core.entities.action import Action
from game_core.state_machine import StateMachine
from aws.dynamodb_repository import DynamoDBRepository
from aws.websocket_comm_service import WebSocketCommService

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("Received event", event)
    try:
        table_name = os.environ['DYNAMODB_TABLE']
        region = os.environ['AWS_REGION']
        websocket_endpoint = os.environ['WEBSOCKET_ENDPOINT']
        message = json.loads(event.get("body", "{}"))
        game_id = message.get("game_id")
        player_id = message.get("player_id")
        action_type = message.get("action_type")
        payload = message.get("payload", {})

        repository = DynamoDBRepository(table_name, region)
        comm_service = WebSocketCommService(websocket_endpoint, repository)
        game_state_machine = StateMachine(comm_service, repository, game_id)
        action = Action(
            id=uuid.uuid4().hex,
            game_id=game_id,
            player_id=player_id,
            type=ActionType(action_type),
            payload=payload,
        )
        game_state_machine.handle_action(action)
        return {
            "statusCode": 200,
        }
    except Exception as e:
        logger.error(e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
