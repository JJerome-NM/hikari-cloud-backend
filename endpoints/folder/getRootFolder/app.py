import os
from datetime import datetime, timedelta

import jwt
from boto3.dynamodb.conditions import Attr
import json
import boto3

TABLE_NAME = "cloud_item_table"
ITEM_TABLE = boto3.resource('dynamodb').Table(TABLE_NAME)

JWT_SECRET = os.getenv('JWT_SECRET')
JWT_ALGORITHM = "HS256"

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
    user_id = claims.get("sub") or "local-test-user-id-3"  # TODO FIX THIS

    if not user_id:
        return build_response(403, {'error': 'User is unauthorized'})

    response = ITEM_TABLE.scan(  # TODO Fix this bad solution (Scan has poor performance)
        FilterExpression=Attr('ownerId').eq(user_id) & Attr('parentId').not_exists()
    )

    for item in response['Items']:
        payload = {
            "itemId": item["itemId"],
            "sharedBy": user_id,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        item["shareToken"] = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return build_response(200, {
        "items": response['Items']
    })
