import json
import logging
import os

from aws.dynamodb_repository import DynamoDBRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info(f"Received event {event}")

    try:
        table_name = os.environ['DYNAMODB_TABLE']
        region = os.environ['AWS_REGION']
        connection_id = event.get("requestContext", {}).get("connectionId")
        query_string_params = event.get("queryStringParameters", {})
        game_id = query_string_params.get("game_id")
        player_id = query_string_params.get("player_id")
        if not connection_id or not game_id or not player_id:
            logger.error(f"Missing required parameters {query_string_params}")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required parameters"}),
            }

        repository = DynamoDBRepository(table_name, region)
        repository.put_connection_id(game_id, player_id, connection_id)
        logger.info(f"Connection id {connection_id} stored for game {game_id} and player {player_id}")
        return {
            "statusCode": 200,
            "body": "Connected",
        }
    except Exception as e:
        logger.error(e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
