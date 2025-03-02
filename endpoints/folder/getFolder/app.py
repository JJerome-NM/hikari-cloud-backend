import json
import re

import boto3
from boto3.dynamodb.conditions import Key

FOLDERS_TABLE_NAME = "folder_table"
PHOTOS_TABLE_NAME = "photo_table"
UUID_REGEX = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', re.IGNORECASE)

FOLDERS_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(FOLDERS_TABLE_NAME)
PHOTOS_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(PHOTOS_TABLE_NAME)


def lambda_handler(event, context):
    folder_id = event.get('pathParameters', {}).get('id')
    print("Folder ID:", folder_id)

    if not UUID_REGEX.match(folder_id):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Folder if is not a valid UUID'})
        }

    existing_folder = FOLDERS_TABLE.get_item(Key={"folderId": folder_id})
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
