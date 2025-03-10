import base64
import json
import os

import boto3
import jwt
from boto3.dynamodb.conditions import Attr, Key

ITEM_TABLE_NAME = "cloud_item_table"
ITEM_TABLE = boto3.resource('dynamodb').Table(ITEM_TABLE_NAME)

SHARED_TABLE_NAME = "cloud_shared_table"
SHARED_TABLE = boto3.resource('dynamodb').Table(SHARED_TABLE_NAME)

JWT_SECRET = os.getenv('JWT_SECRET')
JWT_ALGORITHM = "HS256"

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
    if "body" not in event or not event["body"]:
        return build_response(400, {'error': 'No body provided'})

    try:
        body_decoded = base64.b64decode(event['body']).decode('utf-8')
        data = json.loads(body_decoded)
    except Exception as e:
        print("Body decode error:", e)
        return build_response(400, {'error': 'Invalid body format'})

    if "token" not in data:
        return build_response(400, {'error': 'No token provided'})

    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id-3"  # TODO FIX THIS

    if not user_id:
        return build_response(400, {'error': 'No user_id provided'})

    try:
        token_data = jwt.decode(data["token"], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception as e:
        print("Presigned URL or JWT generation error:", e)
        return build_response(400, {'error': 'Failed to generate presigned URL or JWT token', 'details': str(e)})

    if "itemId" not in token_data or "sharedBy" not in token_data:
        return build_response(400, {'error': 'Invalid token provided'})

    existing_item = ITEM_TABLE.get_item(Key={"itemId": token_data["itemId"]})

    if ("Item" not in existing_item
            or "ownerId" not in existing_item["Item"]
            or existing_item["Item"]["ownerId"] != token_data["sharedBy"]):
        return build_response(400, {'error': 'Invalid object data provided'})

    items_in_folder = ITEM_TABLE.query(
        IndexName="ownerId-index",
        KeyConditionExpression=Key('ownerId').eq(existing_item["Item"]["ownerId"])
                               & Key('parentId').eq(existing_item["Item"]["itemId"]),
        FilterExpression=Attr('type').eq("PHOTO")
    )
    photos = items_in_folder["Items"]

    with SHARED_TABLE.batch_writer() as batch:
        for photo in photos:
            batch.put_item(Item={
                "itemId": photo["itemId"],
                "userId": user_id,
                "parentId": photo["parentId"],
                "permissions": ["VIEW"]
            })

    SHARED_TABLE.put_item(Item={
        "itemId": token_data["itemId"],
        "userId": user_id,
        "permissions": ["VIEW"]
    })

    response = {}
    if existing_item["Item"]["type"] == "FOLDER":
        response["folder"] = existing_item["Item"]

    return build_response(200, response)
