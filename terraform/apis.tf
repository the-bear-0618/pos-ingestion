# terraform/apis.tf

# This file ensures that all required Google Cloud APIs are enabled for the project.

resource "google_project_service" "enabled_apis" {
  project = var.gcp_project_id

  # Using for_each allows us to manage a list of APIs cleanly.
  for_each = toset([
    "run.googleapis.com",                 # Cloud Run Admin API
    "artifactregistry.googleapis.com",    # Artifact Registry API
    "cloudscheduler.googleapis.com",      # Cloud Scheduler API
    "pubsub.googleapis.com",              # Pub/Sub API
    "bigquery.googleapis.com",            # BigQuery API
    "secretmanager.googleapis.com",       # Secret Manager API
    "cloudbuild.googleapis.com",          # Cloud Build API
    "iam.googleapis.com",                 # Identity and Access Management (IAM) API
    "iamcredentials.googleapis.com",      # IAM Service Account Credentials API (for impersonation)
    "cloudresourcemanager.googleapis.com" # Cloud Resource Manager API (for project data lookups)
  ])

  service                    = each.key
  disable_dependent_services = true
}
