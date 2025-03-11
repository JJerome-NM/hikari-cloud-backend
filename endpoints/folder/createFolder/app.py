import json
import base64
import os
import uuid

import boto3

TABLE_NAME = "cloud_item_table"

ITEM_TABLE = boto3.resource('dynamodb').Table(TABLE_NAME)


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
    if "body" not in event or not event["body"]:
        return build_response(400, {"error": "body is required"})

    try:
        if event.get("isBase64Encoded", False):
            body_decoded = base64.b64decode(event['body']).decode('utf-8')
        else:
            body_decoded = event['body']
        data = json.loads(body_decoded)
    except Exception as e:
        print("Body decode error:", e)
        return build_response(400, {"error": "body decode error"})


    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub")  # TODO FIX THIS

    if not user_id:
        return build_response(400, {"error": "user_id is required"})

    if "parentId" in data: # TODO TEST THIS PART
        parent = ITEM_TABLE.get_item(Key={"itemId": data["parentId"]})

        if "Item" in parent:
            if parent["Item"]["ownerId"] != user_id: # TODO Need check whether user have create permission
                return build_response(403, {"error": "user_id is forbidden"})

            if parent["Item"]["type"] != "FOLDER":
                return build_response(403, {"error": "user_id is forbidden"})


    folder_id = str(uuid.uuid4())

    new_item = {
        "itemId": folder_id,
        "ownerId": user_id,
        "name": data["name"],
        "type": "FOLDER",
    }

    if "parentId" in data:
        new_item["parentId"] = data["parentId"]

    ITEM_TABLE.put_item(Item=new_item)

    return build_response(200, {"itemId": folder_id})
