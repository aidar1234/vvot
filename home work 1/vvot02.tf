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
  cloud_id                 = var.cloud_id
  folder_id                = var.folder_id
  zone                     = "ru-central-a"
  service_account_key_file = "/home/aidar/.yc-keys/key.json"
}

provider "telegram" {
  bot_token = var.tg_bot_key
}

resource "archive_file" "archive_function_content" {
  type        = "zip"
  source_dir  = "src"
  output_path = "handler.zip"
}

resource "yandex_function" "function" {
  name              = "vvot02-1-function"
  runtime           = "python312"
  entrypoint        = "vvot02.handle_bot"
  memory            = 128
  execution_timeout = "12"
  user_hash         = archive_file.archive_function_content.output_sha
  content {
    zip_filename = archive_file.archive_function_content.output_path
  }
  environment = {
    FOLDER_ID : var.folder_id,
    TG_BOT_TOKEN : var.TG_BOT_TOKEN,
    LLM_IAM_TOKEN : var.LLM_IAM_TOKEN,
    AWS_ACCESS_KEY_ID : var.AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY : var.AWS_SECRET_ACCESS_KEY,
    AWS_DEFAULT_REGION : var.AWS_DEFAULT_REGION,
    INSTRUCTION_OBJECT_KEY : var.INSTRUCTION_OBJECT_KEY,
    BUCKET_NAME : var.BUCKET_NAME,
    OCR_IAM_TOKEN : var.OCR_IAM_TOKEN
  }
}

resource "yandex_function_iam_binding" "function_iam_binding" {
  function_id = yandex_function.function.id
  role        = "serverless.functions.invoker"
  members = [
    "system:allUsers",
  ]
}

resource "yandex_storage_object" "instruction" {
  bucket = var.BUCKET_NAME
  key    = "instruction.txt"
  acl    = "private"
  source = "instruction.txt"
}

resource "telegram_bot_webhook" "tg_bot_webhook" {
  url = "https://functions.yandexcloud.net/${yandex_function.function.id}"
}
