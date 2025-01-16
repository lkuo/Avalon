import json
import logging
import os
import uuid

from game_core.constants.action_type import ActionType
from game_core.entities.action import Action
from game_core.state_machine import StateMachine
from lambdas.dynamodb_repository import DynamoDBRepository
from lambdas.websocket_comm_service import WebSocketCommService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def lambda_handler(event, context):
    logger.info("Received event", event)
    try:
        table_name = os.environ['DYNAMODB_TABLE']
        region = os.environ['AWS_REGION']
        websocket_endpoint = os.environ['WEBSOCKET_ENDPOINT']

        path_params = event.get("pathParameters", {})
        game_id = path_params.get("game_id")
        if not game_id:
            logger.error("Missing game_id in path parameters")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing game_id in path parameters"}),
            }
        body = json.loads(event.get("body", "{}"))
        player_name = body.get("name")
        if not player_name:
            logger.error("Missing name in request body")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing name in request body"}),
            }
        repository = DynamoDBRepository(table_name, region)
        comm_service = WebSocketCommService(websocket_endpoint, repository)
        game_state_machine = StateMachine(comm_service, repository, game_id)
        player_id = uuid.uuid4().hex
        join_game_action = Action(
            id=uuid.uuid4().hex,
            game_id=game_id,
            player_id=player_id,
            type=ActionType.JoinGame,
            payload={"name": player_name},
        )
        game_state_machine.handle_action(join_game_action)
        return {
            "statusCode": 200,
            "body": json.dumps({
                "game_id": game_id,
                "player_id": f"{game_id}_player_{player_id}",
                "websocket_endpoint": websocket_endpoint,
            }),
        }
    except Exception as e:
        logger.error(e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }

