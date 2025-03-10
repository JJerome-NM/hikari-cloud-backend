import json
import boto3
from boto3.dynamodb.conditions import Key

TABLE_NAME = "cloud_item_table"
ITEM_TABLE = boto3.resource('dynamodb').Table(TABLE_NAME)

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
    item_id = event.get('pathParameters', {}).get('id')
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id-3"

    if not user_id:
        return build_response(403, {"message": "User is unauthorized"})

    item = ITEM_TABLE.get_item(Key={"itemId": item_id})
    if "Item" not in item:
        return build_response(404, {"message": "Object not found"})

    if item["Item"]["ownerId"] != user_id:
        return build_response(403, {"message": "Access is denied"})

    if item["Item"]["type"] == "FOLDER":
        children = ITEM_TABLE.query(
            IndexName="ownerId-index",
            KeyConditionExpression=Key('ownerId').eq(user_id) & Key('parentId').eq(item_id)
        )

        if "Items" in children and len(children["Items"]) > 0:
            return build_response(200, {'error': 'Folder must be empty'})

    if item["Item"]["type"] == "PHOTO":
        try:
            BUCKET.Object(item_id).delete()
        except Exception as e:
            print("S3 remove error:", e)
            return build_response(500, {'error': 'Failed to remove file from S3'})

    ITEM_TABLE.delete_item(Key={"itemId": item_id})

    return build_response(200, {
        "message": "Object deleted",
    })
