import json
import logging
import os

from aws.dynamodb_repository import DynamoDBRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("Received event", event)

    try:
        table_name = os.environ['DYNAMODB_TABLE']
        region = os.environ['AWS_REGION']
        repository = DynamoDBRepository(table_name, region)
        game_id = event.get("pathParameters", {}).get("game_id")
        player_id = event.get("pathParameters", {}).get("player_id")
        headers = event.get("headers", {})
        player_secret = headers.get("player_secret")
        if not game_id or not player_id or not player_secret:
            logger.error(f"Missing required parameters {event}")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required parameters"}),
            }
        player = repository.get_player(player_id)
        if player.secret != player_secret:
            logger.error(f"Invalid player secret {event}")
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Invalid player secret"}),
            }
        events = repository.get_events(game_id, player_id)
        events = [event.to_dict() for event in events]
        return {
            "statusCode": 200,
            "body": json.dumps(events),
        }
    except Exception as e:
        logger.error(e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
