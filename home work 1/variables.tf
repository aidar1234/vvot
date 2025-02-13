variable "cloud_id" {
  type        = string
  description = "Cloud ID"
}

variable "folder_id" {
  type        = string
  description = "Folder ID"
}

variable "tg_bot_key" {
  type        = string
  description = "Telegram Bot Key"
}

variable "TG_BOT_TOKEN" {
  type = string
}

variable "LLM_IAM_TOKEN" {
  type = string
}

variable "AWS_ACCESS_KEY_ID" {
  type = string
}

variable "AWS_SECRET_ACCESS_KEY" {
  type = string
}

variable "AWS_DEFAULT_REGION" {
  type = string
}

variable "INSTRUCTION_OBJECT_KEY" {
  type = string
}

variable "BUCKET_NAME" {
  type = string
}

variable "OCR_IAM_TOKEN" {
  type = string
}
