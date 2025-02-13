import os
import requests
import json
import boto3
import base64

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "Not found")
FOLDER_ID = os.getenv("FOLDER_ID", "Not found")
LLM_IAM_TOKEN = os.getenv("LLM_IAM_TOKEN", "Not found")
OCR_IAM_TOKEN = os.getenv("OCR_IAM_TOKEN", "Not found")
BUCKET_NAME = os.getenv("BUCKET_NAME", "Not found")
INSTRUCTION_OBJECT_KEY = os.getenv("INSTRUCTION_OBJECT_KEY", "Not found")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "Not found")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "Not found")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "Not found")

if (TG_BOT_TOKEN == "Not found"
        or FOLDER_ID == "Not found"
        or LLM_IAM_TOKEN == "Not found"
        or BUCKET_NAME == "Not found"
        or INSTRUCTION_OBJECT_KEY == "Not found"
        or AWS_ACCESS_KEY_ID == "Not found"
        or AWS_SECRET_ACCESS_KEY == "Not found"
        or AWS_DEFAULT_REGION == "Not found"
        or OCR_IAM_TOKEN == "Not found"):
    print(f"LOG START ERROR: Required environment variable not found")
    exit(1)


def build_response(status_code, body=None, headers=None, is_base64_encoded=False):
    return {
        "statusCode": status_code,
        "headers": headers,
        "isBase64Encoded": is_base64_encoded,
        "body": body
    }


def is_message_payload_valid(message):
    if message.get("text") is None and message.get("photo") is None:
        return False
    return True


def is_global_commands(message):
    if not (message.get("text") is None) and (
            message["text"].startswith("/start") or message["text"].startswith("/help")):
        return True
    return False


def send_telegram_message(chat_id, text):
    post = requests.post(url=f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
                         headers={"Content-Type": "application/json"}, json={"chat_id": chat_id, "text": text})
    if post.status_code != 200:
        raise ValueError(f"Request failed with status code {post.status_code}, chat_id: {chat_id}, text: {text}")


def send_telegram_get_file_message(file_id):
    get = requests.get(url=f"https://api.telegram.org/bot{TG_BOT_TOKEN}/getFile?file_id={file_id}")
    if get.status_code != 200:
        raise ValueError(f"Request getFile failed with status code {get.status_code}")
    return json.loads(get.text)


def send_telegram_get_file_content(file_path):
    get = requests.get(url=f"https://api.telegram.org/file/bot{TG_BOT_TOKEN}/{file_path}")
    if get.status_code != 200:
        raise ValueError(f"Request photos failed with status code {get.status_code}")
    return get.content


def send_yandex_gpt_message(text):
    session = boto3.session.Session()
    s3 = session.client(
        region_name="ru-central1",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        service_name="s3",
        endpoint_url="https://storage.yandexcloud.net"
    )

    get_object = s3.get_object(Bucket=BUCKET_NAME, Key=INSTRUCTION_OBJECT_KEY)
    instruction = get_object["Body"].read()
    instruction = instruction.decode("utf-8")
    print(f"LOG INSTRUCTION: {instruction}")

    try:
        gpt_response = requests.post(url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                                     json={"modelUri": f"gpt://{FOLDER_ID}/yandexgpt",
                                           "completionOptions": {"stream": False, "temperature": 1.0,
                                                                 "maxTokens": "2000",
                                                                 "reasoningOptions": {"mode": "DISABLED"}},
                                           "messages": [{"role": "system", "text": instruction},
                                                        {"role": "user", "text": text}]}, timeout=10,
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {LLM_IAM_TOKEN}"})
        if gpt_response.status_code != 200:
            return "Я не смог подготовить ответ на экзаменационный вопрос."
        gpt_response = gpt_response.json()["result"]["alternatives"][0]["message"]["text"]
        print(f"LOG GPT RESPONSE: {gpt_response}")
        return gpt_response
    except requests.exceptions.RequestException:
        return "Я не смог подготовить ответ на экзаменационный вопрос."


def send_yandex_ocr_message(file_content):
    content = base64.b64encode(file_content).decode("utf-8")
    data = {"languageCodes": ["ru", "en"],
            "content": content}

    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {OCR_IAM_TOKEN}",
               "x-folder-id": FOLDER_ID,
               "x-data-logging-enabled": "true"}
    try:
        ocr_response = requests.post(url="https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText", headers=headers,
                                     data=json.dumps(data))
        print(f"LOG OCR RESPONSE: {ocr_response}")
        if ocr_response.status_code != 200:
            return {"success": False, "text": "Я не могу обработать эту фотографию."}
        if ocr_response.json()["result"]["textAnnotation"]["fullText"] == '':
            return {"success": False, "text": "Я не могу обработать эту фотографию."}
        return {"success": True, "text": ocr_response.json()["result"]["textAnnotation"]["fullText"]}
    except Exception as e:
        print(f"LOG Exception: {e}")
        return {"success": False, "text": "Я не могу обработать эту фотографию."}


def handle_bot(event, context):
    try:
        print(f"LOG REQEUST BODY: {event["body"]}")
        body = json.loads(event["body"])
        message = body["message"]

        if not is_message_payload_valid(message):
            send_telegram_message(message["chat"]["id"],
                                  "Я могу обработать только текстовое сообщение или фотографию.")
            return build_response(status_code=200)

        if is_global_commands(message):
            send_telegram_message(message["chat"]["id"],
                                  "Я помогу подготовить ответ на экзаменационный вопрос по дисциплине "
                                  "\"Операционные системы\". \nПришлите мне фотографию с вопросом или наберите "
                                  "его текстом.")
            return build_response(status_code=200)

        if not message.get("text") is None:
            gpt_response = send_yandex_gpt_message(message["text"])
            send_telegram_message(message["chat"]["id"], gpt_response)
            return build_response(status_code=200)

        if not message.get("photo") is None:
            if not message.get("media_group_id") is None:
                send_telegram_message(message["chat"]["id"], "Я могу обработать только одну фотографию.")
                return build_response(status_code=200)
            photo = message["photo"][-1]
            file_message = send_telegram_get_file_message(photo["file_id"])
            print(f"LOG file_message: {file_message}")
            content = send_telegram_get_file_content(file_message["result"]["file_path"])
            print(f"LOG content response is success")
            ocr_message = send_yandex_ocr_message(content)
            print(f"LOG OCR MESSAGE: {ocr_message}")
            if ocr_message["success"] is False:
                send_telegram_message(message["chat"]["id"], ocr_message["text"])
                return build_response(status_code=200)
            gpt_response = send_yandex_gpt_message(ocr_message["text"])
            send_telegram_message(message["chat"]["id"], gpt_response)
            return build_response(status_code=200)

        return build_response(status_code=200)

    except KeyError as e:
        print(f"LOG KeyError: {e}")
        return build_response(status_code=400, body="Invalid Body")
    except Exception as e:
        print(f"LOG Exception: {e}")
        return build_response(status_code=500, body="Internal Server Error")
