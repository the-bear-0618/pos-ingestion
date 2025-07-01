"""
Main Flask application for the POS Processor service.
"""
import os
import json
import base64
import logging
from flask import Flask, request

from google.cloud import bigquery
from schema_validator import validate_message

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize clients
app = Flask(__name__)
bigquery_client = bigquery.Client()
PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
DATASET_ID = os.environ.get("BIGQUERY_DATASET_ID")

@app.route('/', methods=['POST'])
def handle_pubsub_message():
    """Endpoint to receive Pub/Sub push messages."""
    envelope = request.get_json()
    if not envelope or 'message' not in envelope:
        logger.warning("Received an empty or invalid envelope.")
        return "Bad Request: Invalid Pub/Sub message format", 400

    try:
        # Decode the message data
        pubsub_message = envelope['message']
        message_data_str = base64.b64decode(pubsub_message['data']).decode('utf-8')
        message_data = json.loads(message_data_str)
        
        # --- 1. Schema Validation ---
        is_valid, error = validate_message(message_data)
        if not is_valid:
            logger.error(f"Schema validation failed for record_id {message_data.get('record_id')}: {error}")
            # Acknowledge the message to send it to the DLQ
            return f"Validation failed: {error}", 200

        # --- 2. Prepare for BigQuery Insertion ---
        table_id = message_data['table_name']
        record_to_insert = message_data['data']
        
        # BigQuery expects a list of rows
        rows_to_insert = [record_to_insert]
        full_table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_id}"
        
        # --- 3. Insert into BigQuery ---
        errors = bigquery_client.insert_rows_json(full_table_id, rows_to_insert)
        
        if errors:
            logger.error(f"BigQuery insert errors for {full_table_id}: {errors}")
            # Return a server error to trigger a Pub/Sub retry
            return "BigQuery insert failed", 500

        logger.info(f"Successfully inserted 1 record into {full_table_id}")
        # Acknowledge the message successfully
        return "Success", 204

    except Exception as e:
        logger.error(f"Unhandled error processing message: {e}", exc_info=True)
        # Return a server error to trigger a Pub/Sub retry
        return "Internal Server Error", 500

if __name__ == '__main__':
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)