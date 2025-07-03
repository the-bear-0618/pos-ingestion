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
      # NOTE: Using a public placeholder image for initial setup.
      # This allows Terraform to create the service successfully before our
      # application image has been built. The CI/CD pipeline will replace
      # this with the correct application image on the first deployment.
      # The image and environment variables will be managed by the CI/CD pipeline.
      # We use a public placeholder for the initial creation by Terraform.
      image = "us-docker.pkg.dev/cloudrun/container/hello"
    }
  }
}

# 3. POS Poller Cloud Run Service
# This service runs on a schedule to poll the POS API.
resource "google_cloud_run_v2_service" "pos_poller_service" {
  project  = var.gcp_project_id
  name     = "pos-poller"
  location = var.region
  deletion_protection = false

  # Ensure the repo exists before trying to reference an image from it.
  depends_on = [google_artifact_registry_repository.pos_services_repo]

  template {
    # The service account this service will run as.
    # It has permissions to publish to Pub/Sub and access secrets.
    service_account = google_service_account.pos_poller_sa.email

    containers {
      # NOTE: Using a public placeholder image for initial setup.
      # The CI/CD pipeline will replace this with the correct application
      # image on the first deployment.
      # The image will be managed by the CI/CD pipeline. We use a public
      # placeholder for the initial creation by Terraform.
      image = "us-docker.pkg.dev/cloudrun/container/hello"
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
    # Target the /sync endpoint to trigger the actual polling logic.
    uri         = "${google_cloud_run_v2_service.pos_poller_service.uri}/sync"
    http_method = "POST"

    # The body of the POST request, telling the poller what to do.
    # This example syncs all endpoints for the last 7 days.
    # The body must be base64-encoded for the Terraform resource.
    body = base64encode(jsonencode({
      "endpoints" : "all",
      "days_back" : 7
    }))

    oidc_token {
      # The scheduler needs to authenticate to invoke the Cloud Run service.
      # It will use the poller's service account to create an OIDC token.
      service_account_email = google_service_account.pos_poller_sa.email
      audience              = google_cloud_run_v2_service.pos_poller_service.uri
    }

    # Set the correct header for a JSON request body.
    headers = {
      "Content-Type" = "application/json"
    }
  }

  depends_on = [google_cloud_run_v2_service.pos_poller_service]
}