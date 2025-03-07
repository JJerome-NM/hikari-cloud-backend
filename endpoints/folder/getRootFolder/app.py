from datetime import datetime, timedelta

import jwt
from boto3.dynamodb.conditions import Attr
import json
import boto3

TABLE_NAME = "cloud_item_table"
ITEM_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(TABLE_NAME)

JWT_SECRET = "your-secret-key"  # TODO CHANGE THIS
JWT_ALGORITHM = "HS256"

def lambda_handler(event, context):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id"  # TODO FIX THIS

    if not user_id:
        return {'statusCode': 403, 'body': json.dumps({'error': 'User is unauthorized'})}

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

    return {
        "statusCode": 200,
        "body": json.dumps({
            "items": response['Items']
        }),
    }
