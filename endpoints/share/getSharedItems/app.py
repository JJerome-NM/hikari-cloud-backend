import base64
import json
import boto3
import jwt
from boto3.dynamodb.conditions import Attr, Key
from boto3.dynamodb.types import TypeDeserializer

ITEM_TABLE_NAME = "cloud_item_table"
ITEM_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(ITEM_TABLE_NAME)
ITEM_CLIENT = boto3.client('dynamodb', endpoint_url="http://host.docker.internal:8000")

SHARED_TABLE_NAME = "cloud_shared_table"
SHARED_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(SHARED_TABLE_NAME)

JWT_SECRET = "your-secret-key"  # TODO CHANGE THIS
JWT_ALGORITHM = "HS256"

deserializer = TypeDeserializer()

def deserialize_item(item):
    return {k: deserializer.deserialize(v) for k, v in item.items()}

def lambda_handler(event, context):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id"  # TODO FIX THIS

    if not user_id:
        return {'statusCode': 403, 'body': json.dumps({'error': 'No user_id provided'})}

    shared_items = SHARED_TABLE.query(
        KeyConditionExpression=Key('userId').eq(user_id)
    )

    batch_response = ITEM_CLIENT.batch_get_item(
            RequestItems={
                ITEM_TABLE_NAME: {
                    "Keys": [{"itemId": {"S": item["itemId"]}} for item in shared_items.get("Items", [])]
                }
            }
        )
    items = [deserialize_item(item) for item in batch_response.get("Responses", {}).get(ITEM_TABLE_NAME, [])]

    return {
        "statusCode": 200,
        "body": json.dumps({
            "items": items,
        }),
    }
