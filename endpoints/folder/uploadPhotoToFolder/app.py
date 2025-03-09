import boto3
import base64
import json
import re
import uuid

from boto3.dynamodb.conditions import Key
from requests_toolbelt.multipart import decoder

TABLE_NAME = "cloud_item_table"
ITEM_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(TABLE_NAME)

SHARED_TABLE_NAME = "cloud_shared_table"
SHARED_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(SHARED_TABLE_NAME)

S3_NAME = "hikari-cloud-test"
BUCKET = boto3.resource('s3').Bucket(S3_NAME)

def lambda_handler(event, context):
    parent_id = event.get('pathParameters', {}).get('id')
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id-3"

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
            return {'statusCode': 400, 'body': json.dumps({'error': 'No file found in the request'})}
    except Exception as e:
        print("Body decode error:", e)
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid body format'})
        }

    parent = ITEM_TABLE.get_item(Key={"itemId": parent_id})
    if "Item" in parent:
        if parent["Item"]["ownerId"] != user_id:
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
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to upload file to S3'})
        }

    return {
        "statusCode": 200,
        "body": json.dumps(new_item)
    }
