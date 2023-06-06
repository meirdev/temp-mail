import json
import os
import random
import string
import time
import uuid

import boto3

dynamodb = boto3.resource("dynamodb")

table = dynamodb.Table(os.environ["MAILS_TABLE_NAME"])


def generate_name() -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(10))


def handler(event, context):
    user = uuid.uuid4().hex
    mail = generate_name()

    data = {
        "user": user,
        "mail": f"{mail}@{os.environ['DOMAIN']}",
        "ttl": int(time.time()) + int(os.environ["TTL"]),
    }

    table.put_item(
        Item=data,
    )

    return {
        "statusCode": 200,
        "headers": {
            "content-type": "application/json",
        },
        "body": json.dumps(data),
    }
