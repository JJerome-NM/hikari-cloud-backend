import json
import base64
import uuid

import boto3

TABLE_NAME = "cloud_item_table"

ITEM_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(TABLE_NAME)


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
    user_id = claims.get("sub")  # TODO FIX THIS

    if not user_id:
        return {'statusCode': 403, 'body': json.dumps({'error': 'No user_id provided'})}

    if "parentId" in data: # TODO TEST THIS PART
        parent = ITEM_TABLE.get_item(Key={"itemId": data["parentId"]})

        if "Item" in parent:
            if parent["Item"]["ownerId"] != user_id: # TODO Need check whether user have create permission
                return {'statusCode': 403, 'body': json.dumps({'error': 'Invalid owner id'})}

            if parent["Item"]["type"] != "FOLDER":
                return {'statusCode': 404, 'body': json.dumps({'error': 'Invalid parent type'})}


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

    return {
        "statusCode": 200,
        "body": json.dumps(new_item)
    }
