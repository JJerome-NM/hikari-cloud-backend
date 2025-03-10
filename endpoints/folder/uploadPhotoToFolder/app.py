import boto3
import base64
import json
import re
import uuid

from boto3.dynamodb.conditions import Key
from requests_toolbelt.multipart import decoder

TABLE_NAME = "cloud_item_table"
ITEM_TABLE = boto3.resource('dynamodb').Table(TABLE_NAME)

SHARED_TABLE_NAME = "cloud_shared_table"
SHARED_TABLE = boto3.resource('dynamodb').Table(SHARED_TABLE_NAME)

S3_NAME = "hikari-cloud-test"
BUCKET = boto3.resource('s3').Bucket(S3_NAME)

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
    parent_id = event.get('pathParameters', {}).get('id')
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id-3"

    if not user_id:
        return build_response(403, {"error": "User isn't authorized"})

    if "body" not in event or not event["body"]:
        return build_response(400, {"error": "Body is required"})

    headers = event.get('headers', {})
    content_type = headers.get('Content-Type') or headers.get('content-type')

    if not content_type:
        return build_response(400, {"error": "Content type is required"})

    try:
        body_bytes: bytes = base64.b64decode(event['body'])
        multipart_data = decoder.MultipartDecoder(body_bytes, content_type)
        file_name = None
        file_bytes = None
        file_content_type = None

        for part in multipart_data.parts:
            disposition = part.headers.get(b'Content-Disposition', b'').decode('utf-8')
            match = re.search(r'filename="([^"]+)"', disposition)
            if match:
                file_name = match.group(1)
                file_bytes = part.content
                file_content_type = part.headers.get(b'Content-Type', b'application/octet-stream').decode('utf-8')
                break

        if not file_name or file_bytes is None:
            return build_response(400, {"error": "No file found in the request"})
    except Exception as e:
        print("Body decode error:", e)
        return build_response(500, {"error": "Body decode error"})

    parent = ITEM_TABLE.get_item(Key={"itemId": parent_id})
    if "Item" in parent:
        if parent["Item"]["ownerId"] != user_id:
            return build_response(403, {"error": "Invalid owner id"})
        if parent["Item"]["type"] != "FOLDER":
            return build_response(403, {"error": "Invalid parent type"})

    photo_id = str(uuid.uuid4())

    new_item = {
        "itemId": photo_id,
        "ownerId": user_id,
        "name": file_name,
        "type": "PHOTO",
        "parentId": parent_id,
    }

    users = SHARED_TABLE.query(
        IndexName="parentId-index",
        KeyConditionExpression=Key("parentId").eq(parent_id)
    )

    unique_users = {user["userId"]: user for user in users["Items"]}.values()
    with SHARED_TABLE.batch_writer() as batch:
        for user in unique_users:
            batch.put_item(Item={
                "itemId": new_item["itemId"],
                "userId": user["userId"],
                "parentId": new_item["parentId"],
                "permissions": ["VIEW"]
            })

    ITEM_TABLE.put_item(Item=new_item)

    try:
        BUCKET.put_object(
            Key=f"{photo_id}",
            Body=file_bytes,
            ContentType=file_content_type
        )
    except Exception as e:
        print("S3 upload error:", e)
        return build_response(500, {"error": "Failed to upload file"})

    return build_response(200, new_item)
