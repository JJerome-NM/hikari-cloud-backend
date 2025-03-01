import json
import boto3

TABLE_NAME = "folder_table"

def lambda_handler(event, context):
    print("---- Start local logs --------------------------------------")
    folder_id = event.get('pathParameters', {}).get('id')
    print("Folder ID:", folder_id)

    person_table = (boto3
                    .resource('dynamodb', endpoint_url="http://host.docker.internal:8000") # TODO Change this
                    .Table(TABLE_NAME))

    list_items = person_table.scan()

    return {
        "statusCode": 200,
        "body": json.dumps(list_items['Items']),
    }
