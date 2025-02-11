terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
  }
  required_version = ">= 0.13"
}

provider "yandex" {
  cloud_id  = "b1g71e95h51okii30p25"
  folder_id = "b1g3ckinbg76okbv00oi"
  zone      = "ru-central-a"
  token     = "~/.yc-keys/key.json"
}
