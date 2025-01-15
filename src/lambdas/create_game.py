import json
import logging
import os

from pydantic import BaseModel

from lambdas.dynamodb_repository import DynamoDBRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def lambda_handler(event, context):
    logger.info("Received event", event)

    try:
        table_name = os.environ['DYNAMODB_TABLE']
        region = os.environ['AWS_REGION']
        repository = DynamoDBRepository(table_name, region)
        body = json.loads(event.get("body", "{}"))
        payload = CreateGamePayload(**body)
        game = repository.put_game(payload.quest_team_size, payload.roles, payload.assassination_attempts)
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


class CreateGamePayload(BaseModel):
    quest_team_size: dict[int, int]
    roles: dict[str, list[str]]
    assassination_attempts: int
