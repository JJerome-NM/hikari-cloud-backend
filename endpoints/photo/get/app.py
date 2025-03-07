import json
import boto3
from boto3.dynamodb.conditions import Key
import jwt
from datetime import datetime, timedelta

TABLE_NAME = "cloud_item_table"
ITEM_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(TABLE_NAME)

S3_NAME = "hikari-cloud-test"
S3_CLIENT = boto3.client(
    's3',
    region_name='eu-central-1',
    endpoint_url='https://s3.eu-central-1.amazonaws.com'
)

JWT_SECRET = "your-secret-key" # TODO CHANGE THIS
JWT_ALGORITHM = "HS256"

def lambda_handler(event, context):
    item_id = event.get('pathParameters', {}).get('id')
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id"

    if not user_id:
        return {'statusCode': 403, 'body': json.dumps({'error': 'User is unauthorized'})}

    existing_item = ITEM_TABLE.get_item(Key={"itemId": item_id})
    if 'Item' not in existing_item:
        return {'statusCode': 404, 'body': json.dumps({'error': 'Item not found'})}

    if existing_item['Item']['ownerId'] != user_id:
        return {'statusCode': 403, 'body': json.dumps({'error': 'User is not authorized'})}

    if existing_item['Item']['type'] != "PHOTO":
        return {'statusCode': 403, 'body': json.dumps({'error': 'Item is not a photo'})}

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
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to generate presigned URL or JWT token', 'details': str(e)})
        }

    return {
        "statusCode": 200,
        "body": json.dumps({
            "item": existing_item['Item'],
            "presignedUrl": presigned_url,
            "downloadUrl": download_presigned_url,
            "shareToken": share_token
        }),
    }
