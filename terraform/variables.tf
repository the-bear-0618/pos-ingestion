variable "gcp_project_id" {
  type        = string
  description = "The GCP project ID where resources will be deployed."
}

variable "region" {
  type        = string
  description = "The primary GCP region for resources like Cloud Run and Pub/Sub."
  default     = "us-central1"
}

variable "dataset_id" {
  type        = string
  description = "The BigQuery dataset ID for POS data."
  default     = "pos_data"
}

variable "dataset_location" {
  type        = string
  description = "The GCP location for the BigQuery dataset."
  default     = "US"
}