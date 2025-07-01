#!/bin/bash
# This script configures the local Pub/Sub emulator with topics and subscriptions.

# Pub/Sub Emulator host
PUBSUB_EMULATOR_HOST="localhost:8085"

# Main topic for events
echo "Creating main topic: pos-events"
curl -X PUT "http://${PUBSUB_EMULATOR_HOST}/v1/projects/local-project/topics/pos-events"

# Dead-Letter Queue (DLQ) topic
echo "Creating DLQ topic: pos-events-dlq"
curl -X PUT "http://${PUBSUB_EMULATOR_HOST}/v1/projects/local-project/topics/pos-events-dlq"

# Push subscription for the processor service
echo "Creating push subscription: pos-processor-sub"
curl -X PUT "http://${PUBSUB_EMULATOR_HOST}/v1/projects/local-project/subscriptions/pos-processor-sub" \
  -H "Content-Type: application/json" \
  -d '{
        "topic": "projects/local-project/topics/pos-events",
        "pushConfig": {
          "pushEndpoint": "http://pos-processor:8080/"
        },
        "ackDeadlineSeconds": 60,
        "deadLetterPolicy": {
          "deadLetterTopic": "projects/local-project/topics/pos-events-dlq",
          "maxDeliveryAttempts": 5
        }
      }'

echo -e "\nLocal Pub/Sub setup complete."