import json
import logging
import os

from aws.dynamodb_repository import DynamoDBRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def lambda_handler(event, context):
    logger.info("Received event", event)

    try:
        table_name = os.environ['DYNAMODB_TABLE']
        region = os.environ['AWS_REGION']
        repository = DynamoDBRepository(table_name, region)
        game_id = event.get("pathParameters", {}).get("game_id")
        body = json.loads(event.get("body", {}))
        if "player_ids" not in body:
            raise ValueError("player_ids is required")
        game = repository.get_game(game_id)
        game.player_ids = body["player_ids"]
        if "assassination_attempts" in body:
            game.assassination_attempts = body["assassination_attempts"]
        repository.update_game(game)
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
