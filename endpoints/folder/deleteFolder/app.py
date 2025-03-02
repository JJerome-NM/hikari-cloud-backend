import json

import boto3

TABLE_NAME = "cloud_item_table"

ITEM_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(TABLE_NAME)

def lambda_handler(event, context):
    folder_id = event.get('pathParameters', {}).get('id')
    print("Folder ID:", folder_id)
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id" # TODO FIX THIS

    if not user_id:
        return {'statusCode': 403, 'body': json.dumps({'error': 'User is unauthorized'})}

    item = ITEM_TABLE.get_item(Key={"itemId": folder_id})

    if "Item" not in item:
        return {'statusCode': 404, 'body': json.dumps({'error': 'Folder not found'})}

    if item["Item"]["ownerId"] != user_id:
        return {'statusCode': 403, 'body': json.dumps({'error': 'User is not authorized'})}

    ITEM_TABLE.delete_item(Key={"itemId": folder_id})

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Folder deleted",
        }),
    }
