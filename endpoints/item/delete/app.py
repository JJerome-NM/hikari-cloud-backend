import json
import boto3
from boto3.dynamodb.conditions import Key

TABLE_NAME = "cloud_item_table"
ITEM_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(TABLE_NAME)


def lambda_handler(event, context):
    item_id = event.get('pathParameters', {}).get('id')
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id"

    if not user_id:
        return {
            'statusCode': 403,
            'body': json.dumps({'error': 'User is unauthorized'})
        }

    item = ITEM_TABLE.get_item(Key={"itemId": item_id})
    if "Item" not in item:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Object not found'})
        }

    if item["Item"]["ownerId"] != user_id:
        return {
            'statusCode': 403,
            'body': json.dumps({'error': 'User is not authorized'})
        }

    if item["Item"]["type"] == "FOLDER":
        children = ITEM_TABLE.query(
            IndexName="ownerId-index",
            KeyConditionExpression=Key('ownerId').eq(user_id) & Key('parentId').eq(item_id)
        )

        if "Items" in children and len(children["Items"]) > 0:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Folder must be empty'})
            }

    ITEM_TABLE.delete_item(Key={"itemId": item_id})

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Object deleted",
        }),
    }
