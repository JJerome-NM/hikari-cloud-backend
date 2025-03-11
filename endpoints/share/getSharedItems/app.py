import json
import os

import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeDeserializer

ITEM_TABLE_NAME = "cloud_item_table"
ITEM_TABLE = boto3.resource('dynamodb').Table(ITEM_TABLE_NAME)
ITEM_CLIENT = boto3.client('dynamodb')

SHARED_TABLE_NAME = "cloud_shared_table"
SHARED_TABLE = boto3.resource('dynamodb').Table(SHARED_TABLE_NAME)

JWT_SECRET = os.getenv('JWT_SECRET')
JWT_ALGORITHM = "HS256"

deserializer = TypeDeserializer()


def deserialize_item(item):
    return {k: deserializer.deserialize(v) for k, v in item.items()}


def build_response(status: int, body):
    return {
        "statusCode": status,
        "headers": {
            'Access-Control-Allow-Origin': os.getenv('HIKARI_CLOUD_FRONTEND'),
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,PUT,DELETE'
        },
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub")  # TODO FIX THIS

    if not user_id:
        return build_response(403, {'error': 'No user_id provided'})

    shared_items = SHARED_TABLE.query(
        KeyConditionExpression=Key('userId').eq(user_id)
    )

    if "Items" not in shared_items or len(shared_items["Items"]) == 0:
        return build_response(200, [])

    batch_response = ITEM_CLIENT.batch_get_item(
        RequestItems={
            ITEM_TABLE_NAME: {
                "Keys": [{"itemId": {"S": item["itemId"]}} for item in shared_items.get("Items", [])]
            }
        }
    )
    items = [deserialize_item(item) for item in batch_response.get("Responses", {}).get(ITEM_TABLE_NAME, [])]

    return build_response(200, {
        "items": items,
    })
