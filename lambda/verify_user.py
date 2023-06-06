import os

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")

table = dynamodb.Table(os.environ["MAILS_TABLE_NAME"])

# https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-lambda-authorizer.html

def handler(event, context):
    user = event["identitySource"][0]

    res = table.query(
        KeyConditionExpression=Key("user").eq(user),
        IndexName="temp-mail-user-mail-index",
    )

    if len(res["Items"]) == 0:
        return {
            "isAuthorized": False,
        }

    return {
        "isAuthorized": True,
        "context": {
            "mail": res["Items"][0]["mail"],
        }
    }
