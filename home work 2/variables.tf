variable "CLOUD_ID" {
  type        = string
  description = "Cloud ID"
}

variable "FOLDER_ID" {
  type        = string
  description = "Folder ID"
}

variable "TG_BOT_TOKEN" {
  type = string
}

variable "S3_AWS_ACCESS_KEY_ID" {
  type = string
}

variable "S3_AWS_SECRET_ACCESS_KEY" {
  type = string
}

variable "MQ_AWS_ACCESS_KEY_ID" {
  type = string
}

variable "MQ_AWS_SECRET_ACCESS_KEY" {
  type = string
}

variable "MQ_QUEUE_NAME" {
  type = string
}

variable "FACES_BUCKET_NAME" {
  type = string
}

variable "MQ_SERVICE_ACCOUNT_ID" {
  type = string
}

variable "STORAGE_VIEWER_ACCOUNT_ID" {
  type = string
}

variable "MQ_ACCESS_KEY" {
  type = string
}

variable "MQ_SECRET_KEY" {
  type = string
}

variable "INVOKE_FUNCTION_ACCOUNT_ID" {
  type = string
}
