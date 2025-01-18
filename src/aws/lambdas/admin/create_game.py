import json
import logging
import os

from aws.dynamodb_repository import DynamoDBRepository
from game_core.constants.config import DEFAULT_QUEST_TEAM_SIZE, KNOWN_ROLES, DEFAULT_ASSASSINATION_ATTEMPTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def lambda_handler(event, context):
    logger.info("Received event", event)

    try:
        table_name = os.environ['DYNAMODB_TABLE']
        region = os.environ['AWS_REGION']
        repository = DynamoDBRepository(table_name, region)
        body = json.loads(event.get("body", "{}"))
        team_size = int(body.get("team_size"))
        if not team_size:
            raise ValueError("team_size is required")
        team_sizes = set(DEFAULT_QUEST_TEAM_SIZE.keys())
        if team_size not in team_sizes:
            raise ValueError(f"team_size must be one of {team_sizes}")
        game = repository.put_game(DEFAULT_QUEST_TEAM_SIZE[team_size], KNOWN_ROLES, DEFAULT_ASSASSINATION_ATTEMPTS)
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
