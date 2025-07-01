terraform {
  backend "gcs" {
    bucket  = "ghcp-restaurant-data-tf-state"
    prefix  = "terraform/state"
  }
}