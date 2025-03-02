import json
import base64
import re
import uuid

import boto3

TABLE_NAME = "folder_table"
UUID_REGEX = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', re.IGNORECASE)

person_table = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(TABLE_NAME)

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

    if "folderName" not in data or not isinstance(data["folderName"], str):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'folderName must be provided and be a string'})
        }

    if "parentFolderId" not in data or not isinstance(data["parentFolderId"], str):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'parentFolderId must be provided and be a string'})
        }

    if not UUID_REGEX.match(data["parentFolderId"]):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'parentFolderId is not a valid UUID'})
        }

    print("Valid request data:", data)

    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id" # TODO FIX THIS

    if not user_id:
        return {'statusCode': 403, 'body': 'User is unauthorized'}


    folder_id = str(uuid.uuid4())

    person_table.put_item(
        Item={
            "folderId": folder_id,
            "ownerId": user_id,
            "folderName": data["folderName"],
            "parentFolderId": data["parentFolderId"],
        }
    )

    new_folder = person_table.get_item(Key={"folderId": folder_id})

    return {
        "statusCode": 200,
        "body": json.dumps(new_folder["Item"])
    }