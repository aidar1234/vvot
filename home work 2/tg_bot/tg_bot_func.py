import json
import requests
import os
import boto3
import re

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
S3_AWS_ACCESS_KEY_ID = os.getenv("S3_AWS_ACCESS_KEY_ID")
S3_AWS_SECRET_ACCESS_KEY = os.getenv("S3_AWS_SECRET_ACCESS_KEY")
FACES_BUCKET_NAME = os.getenv("FACES_BUCKET_NAME")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL")


def build_response(status_code, body=None, headers=None, is_base64_encoded=False):
    return {
        "statusCode": status_code,
        "headers": headers,
        "isBase64Encoded": is_base64_encoded,
        "body": body
    }


def is_message_payload_valid(message):
    if message.get("text") is None:
        return False
    return True


def send_telegram_message(chat_id, text):
    post = requests.post(url=f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
                         headers={"Content-Type": "application/json"}, json={"chat_id": chat_id, "text": text})
    if post.status_code != 200:
        raise ValueError(f"Request failed with status code {post.status_code}, chat_id: {chat_id}, text: {text}")


def send_telegram_photo(chat_id, photo):
    post = requests.post(url=f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto",
                         data={"chat_id": chat_id},
                         files={"photo": photo["Body"].read()})
    if post.status_code != 200:
        raise ValueError(f"Request failed with status code {post.status_code}, chat_id: {chat_id}")


def send_telegram_photo_url(chat_id, photo_url):
    post = requests.post(url=f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto",
                         json={"chat_id": chat_id, "photo": photo_url})
    if post.status_code != 200:
        raise ValueError(f"Request failed with status code {post.status_code}, chat_id: {chat_id}")
    return post.json()["result"]["message_id"]


def get_no_name_photo():
    session = boto3.session.Session()
    s3 = session.client(
        region_name="ru-central1",
        aws_access_key_id=S3_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=S3_AWS_SECRET_ACCESS_KEY,
        service_name='s3',
        endpoint_url='https://storage.yandexcloud.net'
    )
    list = s3.list_objects(Bucket=FACES_BUCKET_NAME)
    if list.get("Contents") is None:
        return None, None
    for key in list["Contents"]:
        object_key = key['Key']
        object = s3.get_object(Bucket=FACES_BUCKET_NAME, Key=object_key)
        object_metadata = object['Metadata']
        print(f"METADATA: {object_metadata}")
        if object_metadata.get("Name") is None:
            return object_key, object["Body"].read()
    return None, None


def get_photo_key_by_message_id(message_id):
    session = boto3.session.Session()
    s3 = session.client(
        region_name="ru-central1",
        aws_access_key_id=S3_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=S3_AWS_SECRET_ACCESS_KEY,
        service_name='s3',
        endpoint_url='https://storage.yandexcloud.net'
    )
    list = s3.list_objects(Bucket=FACES_BUCKET_NAME)
    for key in list["Contents"]:
        object_key = key['Key']
        object = s3.get_object(Bucket=FACES_BUCKET_NAME, Key=object_key)
        object_metadata = object['Metadata']
        print(f"METADATA: {object_metadata}")
        print(f"Message_id: {object_metadata.get('Message_id')}")
        if object_metadata.get('Message_id') is not None and object_metadata.get('Message_id') == str(message_id):
            return object_key
    return None


def add_message_id_metadata(object_key, message_id):
    session = boto3.session.Session()
    s3 = session.client(
        region_name="ru-central1",
        aws_access_key_id=S3_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=S3_AWS_SECRET_ACCESS_KEY,
        service_name='s3',
        endpoint_url='https://storage.yandexcloud.net'
    )

    get_object_response = s3.get_object(Bucket=FACES_BUCKET_NAME, Key=object_key)
    metadata = get_object_response["Metadata"]
    if metadata.get("Message_id") is not None:
        return
    merged_metadata = {**get_object_response["Metadata"], **{"Message_id": str(message_id)}}
    print(f"MERGED_METADATA: {merged_metadata}")
    s3.copy_object(Bucket=FACES_BUCKET_NAME, Key=object_key,
                   CopySource={'Bucket': FACES_BUCKET_NAME, 'Key': object_key},
                   Metadata=merged_metadata, MetadataDirective="REPLACE")
    print("MESSAGE_ID ADDED TO METADATA")


def add_name_metadata(object_key, name):
    session = boto3.session.Session()
    s3 = session.client(
        region_name="ru-central1",
        aws_access_key_id=S3_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=S3_AWS_SECRET_ACCESS_KEY,
        service_name='s3',
        endpoint_url='https://storage.yandexcloud.net'
    )

    get_object_response = s3.get_object(Bucket=FACES_BUCKET_NAME, Key=object_key)
    metadata = get_object_response["Metadata"]
    if metadata.get("Name") is not None:
        return
    merged_metadata = {**get_object_response["Metadata"], **{"Name": name}}
    s3.copy_object(Bucket=FACES_BUCKET_NAME, Key=object_key,
                   CopySource={'Bucket': FACES_BUCKET_NAME, 'Key': object_key},
                   Metadata=merged_metadata, MetadataDirective="REPLACE")
    print("NAME ADDED TO METADATA")


def get_photos_by_name(name):
    session = boto3.session.Session()
    s3 = session.client(
        region_name="ru-central1",
        aws_access_key_id=S3_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=S3_AWS_SECRET_ACCESS_KEY,
        service_name='s3',
        endpoint_url='https://storage.yandexcloud.net'
    )
    list = s3.list_objects(Bucket=FACES_BUCKET_NAME)
    names = []
    for key in list["Contents"]:
        object_key = key['Key']
        object = s3.get_object(Bucket=FACES_BUCKET_NAME, Key=object_key)
        object_metadata = object['Metadata']
        print(f"METADATA: {object_metadata}")
        if object_metadata.get('Name') is not None and object_metadata.get('Name') == name:
            names.append(object_key)
    return names


def get_object_by_key(object_key):
    session = boto3.session.Session()
    s3 = session.client(
        region_name="ru-central1",
        aws_access_key_id=S3_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=S3_AWS_SECRET_ACCESS_KEY,
        service_name='s3',
        endpoint_url='https://storage.yandexcloud.net'
    )
    return s3.get_object(Bucket=FACES_BUCKET_NAME, Key=object_key)


def handle(event, context):
    try:
        print(f"Event: {event}")
        body = json.loads(event["body"])
        message = body["message"]

        if not is_message_payload_valid(message):
            send_telegram_message(message["chat"]["id"], "Я могу обработать только текстовое сообщение")
            return build_response(status_code=200)

        text = message["text"]
        if text == "/getface":
            photo_key, photo = get_no_name_photo()
            if photo_key is None:
                send_telegram_message(message["chat"]["id"], "Все фото лица имеют имя")
                return build_response(status_code=200)
            url = f"{API_GATEWAY_URL}/?face={photo_key}"
            print(f"URL: {url}")
            message_id = send_telegram_photo_url(message["chat"]["id"], url)
            print(f"MESSAGE_ID: {message_id}")
            add_message_id_metadata(photo_key, message_id)
            return build_response(status_code=200)

        print(f"REPLY: {message.get("reply_to_message")}")
        if not message.get("reply_to_message") is None:
            message_id = message["reply_to_message"]["message_id"]
            print(f"MESSAGE_ID: {message_id}")
            text = message["text"]
            print(f"TEXT:{text}")
            object_key = get_photo_key_by_message_id(message_id)
            print(f"OBJECT KEY: {object_key}")
            if object_key is not None:
                add_name_metadata(object_key, text)
            return build_response(status_code=200)

        match = re.match(r"^/find\s+(.+)$", text)
        if match:
            name = match.group(1)
            print("Имя:", name)
            photos = get_photos_by_name(name)
            if len(photos) > 0:
                for photo in photos:
                    object = get_object_by_key(photo)
                    send_telegram_photo(message["chat"]["id"], object)
            else:
                send_telegram_message(message["chat"]["id"], "Нет фото с таким именем")
            return build_response(status_code=200)

        send_telegram_message(message["chat"]["id"], "Ошибка")
        return build_response(status_code=200)

    except Exception as e:
        print(f"LOG Exception: {e}")
        return build_response(status_code=200)
