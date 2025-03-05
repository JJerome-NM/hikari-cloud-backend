import json
import base64
import re
import uuid

import boto3
from requests_toolbelt.multipart import decoder

TABLE_NAME = "cloud_item_table"

ITEM_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(TABLE_NAME)


def lambda_handler(event, context):
    parent_id = event.get('pathParameters', {}).get('id')
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id"  # TODO FIX THIS

    if not user_id:
        return {'statusCode': 403, 'body': json.dumps({'error': "User isn't authorized"})}


    if "body" not in event or not event["body"]:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No body provided'})
        }

    headers = event.get('headers', {})
    content_type = headers.get('Content-Type') or headers.get('content-type')

    if not content_type:
        return {'statusCode': 400, 'body': json.dumps({'error': 'No "Content-Type" provided'})}

    try:
        body: bytes = base64.b64decode(event['body'])
        multipart_data = decoder.MultipartDecoder(body, content_type)
        file_name = None

        for part in multipart_data.parts:
            disposition = part.headers.get(b'Content-Disposition', b'').decode('utf-8')
            match = re.search(r'filename="([^"]+)"', disposition)
            if match:
                file_name = match.group(1)
                break

        if not file_name:
            return {'statusCode': 400, 'body': 'No file found in the request'}
    except Exception as e:
        print("Body decode error:", e)
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid body format'})
        }

    parent = ITEM_TABLE.get_item(Key={"itemId": parent_id})

    if "Item" in parent:
        if parent["Item"]["ownerId"] != user_id:  # TODO Need check whether user have create permission
            return {'statusCode': 403, 'body': json.dumps({'error': 'Invalid owner id'})}

        if parent["Item"]["type"] != "FOLDER":
            return {'statusCode': 404, 'body': json.dumps({'error': 'Invalid parent type'})}

    photo_id = str(uuid.uuid4())

    new_item = {
        "itemId": photo_id,
        "ownerId": user_id,
        "name": file_name,
        "type": "PHOTO",
        "parentId": parent_id,
    }

    ITEM_TABLE.put_item(Item=new_item)

    return {
        "statusCode": 200,
        "body": json.dumps(new_item)
    }
