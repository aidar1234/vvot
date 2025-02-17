terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
    telegram = {
      source = "yi-jiayu/telegram"
    }
  }
  required_version = ">= 0.13"
}

provider "yandex" {
  cloud_id                 = var.CLOUD_ID
  folder_id                = var.FOLDER_ID
  zone                     = "ru-central-a"
  service_account_key_file = "/home/aidar/.yc-keys/key.json"
}

provider "telegram" {
  bot_token = var.TG_BOT_TOKEN
}

resource "archive_file" "archive_detection_function_content" {
  type        = "zip"
  source_dir  = "face_detection"
  output_path = "face_detection.zip"
}

resource "archive_file" "archive_cut_function_content" {
  type        = "zip"
  source_dir  = "face_cut"
  output_path = "face_cut.zip"
}

resource "archive_file" "archive_tg_bot_function_content" {
  type        = "zip"
  source_dir  = "tg_bot"
  output_path = "tg_bot.zip"
}

resource "yandex_function" "face-detection-function" {
  name              = "vvot02-detection-function"
  runtime           = "python312"
  entrypoint        = "face_detection_func.handle"
  memory            = 128
  execution_timeout = "10"
  user_hash         = archive_file.archive_detection_function_content.output_sha
  content {
    zip_filename = archive_file.archive_detection_function_content.output_path
  }
  environment = {
    S3_AWS_ACCESS_KEY_ID : var.S3_AWS_ACCESS_KEY_ID,
    S3_AWS_SECRET_ACCESS_KEY : var.S3_AWS_SECRET_ACCESS_KEY,
    MQ_AWS_ACCESS_KEY_ID : var.MQ_AWS_ACCESS_KEY_ID,
    MQ_AWS_SECRET_ACCESS_KEY : var.MQ_AWS_SECRET_ACCESS_KEY,
    MQ_QUEUE_NAME : var.MQ_QUEUE_NAME,
  }
}

resource "yandex_function" "face-cut-function" {
  name              = "vvot02-cut-function"
  runtime           = "python312"
  entrypoint        = "face_cut_func.handle"
  memory            = 128
  execution_timeout = "10"
  user_hash         = archive_file.archive_cut_function_content.output_sha
  content {
    zip_filename = archive_file.archive_cut_function_content.output_path
  }
  environment = {
    S3_AWS_ACCESS_KEY_ID : var.S3_AWS_ACCESS_KEY_ID,
    S3_AWS_SECRET_ACCESS_KEY : var.S3_AWS_SECRET_ACCESS_KEY,
    FACES_BUCKET_NAME: var.FACES_BUCKET_NAME
  }
}

resource "yandex_function" "tg-bot-function" {
  name              = "vvot02-tg-bot-function"
  runtime           = "python312"
  entrypoint        = "tg_bot_func.handle"
  memory            = 128
  execution_timeout = "10"
  user_hash         = archive_file.archive_tg_bot_function_content.output_sha
  content {
    zip_filename = archive_file.archive_tg_bot_function_content.output_path
  }
  environment = {
    S3_AWS_ACCESS_KEY_ID : var.S3_AWS_ACCESS_KEY_ID,
    S3_AWS_SECRET_ACCESS_KEY : var.S3_AWS_SECRET_ACCESS_KEY,
    TG_BOT_TOKEN : var.TG_BOT_TOKEN,
    FACES_BUCKET_NAME : var.FACES_BUCKET_NAME,
    API_GATEWAY_URL : "https://${yandex_api_gateway.api-gateway.domain}"
  }
}

resource "yandex_function_iam_binding" "tg-bot-function_iam_binding" {
  function_id = yandex_function.tg-bot-function.id
  role        = "serverless.functions.invoker"
  members = [
    "system:allUsers",
  ]
}

resource "yandex_storage_bucket" "photos-bucket" {
  bucket = "vvot02-photos"
  acl = "private"
}

resource "yandex_storage_bucket" "faces-bucket" {
  bucket = "vvot02-faces"
  acl = "private"
}

resource "yandex_function_trigger" "create-trigger" {
  name = "vvot02-photo-create-trigger"
  object_storage {
    batch_cutoff = "0"
    bucket_id    = yandex_storage_bucket.photos-bucket.id
    create       = true
    batch_size = "1"
    suffix       = ".jpg"
  }
  function {
    id = yandex_function.face-detection-function.id
    tag = "$latest"
    service_account_id = var.INVOKE_FUNCTION_ACCOUNT_ID
    retry_attempts = "1"
    retry_interval = "10"
  }
}

resource "yandex_message_queue" "mq" {
  name = var.MQ_QUEUE_NAME
  visibility_timeout_seconds = 30
  access_key = var.MQ_ACCESS_KEY
  secret_key = var.MQ_SECRET_KEY
}

resource "yandex_function_trigger" "mq-trigger" {
  name = "vvot02-mq-trigger"
  message_queue {
    queue_id = yandex_message_queue.mq.arn
    batch_cutoff       = "0"
    service_account_id = var.MQ_SERVICE_ACCOUNT_ID
    batch_size = "256"
  }
  function {
    id = yandex_function.face-cut-function.id
    tag = "$latest"
    service_account_id = var.INVOKE_FUNCTION_ACCOUNT_ID
  }
}

resource "yandex_api_gateway" "api-gateway" {
  name = "vvot02-api-gateway"
  spec = <<-EOT
openapi: "3.0.0"
info:
  version: 1.0.0
  title: Test API
paths:
  /:
    get:
      parameters:
        - name: face
          in: query
          required: true
          schema:
            type: string
      x-yc-apigateway-integration:
        type: object_storage
        bucket: ${yandex_storage_bucket.faces-bucket.id}
        object: "{face}"
        service_account_id: ${var.STORAGE_VIEWER_ACCOUNT_ID}
        pass_headers: true
EOT
}

resource "telegram_bot_webhook" "tg_bot_webhook" {
  url = "https://functions.yandexcloud.net/${yandex_function.tg-bot-function.id}"
}
