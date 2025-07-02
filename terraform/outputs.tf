# terraform/outputs.tf

output "github_actions_deployer_sa_email" {
  description = "The email of the service account for GitHub Actions to impersonate."
  value       = google_service_account.github_actions_deployer_sa.email
}

output "workload_identity_provider_name" {
  description = "The full name of the Workload Identity Provider for GitHub Actions."
  value       = google_iam_workload_identity_pool_provider.github_actions_provider.name
}