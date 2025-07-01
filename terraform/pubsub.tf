# terraform/pubsub.tf

# 1. Main Pub/Sub topic where the poller sends all events.
resource "google_pubsub_topic" "pos_events_topic" {
  project = var.gcp_project_id
  name    = "pos-events"
}

# 2. Dead-Letter Queue (DLQ) topic for messages that fail processing.
resource "google_pubsub_topic" "pos_events_dlq_topic" {
  project = var.gcp_project_id
  name    = "pos-events-dlq"
}

# 3. Push subscription that connects the main topic to the processor service.
resource "google_pubsub_subscription" "pos_processor_subscription" {
  project = var.gcp_project_id
  name    = "pos-processor-sub"
  topic   = google_pubsub_topic.pos_events_topic.name

  # Acknowledge deadline: How long the processor has to process a message.
  ack_deadline_seconds = 60

  # This configures the subscription to send messages via HTTP POST
  # to the pos-processor Cloud Run service.
  push_config {
    # NOTE: This URL will be replaced later by the URL of your deployed
    # pos-processor Cloud Run service. We will define a service account for auth.
    push_endpoint = "https://placeholder-your-processor-url.a.run.app"
  }

  # This is the critical Dead-Letter Queue configuration.
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.pos_events_dlq_topic.id
    max_delivery_attempts = 5 # After 5 failed delivery attempts, send to DLQ.
  }

  depends_on = [
    google_pubsub_topic.pos_events_topic,
    google_pubsub_topic.pos_events_dlq_topic
  ]
}

# 4. (Optional but Recommended) A pull subscription for the DLQ topic.
# This makes it easy to inspect messages that have failed.
resource "google_pubsub_subscription" "pos_events_dlq_subscription" {
  project = var.gcp_project_id
  name    = "pos-events-dlq-pull-sub"
  topic   = google_pubsub_topic.pos_events_dlq_topic.name

  # Keep failed messages for the maximum duration.
  message_retention_duration = "604800s" # 7 days

  depends_on = [
    google_pubsub_topic.pos_events_dlq_topic
  ]
}