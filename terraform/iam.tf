# terraform/iam.tf
#
# Defines all Service Accounts and IAM permissions for the project.

# Data block to get the Project Number, which is needed for some IAM bindings.
data "google_project" "project" {}


# -----------------------------------------------------------------------------
# Application Runtime Service Accounts
# -----------------------------------------------------------------------------

# Service Account for the POS Poller Service
resource "google_service_account" "pos_poller_sa" {
  project      = var.gcp_project_id
  account_id   = "pos-poller-sa"
  display_name = "Service Account for POS Poller"
}

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

# Service Account for the POS Processor Service
resource "google_service_account" "pos_processor_sa" {
  project      = var.gcp_project_id
  account_id   = "pos-processor-sa"
  display_name = "Service Account for POS Processor"
}

# Allow the Processor to write data into our BigQuery dataset.
resource "google_bigquery_dataset_iam_member" "processor_can_write_to_bq" {
  project    = var.gcp_project_id
  dataset_id = google_bigquery_dataset.pos_dataset.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_service_account.pos_processor_sa.member
}


# -----------------------------------------------------------------------------
# CI/CD Service Accounts & Permissions
# -----------------------------------------------------------------------------

# --- Workload Identity Federation (WIF) for GitHub Actions ---
# This allows GitHub Actions to authenticate to GCP without a long-lived key.

# 1. Create the Identity Pool
resource "google_iam_workload_identity_pool" "github_actions_pool" {
  project                   = var.gcp_project_id
  workload_identity_pool_id = "github-actions-pool"
  display_name              = "GitHub Actions Pool"
  description               = "Identity pool for GitHub Actions CI/CD"
}

# 2. Create the Pool Provider to trust GitHub's OIDC tokens
resource "google_iam_workload_identity_pool_provider" "github_actions_provider" {
  project                            = var.gcp_project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_actions_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub OIDC Provider"
  description                        = "Trusts OIDC tokens from GitHub"

  # Restrict this provider to only accept tokens from a specific repository.
  attribute_condition = "attribute.repository == 'the-bear-0618/pos-ingestion'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }
}

# Service Account for the GitHub Actions Deployer
resource "google_service_account" "github_actions_deployer_sa" {
  project      = var.gcp_project_id
  account_id   = "github-actions-deployer"
  display_name = "Service Account for GitHub Actions Deployer"
}

# Service Account for the Cloud Build job itself
# This SA performs the actual `docker build` and `docker push` steps.
resource "google_service_account" "manual_cloud_build_sa" {
  project      = var.gcp_project_id
  account_id   = "manual-cloud-build-sa"
  display_name = "Service Account for manual Cloud Build jobs"
}

# --- Permissions for the GitHub Actions Deployer SA ---

# Allow the Deployer to submit jobs to Cloud Build.
resource "google_project_iam_member" "deployer_can_edit_builds" {
  project = var.gcp_project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = google_service_account.github_actions_deployer_sa.member
}

# Allow the Deployer to upload source code to the Cloud Build GCS bucket.
# NOTE: `storage.admin` is highly permissive. A more secure alternative is to
# grant `roles/storage.objectAdmin` on the specific GCS bucket used by Cloud Build
# (e.g., `gs://<project_number>_cloudbuild/`).
resource "google_project_iam_member" "deployer_can_write_to_storage" {
  project = var.gcp_project_id
  role    = "roles/storage.admin"
  member  = google_service_account.github_actions_deployer_sa.member
}

# Allow the Deployer to deploy and manage Cloud Run services.
resource "google_project_iam_member" "deployer_can_admin_run" {
  project = var.gcp_project_id
  role    = "roles/run.admin"
  member  = google_service_account.github_actions_deployer_sa.member
}

# --- Permissions for the Cloud Build SA ---

# Allow the Cloud Build SA to push the built container images to Artifact Registry.
resource "google_project_iam_member" "build_sa_can_write_to_registry" {
  project = var.gcp_project_id
  role    = "roles/artifactregistry.writer"
  member  = google_service_account.manual_cloud_build_sa.member
}

# --- CI/CD Impersonation Permissions ("Act As") ---

# Allow the GitHub Actions WIF principal to impersonate the deployer SA.
# This is required for the `google-github-actions/auth` step to get a token.
resource "google_service_account_iam_member" "wif_can_create_tokens_for_deployer" {
  service_account_id = google_service_account.github_actions_deployer_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  # Bind to principals from a specific repository, as filtered by the provider's condition.
  # This is more flexible than hardcoding a specific branch in the subject.
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_actions_pool.name}/attribute.repository/the-bear-0618/pos-ingestion"

  # Explicitly depend on the pool and provider to avoid race conditions where
  # this resource is created before the pool is fully provisioned and recognized
  # by the IAM API.
  depends_on = [
    google_iam_workload_identity_pool_provider.github_actions_provider
  ]
}

# Allow the Deployer SA to act as the Cloud Build SA.
# This is required for the `gcloud builds submit --service-account=...` command.
resource "google_service_account_iam_member" "deployer_can_act_as_build_sa" {
  service_account_id = google_service_account.manual_cloud_build_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.github_actions_deployer_sa.member
}

# Allow the Deployer SA to act as the pos-poller's runtime SA during deployment.
resource "google_service_account_iam_member" "deployer_can_act_as_poller_sa" {
  service_account_id = google_service_account.pos_poller_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.github_actions_deployer_sa.member
}

# Allow the Deployer SA to act as the pos-processor's runtime SA during deployment.
resource "google_service_account_iam_member" "deployer_can_act_as_processor_sa" {
  service_account_id = google_service_account.pos_processor_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.github_actions_deployer_sa.member
}


# -----------------------------------------------------------------------------
# Permissions for Google-Managed Services
# -----------------------------------------------------------------------------

# Allow the Google-managed Pub/Sub service account to invoke our Cloud Run
# services. This is required for authenticated push subscriptions.
resource "google_project_iam_member" "pubsub_can_invoke_run" {
  project = var.gcp_project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# Allow the Google-managed Cloud Scheduler service account to use the poller's
# service account identity. This is required for the scheduler to invoke the
# poller Cloud Run service with the correct OIDC token.
resource "google_service_account_iam_member" "scheduler_can_use_poller_sa" {
  service_account_id = google_service_account.pos_poller_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-cloudscheduler.iam.gserviceaccount.com"
}
