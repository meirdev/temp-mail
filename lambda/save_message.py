import json
import os
import time

import boto3

dynamodb = boto3.resource("dynamodb")

table = dynamodb.Table(os.environ["MESSAGES_TABLE_NAME"])

# https://docs.aws.amazon.com/ses/latest/dg/receiving-email-action-lambda-event.html

def handler(event, context):
    for record in event["Records"]:
        message = json.loads(record["Sns"]["Message"])
        mail = message["mail"]

        for destination in mail["destination"]:
            table.put_item(
                Item={
                    "destination": destination,
                    "timestamp": mail["timestamp"],
                    "message": message,
                    "ttl": int(time.time()) + int(os.environ["TTL"]),
                }
            )
