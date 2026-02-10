variable "resource_group_name" {
  default = "terraform-rg"
}

variable "location" {
  default = "Central India" # Use a region allowed by your subscription
}

variable "prefix" {
  default = "iacdemo"
}

variable "admin_username" {
  default = "azureuser"
}

variable "ssh_public_key" {
  default = "~/.ssh/id_rsa.pub"
}
