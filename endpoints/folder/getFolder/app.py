import json

import boto3
from boto3.dynamodb.conditions import Key

FOLDERS_TABLE_NAME = "folder_table"
PHOTOS_TABLE_NAME = "photo_table"

FOLDERS_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(FOLDERS_TABLE_NAME)
PHOTOS_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(PHOTOS_TABLE_NAME)


def lambda_handler(event, context):
    folder_id = event.get('pathParameters', {}).get('id')
    # print("Folder ID:", folder_id)

    # TODO Owner Sharing

    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id" # TODO FIX THIS

    if not user_id:
        return {'statusCode': 403, 'body': json.dumps({'error': 'User is unauthorized'})}


    existing_folder = FOLDERS_TABLE.get_item(Key={"folderId": folder_id})

    if 'Item' not in existing_folder:
        return {'statusCode': 403, 'body': json.dumps({'error': 'Folder does not exist'})}

    if existing_folder['Item']['ownerId'] != user_id:
        return {'statusCode': 403, 'body': json.dumps({'error': 'User is not authorized'})}


    photos_in_folder = PHOTOS_TABLE.query(
        IndexName="folderId-index",
        KeyConditionExpression=Key("folderId").eq(folder_id)
    )

    if "Item" not in existing_folder:
        return {
            "statusCode": 404,
            "body": json.dumps({'error': f"item with id {folder_id} not found"})
        }

    return {
        "statusCode": 200,
        "body": json.dumps({
            "folder": existing_folder['Item'],
            "photos": photos_in_folder['Items']
        }),
    }
