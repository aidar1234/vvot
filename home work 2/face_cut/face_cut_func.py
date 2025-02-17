import json
import os
import uuid

import cv2
import boto3
import numpy as np

S3_AWS_ACCESS_KEY_ID = os.getenv("S3_AWS_ACCESS_KEY_ID")
S3_AWS_SECRET_ACCESS_KEY = os.getenv("S3_AWS_SECRET_ACCESS_KEY")
FACES_BUCKET_NAME = os.getenv("FACES_BUCKET_NAME")


def build_response(status_code, body=None, headers=None, is_base64_encoded=False):
    return {
        "statusCode": status_code,
        "headers": headers,
        "isBase64Encoded": is_base64_encoded,
        "body": body
    }


def handle(event, context):
    message = event["messages"][0]["details"]["message"]
    body = json.loads(message["body"])
    print(f"Body: {body}")

    s3_session = boto3.session.Session()
    s3 = s3_session.client(
        region_name="ru-central1",
        aws_access_key_id=S3_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=S3_AWS_SECRET_ACCESS_KEY,
        service_name="s3",
        endpoint_url="https://storage.yandexcloud.net"
    )

    bucket_id = body["bucket"]
    original_key = body["original_key"]
    coords = body["coords"]
    print(f"Bucket_Id: {bucket_id}, Original_Key: {original_key}, Coords: {coords}")
    get_object = s3.get_object(Bucket=bucket_id, Key=original_key)

    image_bytes = get_object["Body"].read()
    numpy_arr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(numpy_arr, cv2.IMREAD_COLOR)

    x, y, w, h = np.array(coords, dtype=np.int32)
    face_crop = image[y:y + h, x:x + w]

    _, encoded_image = cv2.imencode('.jpg', face_crop)
    image_bytes = encoded_image.tobytes()

    new_key = str(uuid.uuid4()) + ".jpg"
    s3.put_object(Body=image_bytes, Bucket=FACES_BUCKET_NAME, Key=new_key, ContentType="image/jpeg", Metadata={
        "Original_key": original_key
    })

    return build_response(status_code=200)
