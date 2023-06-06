import decimal
import json
import os

import boto3

dynamodb = boto3.resource("dynamodb")

table = dynamodb.Table(os.environ["MESSAGES_TABLE_NAME"])


def json_type_error_handler(obj):
    if isinstance(obj, decimal.Decimal):
        return int(obj)
    raise TypeError


def handler(event, context):
    mail = event["requestContext"]["authorizer"]["lambda"]["mail"]

    response = table.query(
        KeyConditionExpression="destination = :destination",
        ExpressionAttributeValues={
            ":destination": mail,
        },
    )

    items = response["Items"]

    return {
        "statusCode": 200,
        "headers": {
            "content-type": "application/json",
        },
        "body": json.dumps(items, default=json_type_error_handler),
    }
