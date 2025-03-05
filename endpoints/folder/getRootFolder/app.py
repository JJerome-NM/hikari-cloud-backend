from boto3.dynamodb.conditions import Key, Attr
import json
import boto3

TABLE_NAME = "cloud_item_table"
ITEM_TABLE = boto3.resource('dynamodb', endpoint_url="http://host.docker.internal:8000").Table(TABLE_NAME)

def lambda_handler(event, context):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or "local-test-user-id"  # TODO FIX THIS

    if not user_id:
        return {'statusCode': 403, 'body': json.dumps({'error': 'User is unauthorized'})}

    response = ITEM_TABLE.scan(  # TODO Fix this bad solution (Scan has poor performance)
        FilterExpression=Attr('ownerId').eq(user_id) & Attr('parentId').not_exists()
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "items": response['Items']
        }),
    }
