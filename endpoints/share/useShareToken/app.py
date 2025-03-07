import base64
import json
import boto3
import jwt
from boto3.dynamodb.conditions import Attr, Key
from pyexpat.errors import messages

ITEM_TABLE_NAME = "cloud_item_table"
ITEM_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(ITEM_TABLE_NAME)

SHARED_TABLE_NAME = "cloud_shared_table"
SHARED_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(SHARED_TABLE_NAME)

JWT_SECRET = "your-secret-key"  # TODO CHANGE THIS
JWT_ALGORITHM = "HS256"


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

    if "token" not in data:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'No token provided'})
        }

    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id"  # TODO FIX THIS

    if not user_id:
        return {'statusCode': 403, 'body': json.dumps({'error': 'No user_id provided'})}

    try:
        token_data = jwt.decode(data["token"], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception as e:
        print("Presigned URL or JWT generation error:", e)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to generate presigned URL or JWT token', 'details': str(e)})
        }

    if "itemId" not in token_data or "sharedBy" not in token_data:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Invalid token provided'})
        }

    existing_item = ITEM_TABLE.get_item(Key={"itemId": token_data["itemId"]})

    if ("Item" not in existing_item
            or "ownerId" not in existing_item["Item"]
            or existing_item["Item"]["ownerId"] != token_data["sharedBy"]):
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Invalid object data provided'})
        }

    items_in_folder = ITEM_TABLE.query(
        IndexName="ownerId-index",
        KeyConditionExpression=Key('ownerId').eq(existing_item["Item"]["ownerId"])
                               & Key('parentId').eq(existing_item["Item"]["itemId"]),
        FilterExpression=Attr('type').eq("PHOTO")
    )
    photos = items_in_folder["Items"]

    print(photos)

    with SHARED_TABLE.batch_writer() as batch:
        for photo in photos:
            batch.put_item(Item={
                "itemId": photo["itemId"],
                "userId": user_id,
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

    return {
        "statusCode": 200,
        "body": json.dumps(response),
    }
