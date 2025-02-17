import os
import json
import cv2
import boto3
import numpy as np

S3_AWS_ACCESS_KEY_ID = os.getenv("S3_AWS_ACCESS_KEY_ID")
S3_AWS_SECRET_ACCESS_KEY = os.getenv("S3_AWS_SECRET_ACCESS_KEY")
MQ_AWS_ACCESS_KEY_ID = os.getenv("MQ_AWS_ACCESS_KEY_ID")
MQ_AWS_SECRET_ACCESS_KEY = os.getenv("MQ_AWS_SECRET_ACCESS_KEY")
MQ_QUEUE_NAME = os.getenv("MQ_QUEUE_NAME")


def build_response(status_code, body=None, headers=None, is_base64_encoded=False):
    return {
        "statusCode": status_code,
        "headers": headers,
        "isBase64Encoded": is_base64_encoded,
        "body": body
    }


def handle(event, context):
    details = event["messages"][0]["details"]
    bucket_id = details["bucket_id"]
    object_id = details["object_id"]
    print(f"Bucket_Id: {bucket_id}, Object_Id: {object_id}")

    s3_session = boto3.session.Session()
    s3 = s3_session.client(
        region_name="ru-central1",
        aws_access_key_id=S3_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=S3_AWS_SECRET_ACCESS_KEY,
        service_name="s3",
        endpoint_url="https://storage.yandexcloud.net"
    )

    get_object = s3.get_object(Bucket=bucket_id, Key=object_id)
    image_bytes = get_object["Body"].read()
    numpy_arr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(numpy_arr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    if len(faces) == 0:
        print("Faces not found")
        return build_response(status_code=200)

    mq_session = boto3.session.Session()
    client = mq_session.client(
        aws_access_key_id=MQ_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=MQ_AWS_SECRET_ACCESS_KEY,
        service_name="sqs",
        endpoint_url="https://message-queue.api.cloud.yandex.net",
        region_name="ru-central1"
    )
    queue_url = client.get_queue_url(QueueName=MQ_QUEUE_NAME).get("QueueUrl")

    for i in range(0, len(faces)):
        x, y, w, h = map(int, faces[i])
        body = json.dumps({
            "bucket": bucket_id,
            "original_key": object_id,
            "coords": [x, y, w, h],
        })
        client.send_message(
            QueueUrl=queue_url,
            MessageBody=body
        )
        print(f"Successfully sent test message to queue. Body: {body}")

    return build_response(status_code=200)
