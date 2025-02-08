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
        game = repository.get_game(game_id)
        players = repository.get_players(game_id)
        res_body = {
            "id": game.id,
            "quest_team_size": game.config.quest_team_size,
            "roles": game.config.roles,
            "known_roles": game.config.known_roles,
            "assassination_attempts": game.config.assassination_attempts,
            "players": [
                {
                    "id": player.id,
                    "name": player.name,
                }
                for player in players
            ],
        }
        return {
            "statusCode": 200,
            "body": json.dumps(res_body),
        }
    except Exception as e:
        logger.error(e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
