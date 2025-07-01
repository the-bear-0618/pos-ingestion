# terraform/iam.tf
#
# Defines all Service Accounts and IAM permissions for the project.

# Data block to get the Project Number, which is needed to construct the
# full email of the Google-managed Pub/Sub service account.
data "google_project" "project" {}


# -----------------------------------------------------------------------------
# Service Account for the POS Poller Service
# This account is used by the pos-poller Cloud Run service.
# -----------------------------------------------------------------------------
resource "google_service_account" "pos_poller_sa" {
  project      = var.gcp_project_id
  account_id   = "pos-poller-sa"
  display_name = "Service Account for POS Poller"
}

# --- Permissions for the Poller Service Account ---

# Allow the Poller to publish messages to the pos-events topic.
resource "google_pubsub_topic_iam_member" "poller_can_publish" {
  project = var.gcp_project_id
  topic   = google_pubsub_topic.pos_events_topic.name
  role    = "roles/pubsub.publisher"
  member  = google_service_account.pos_poller_sa.member
}

# Allow the Poller to access secrets from Secret Manager.
resource "google_project_iam_member" "poller_can_access_secrets" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = google_service_account.pos_poller_sa.member
}


# -----------------------------------------------------------------------------
# Service Account for the POS Processor Service
# This account is used by the pos-processor Cloud Run service.
# -----------------------------------------------------------------------------
resource "google_service_account" "pos_processor_sa" {
  project      = var.gcp_project_id
  account_id   = "pos-processor-sa"
  display_name = "Service Account for POS Processor"
}

# --- Permissions for the Processor Service Account ---

# Allow the Processor to write data into our BigQuery dataset.
resource "google_bigquery_dataset_iam_member" "processor_can_write_to_bq" {
  project    = var.gcp_project_id
  dataset_id = google_bigquery_dataset.pos_dataset.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_service_account.pos_processor_sa.member
}


# -----------------------------------------------------------------------------
# Permissions for Google Services
# -----------------------------------------------------------------------------

# Allow the Google-managed Pub/Sub service account to invoke our Cloud Run
# services. This is required for authenticated push subscriptions.
resource "google_project_iam_member" "pubsub_can_invoke_run" {
  project = var.gcp_project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}


# -----------------------------------------------------------------------------
# Service Account for CI/CD (GitHub Actions)
# This account is used by the GitHub Actions workflow to deploy the application.
# -----------------------------------------------------------------------------
resource "google_service_account" "github_actions_deployer_sa" {
  project      = var.gcp_project_id
  account_id   = "github-actions-deployer"
  display_name = "Service Account for GitHub Actions Deployer"
}

# --- Permissions for the Deployer Service Account ---

# Allow it to create and manage Cloud Builds
resource "google_project_iam_member" "deployer_can_edit_builds" {
  project = var.gcp_project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = google_service_account.github_actions_deployer_sa.member
}

# Allow it to write source code to the Cloud Build GCS bucket
resource "google_project_iam_member" "deployer_can_write_to_storage" {
  project = var.gcp_project_id
  # NOTE: Reverted to storage.admin. The more restrictive objectAdmin role was
  # insufficient for the 'gcloud builds submit' command's requirements.
  role    = "roles/storage.admin"
  member  = google_service_account.github_actions_deployer_sa.member
}

# Allow it to deploy and manage Cloud Run services
resource "google_project_iam_member" "deployer_can_admin_run" {
  project = var.gcp_project_id
  role    = "roles/run.admin"
  member  = google_service_account.github_actions_deployer_sa.member
}

# Allow the deployer to act as the runtime service accounts for Cloud Run.
# This is more secure than granting the iam.serviceAccountUser role at the project level.

# Allow the deployer SA to act as the pos-poller's runtime SA
resource "google_service_account_iam_member" "deployer_can_act_as_poller_sa" {
  service_account_id = google_service_account.pos_poller_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.github_actions_deployer_sa.member
}

# Allow the deployer SA to act as the pos-processor's runtime SA
resource "google_service_account_iam_member" "deployer_can_act_as_processor_sa" {
  service_account_id = google_service_account.pos_processor_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.github_actions_deployer_sa.member
}