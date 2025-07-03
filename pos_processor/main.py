"""
Main Flask application for the POS Processor service.
"""
import os
import json
import base64
import logging
from datetime import datetime
from functools import lru_cache
from flask import Flask, request, Response

from google.cloud import bigquery
from pos_processor.schema_validator import validate_message
from pos_processor.config import NORMALIZATION_RULES

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
DATASET_ID = os.environ.get("BIGQUERY_DATASET_ID")

@lru_cache(maxsize=1)
def get_bigquery_client() -> bigquery.Client:
    """Returns a cached instance of the BigQuery client."""
    return bigquery.Client()

def normalize_record(record: dict, table_name: str) -> dict:
    """
    Normalizes record fields based on a predefined set of rules for the given table.
    """
    rules = NORMALIZATION_RULES.get(table_name, {})
    if not rules:
        return record  # No rules for this table, return original record.

    for field, target_format in rules.items():
        if field not in record:
            continue

        field_value = record.get(field)
        if not isinstance(field_value, str) or not field_value:
            continue  # Skip if not a non-empty string.

        try:
            dt_object = datetime.fromisoformat(field_value.replace('Z', '+00:00'))
            if target_format == "DATE":
                record[field] = dt_object.strftime('%Y-%m-%d')
            elif target_format == "DATETIME":
                record[field] = dt_object.isoformat(sep=' ')
        except (ValueError, TypeError):
            logger.warning(f"Could not parse timestamp for field '{field}' with value '{field_value}' in table '{table_name}'.")
    return record

def _prepare_record_for_insertion(message_data: dict) -> tuple[str, list]:
    """Prepares a record for BigQuery insertion by normalizing it."""
    table_id = message_data['table_name']
    record_to_insert = message_data['data']
    
    # Normalize the record based on predefined rules
    normalized_record = normalize_record(record_to_insert, table_id)
    
    return table_id, [normalized_record]

def _insert_into_bigquery(table_id: str, rows: list) -> list:
    """
    Inserts rows into the specified BigQuery table and returns a list of any errors.
    """
    full_table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_id}"
    bq_client = get_bigquery_client()
    errors = bq_client.insert_rows_json(full_table_id, rows)
    if not errors:
        logger.info(f"Successfully inserted {len(rows)} record(s) into {full_table_id}")
    return errors

def _process_message(message_data: dict) -> Response:
    """
    Handles the core logic of processing a single decoded Pub/Sub message.
    Returns a Flask Response object.
    """
    # --- 1. Schema Validation ---
    is_valid, error = validate_message(message_data)
    if not is_valid:
        record_id = message_data.get('record_id', 'N/A')
        table_name = message_data.get('table_name', 'N/A')
        error_log_data = {
            "message": "Schema validation failed",
            "record_id": record_id,
            "table_name": table_name,
            "validation_error": json.loads(error) if error.startswith('{') else error,
            "record_data": message_data.get('data')
        }
        logger.error(json.dumps(error_log_data, indent=2))
        # Acknowledge the message to prevent retries for invalid data.
        return Response(f"Validation failed for record_id {record_id}", status=200)

    # --- 2. Prepare for BigQuery Insertion ---
    table_id, rows_to_insert = _prepare_record_for_insertion(message_data)
    
    # --- 3. Optional Dry-Run Mode for safe testing ---
    if os.getenv("BQ_DRY_RUN", "false").lower() == "true":
        logger.info(f"[DRY-RUN] Would insert to {table_id}: {json.dumps(rows_to_insert)}")
        return Response(status=204)

    # --- 3. Insert into BigQuery ---
    logger.info(f"[DEBUG] Incoming table={table_id}, event_type={message_data.get('event_type')}")
    logger.info(f"[DEBUG] Insert payload preview: {json.dumps(rows_to_insert)[:500]}")
    logger.info(f"Attempting BigQuery insert to table {table_id} for sync_id={message_data.get('sync_id')} and record_id={message_data.get('record_id')}")

    errors = _insert_into_bigquery(table_id, rows_to_insert)

    if errors:
        logger.error(f"BigQuery insert failed for table {table_id}: {errors}")
        # TEMPORARILY acknowledge to prevent retry loop while debugging
        return Response("Insert failed but acknowledged", status=200)

    logger.info(f"Successfully inserted {len(rows_to_insert)} record(s) into table {table_id} (sync_id={message_data.get('sync_id')})")
    
    # Acknowledge the message successfully
    return Response(status=204)

def _decode_pubsub_message(envelope: dict) -> dict:
    """Decodes the base64 data from a Pub/Sub message envelope."""
    pubsub_message = envelope['message']
    message_data_str = base64.b64decode(pubsub_message['data']).decode('utf-8')
    return json.loads(message_data_str)

@app.route('/', methods=['POST'])
def handle_pubsub_message():
    """Endpoint to receive Pub/Sub push messages."""
    envelope = request.get_json()
    if not envelope or 'message' not in envelope:
        logger.warning("Received an empty or invalid envelope.")
        return Response("Bad Request: Invalid Pub/Sub message format", status=400)

    try:
        message_data = _decode_pubsub_message(envelope)
        # Delegate processing to the helper function
        return _process_message(message_data)

    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Error decoding Pub/Sub message data: {e}")
        # Acknowledge the message to prevent retries for malformed data
        return Response("Bad Request: Malformed message data", status=400)
    except Exception as e:
        logger.error(f"Unhandled error in message handler: {e}", exc_info=True)
        # Return a server error to trigger a Pub/Sub retry for transient issues
        return Response("Internal Server Error", status=500)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    is_debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=is_debug)