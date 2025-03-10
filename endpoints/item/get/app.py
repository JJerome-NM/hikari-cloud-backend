import json
import os
from datetime import datetime, timedelta

import boto3
import jwt
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
            'Access-Control-Allow-Origin': 'https://jjerome-nm.github.io',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,PUT,DELETE'
        },
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    item_id = event.get('pathParameters', {}).get('id')
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id-3"  # TODO FIX THIS

    if not user_id:
        return build_response(403, {'error': 'User is unauthorized'})

    existing_item = ITEM_TABLE.get_item(Key={"itemId": item_id})

    if 'Item' not in existing_item:
        return build_response(403, {'error': 'Folder does not exist'})

    item_in_shared_table = SHARED_TABLE.query(
        IndexName="userId-index",
        KeyConditionExpression=Key('userId').eq(user_id) & Key('itemId').eq(item_id)
    )

    if existing_item['Item']['ownerId'] != user_id:
        if "Items" not in item_in_shared_table or len(item_in_shared_table["Items"]) == 0:
            return build_response(403, {'error': 'Item not found'})

        shared_items = SHARED_TABLE.query(
            IndexName="parentId-index",
            KeyConditionExpression=Key('userId').eq(user_id) & Key('parentId').eq(item_id)
        )

        if "Items" in shared_items and len(shared_items["Items"]) != 0:
            batch_response = ITEM_CLIENT.batch_get_item(
                RequestItems={
                    ITEM_TABLE_NAME: {
                        "Keys": [{"itemId": {"S": item["itemId"]}} for item in shared_items.get("Items", [])]
                    }
                }
            )

            shared_items = [deserialize_item(item) for item in
                            batch_response.get("Responses", {}).get(ITEM_TABLE_NAME, [])]
        else:
            shared_items = []
    else:
        shared_items = ITEM_TABLE.query(
            IndexName="ownerId-index",
            KeyConditionExpression=Key('ownerId').eq(user_id) & Key('parentId').eq(item_id)
        )["Items"]

    for item in shared_items:
        payload = {
            "itemId": item["itemId"],
            "sharedBy": user_id,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        item["shareToken"] = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return build_response(200, {
        "folder": existing_item['Item'],
        "items": shared_items
    })
