import json
import base64
import uuid

import boto3

TABLE_NAME = "cloud_item_table"

item_table = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(TABLE_NAME)


def lambda_handler(event, context):
    if "body" not in event or not event["body"]:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No body provided'})
        }

    try:
        body_decoded = base64.b64decode(event['body']).decode('utf-8')
        data = json.loads(body_decoded)
    except Exception as e:
        print("Body decode error:", e)
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid body format'})
        }

    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id"  # TODO FIX THIS

    if not user_id:
        return {'statusCode': 403, 'body': 'User is unauthorized'}

    folder_id = str(uuid.uuid4())

    new_item = {
        "itemId": folder_id,
        "ownerId": user_id,
        "name": data["name"],
        "type": "FOLDER",
    }

    if "parentId" in data:
        new_item["parentId"] = data["parentId"]

    item_table.put_item(Item=new_item)

    item = item_table.get_item(Key={"itemId": folder_id})

    return {
        "statusCode": 200,
        "body": json.dumps(item["Item"])
    }
