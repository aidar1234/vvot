import os
import requests
import json


def build_response(status_code, body, headers=None, is_base64_encoded=False):
    return {
        "statusCode": status_code,
        "headers": headers,
        "isBase64Encoded": is_base64_encoded,
        "body": body
    }


def handle_bot(event, context):
    return build_response(200, json.dumps({
        "event": event,
        "context": context
    }, default=vars))
