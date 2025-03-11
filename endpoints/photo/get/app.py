import json
import os

import boto3
from boto3.dynamodb.conditions import Key
import jwt
from datetime import datetime, timedelta

TABLE_NAME = "cloud_item_table"
ITEM_TABLE = boto3.resource('dynamodb').Table(TABLE_NAME)

SHARED_TABLE_NAME = "cloud_shared_table"
SHARED_TABLE = boto3.resource('dynamodb').Table(SHARED_TABLE_NAME)

S3_NAME = os.getenv('HIKARI_CLOUD_S3BUCKET')
S3_CLIENT = boto3.client(
    's3',
    region_name='eu-central-1',
    endpoint_url='https://s3.eu-central-1.amazonaws.com'
)

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
    item_id = event.get('pathParameters', {}).get('id')
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id-3"

    if not user_id:
        return build_response(403, {'error': 'User is unauthorized'})

    existing_item = ITEM_TABLE.get_item(Key={"itemId": item_id})
    if 'Item' not in existing_item:
        return build_response(403, {'error': 'Item not found'})

    shared_items = SHARED_TABLE.query(
        KeyConditionExpression=Key('userId').eq(user_id) & Key('itemId').eq(item_id)
    )

    if existing_item['Item']['ownerId'] != user_id:
        if "Items" not in shared_items or len(shared_items["Items"]) == 0:
            return build_response(403, {'error': 'Item not found'})

    if existing_item['Item']['type'] != "PHOTO":
        return build_response(403, {'error': 'Item is not a photo'})

    try:
        presigned_url = S3_CLIENT.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_NAME, 'Key': item_id},
            ExpiresIn=3600
        )
        download_presigned_url = S3_CLIENT.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_NAME,
                'Key': item_id,
                'ResponseContentDisposition': f'attachment; filename="{existing_item["Item"]["name"]}"'
            },
            ExpiresIn=3600
        )
        payload = {
            "itemId": item_id,
            "sharedBy": user_id,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        share_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    except Exception as e:
        print("Presigned URL or JWT generation error:", e)
        return build_response(403, {'error': 'Failed to generate presigned URL or JWT token', 'details': str(e)})

    return build_response(200, {
        "item": existing_item['Item'],
        "presignedUrl": presigned_url,
        "downloadUrl": download_presigned_url,
        "shareToken": share_token
    })
