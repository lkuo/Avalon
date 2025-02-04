import json
import logging
import os
import uuid

from aws.dynamodb_repository import DynamoDBRepository
from aws.websocket_comm_service import WebSocketCommService
from game_core.constants.action_type import ActionType
from game_core.entities.action import Action
from game_core.state_machine import StateMachine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def lambda_handler(event, context):
    logger.info(f"Received event {event}")

    try:
        table_name = os.environ['DYNAMODB_TABLE']
        region = os.environ['AWS_REGION']
        websocket_endpoint = os.environ['WEBSOCKET_ENDPOINT']
        repository = DynamoDBRepository(table_name, region)
        comm_service = WebSocketCommService(websocket_endpoint, repository)
        game_id = event.get("pathParameters", {}).get("game_id")
        body = json.loads(event.get("body", {}))
        if "player_ids" not in body:
            raise ValueError("player_ids is required")
        payload = {
            "game_id": game_id,
            "player_ids": body["player_ids"],
        }
        if "assassination_attempts" in body:
            payload["assassination_attempts"] = body["assassination_attempts"]
        game_state_machine = StateMachine(comm_service, repository, game_id)
        action = Action(
            id=uuid.uuid4().hex,
            game_id=game_id,
            player_id="admin",
            type=ActionType.StartGame,
            payload=payload,
        )
        game_state_machine.handle_action(action)
        return {
            "statusCode": 200,
            "body": "",
        }
    except Exception as e:
        logger.error(e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
