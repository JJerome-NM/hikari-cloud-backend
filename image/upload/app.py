import base64
import boto3
import datetime
import re
import uuid
from requests_toolbelt.multipart import decoder

TABLE_NAME = "images_table"

def lambda_handler(event, context):
    print("---- Start lambda process --------------------------------------")

    headers = event.get('headers', {})
    content_type = headers.get('Content-Type') or headers.get('content-type')

    if not content_type:
        return {'statusCode': 400, 'body': 'Content-Type header is missing'}

    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id" # TODO FIX THIS

    if not user_id:
        return {'statusCode': 403, 'body': 'User is unauthorized'}
    print("User ID from Cognito:", user_id)

    body = base64.b64decode(event['body'])
    multipart_data = decoder.MultipartDecoder(body, content_type)
    file_name = None

    for part in multipart_data.parts:
        disposition = part.headers.get(b'Content-Disposition', b'').decode('utf-8')
        match = re.search(r'filename="([^"]+)"', disposition)
        if match:
            file_name = match.group(1)
            break

    if not file_name:
        return {'statusCode': 400, 'body': 'No file found in the request'}

    print(f"File name: {file_name}")

    dynamodb = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000")
    images_table = dynamodb.Table(TABLE_NAME)

    file_id = str(uuid.uuid4())

    images_table.put_item(Item={
        "id": file_id,
        "filename": file_name,
        "userId": user_id,
        "createdAt": datetime.datetime.utcnow().isoformat()
    })

    return {
        'statusCode': 200,
        'body': f'File {file_name} processed successfully'
    }
