import json

import boto3
from boto3.dynamodb.conditions import Key

TABLE_NAME = "cloud_item_table"
ITEM_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(TABLE_NAME)


def lambda_handler(event, context):
    item_id = event.get('pathParameters', {}).get('id')
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id"  # TODO FIX THIS

    if not user_id:
        return {'statusCode': 403, 'body': json.dumps({'error': 'User is unauthorized'})}

    existing_item = ITEM_TABLE.get_item(Key={"itemId": item_id})

    if 'Item' not in existing_item:
        return {'statusCode': 403, 'body': json.dumps({'error': 'Folder does not exist'})}

    if existing_item['Item']['ownerId'] != user_id:
        return {'statusCode': 403, 'body': json.dumps({'error': 'User is not authorized'})}

    items_in_folder = ITEM_TABLE.query(
        IndexName="ownerId-index",
        KeyConditionExpression=Key('ownerId').eq(user_id) & Key('parentId').eq(item_id)
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "folder": existing_item['Item'],
            "items": items_in_folder['Items']
        }),
    }
