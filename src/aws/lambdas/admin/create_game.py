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
        game = repository.put_game()
        return {
            "statusCode": 200,
            "body": json.dumps({"game_id": game.id}),
        }
    except Exception as e:
        logger.error(e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
