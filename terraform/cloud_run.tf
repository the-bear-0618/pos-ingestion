# terraform/cloud_run.tf

# 1. Artifact Registry to store our container images
resource "google_artifact_registry_repository" "pos_services_repo" {
  project       = var.gcp_project_id
  location      = var.region
  repository_id = "pos-services"
  description   = "Docker repository for POS ingestion services"
  format        = "DOCKER"
}

# 2. POS Processor Cloud Run Service
# This service receives messages from the Pub/Sub push subscription.
resource "google_cloud_run_v2_service" "pos_processor_service" {
  project  = var.gcp_project_id
  name     = "pos-processor"
  location = var.region

  # Ensure the repo exists before trying to reference an image from it.
  depends_on = [google_artifact_registry_repository.pos_services_repo]

  template {
    # The service account this service will run as.
    # It has permissions to write to BigQuery.
    service_account = google_service_account.pos_processor_sa.email

    containers {
      # NOTE: The image URL is a placeholder. The CI/CD pipeline will build
      # the actual image and push it to this location in Artifact Registry.
      # We are defining the service here so Terraform can manage it and
      # provide its URL to the Pub/Sub subscription.
      image = "${var.region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.pos_services_repo.repository_id}/pos-processor:latest"

      # Define environment variables needed by the application.
      # The processor needs to know the project and dataset ID.
      env {
        name  = "GCP_PROJECT_ID"
        value = var.gcp_project_id
      }
      env {
        name  = "BIGQUERY_DATASET_ID"
        value = google_bigquery_dataset.pos_dataset.dataset_id
      }
    }
  }
}

# 3. POS Poller Cloud Run Service
# This service runs on a schedule to poll the POS API.
resource "google_cloud_run_v2_service" "pos_poller_service" {
  project  = var.gcp_project_id
  name     = "pos-poller"
  location = var.region

  # Ensure the repo exists before trying to reference an image from it.
  depends_on = [google_artifact_registry_repository.pos_services_repo]

  template {
    # The service account this service will run as.
    # It has permissions to publish to Pub/Sub and access secrets.
    service_account = google_service_account.pos_poller_sa.email

    containers {
      # NOTE: Placeholder image URL. The CI/CD pipeline will build this.
      image = "${var.region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.pos_services_repo.repository_id}/pos-poller:latest"

      # Define environment variables needed by the application.
      # The poller needs to know the project and the topic to publish to.
      env {
        name  = "GCP_PROJECT_ID"
        value = var.gcp_project_id
      }
      env {
        name  = "PUBSUB_TOPIC_ID"
        value = google_pubsub_topic.pos_events_topic.name
      }
      # The poller also needs the name of the secret to fetch API keys from.
      # We'll assume a secret named 'pos-api-credentials'.
      # You would create this secret manually or with Terraform.
      env {
        name  = "SECRET_NAME"
        value = "pos-api-credentials"
      }
    }
  }
}

# 4. Cloud Scheduler Job to trigger the Poller
# This job will invoke the poller service on a regular schedule.
resource "google_cloud_scheduler_job" "pos_poller_scheduler" {
  project     = var.gcp_project_id
  name        = "pos-poller-job"
  region      = var.region
  description = "Triggers the POS Poller Cloud Run service"
  schedule    = "*/15 * * * *" # Every 15 minutes
  time_zone   = "UTC"

  http_target {
    uri         = google_cloud_run_v2_service.pos_poller_service.uri
    http_method = "POST"

    oidc_token {
      # The scheduler needs to authenticate to invoke the Cloud Run service.
      # It will use the poller's service account to create an OIDC token.
      service_account_email = google_service_account.pos_poller_sa.email
      audience              = google_cloud_run_v2_service.pos_poller_service.uri
    }
  }

  depends_on = [google_cloud_run_v2_service.pos_poller_service]
}