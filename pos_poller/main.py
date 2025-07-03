"""
Flask application entry point for the POS Poller service.
Handles HTTP requests and delegates to the poller logic.
"""
import os
import json
import logging
from datetime import datetime, timezone
from flask import Flask, request, jsonify, Response

# Import the core logic from our new poller module
from pos_poller.poller import sync_endpoint
from pos_poller.config import ODATA_ENDPOINTS

# Initialize Flask app and logging
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# --- Configuration Validation on Startup ---
# This will run once when the container starts to validate and log configuration.
logger.info("--- VALIDATING CONFIGURATION ON STARTUP ---")
is_local = os.environ.get("PUBSUB_EMULATOR_HOST") is not None

# Define required variables based on the environment
required_vars = ["GCP_PROJECT_ID", "TOPIC_ID", "API_BASE_URL"]
if is_local:
    required_vars.extend(["SITE_ID", "API_ACCESS_TOKEN"])
else:
    required_vars.extend(["SITE_ID_SECRET_ID", "API_ACCESS_TOKEN_SECRET_ID"])

# Check for the presence of each required variable and log its status
all_vars_found = True
for var in required_vars:
    if var in os.environ:
        logger.info(f"CONFIG: Found required environment variable '{var}'.")
    else:
        logger.error(f"CONFIG: MISSING required environment variable '{var}'.")
        all_vars_found = False

if all_vars_found:
    logger.info("--- CONFIGURATION VALIDATION SUCCESSFUL ---")
else:
    logger.critical("--- CONFIGURATION VALIDATION FAILED: Missing one or more required environment variables. ---")

@app.route('/', methods=['GET'])
def health_check() -> Response:
    """A simple health check endpoint to confirm the service is running."""
    return jsonify({
        'status': 'healthy',
        'service': 'pos-poller',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200

def _parse_and_validate_sync_request(request_data: dict) -> tuple[int, list, Response | None]:
    """
    Parses and validates the sync request payload.
    Returns (days_back, endpoints_to_sync, optional_error_response).
    """
    try:
        days_back = int(request_data.get('days_back', 7))
        if not 1 <= days_back <= 365:
            raise ValueError("days_back must be between 1 and 365.")
    except (ValueError, TypeError):
        logger.error(f"Invalid days_back value received: {request_data.get('days_back')}")
        error_response = jsonify({'error': 'days_back must be an integer between 1 and 365'}), 400
        return 0, [], error_response

    endpoints_req = request_data.get('endpoints', 'all')
    endpoints_to_sync = []

    if endpoints_req == 'all':
        endpoints_to_sync = sorted(list(ODATA_ENDPOINTS.keys()))
    elif isinstance(endpoints_req, list):
        valid_endpoints = set(ODATA_ENDPOINTS.keys())
        requested_endpoints = set(endpoints_req)
        endpoints_to_sync = sorted(list(valid_endpoints.intersection(requested_endpoints)))
        invalid_endpoints = sorted(list(requested_endpoints.difference(valid_endpoints)))
        if invalid_endpoints:
            logger.warning(f"Ignoring invalid endpoints in request: {invalid_endpoints}")
    else:
        logger.error(f"Invalid 'endpoints' format received: {type(endpoints_req)}")
        error_response = jsonify({'error': 'endpoints must be "all" or a list of strings'}), 400
        return 0, [], error_response
    
    return days_back, endpoints_to_sync, None

def _build_sync_summary(results: dict, endpoints_to_sync: list, errors: list) -> tuple[dict, int]:
    """Builds the final summary response for the sync operation."""
    status_code = 200 if not errors else 207
    summary = {
        'status': 'completed' if not errors else 'completed_with_errors',
        'results': results,
        'summary': {
            'total_valid_endpoints': len(endpoints_to_sync),
            'successful': len(endpoints_to_sync) - len(errors),
            'failed': len(errors)
        },
        'completed_at': datetime.now(timezone.utc).isoformat()
    }
    logger.info(f"Sync process finished. Summary: {json.dumps(summary)}")
    return summary, status_code

def _execute_sync_for_endpoints(endpoints_to_sync: list, days_back: int) -> tuple[dict, list]:
    """Iterates through endpoints, triggers sync, and collects results."""
    results = {}
    errors = []
    for endpoint in endpoints_to_sync:
        try:
            record_count = sync_endpoint(endpoint, days_back)
            # --- ADDED: Log the successful sync for this endpoint ---
            logger.info(
                f"Successfully processed endpoint '{endpoint}'. Published {record_count} records."
            )
            results[endpoint] = {'status': 'success', 'records_published': record_count}
        except Exception as e:
            logger.error(f"Sync failed for endpoint '{endpoint}': {e}", exc_info=True)
            results[endpoint] = {'status': 'error', 'message': str(e)}
            errors.append(endpoint)
    return results, errors

@app.route('/sync', methods=['POST'])
def sync() -> Response:
    """
    Main sync endpoint. Accepts a JSON payload to trigger a sync for
    specific endpoints and a given number of days.
    """
    try:
        request_data = request.get_json(silent=True) or {}
        logger.info(f"Sync request received. Payload: {json.dumps(request_data)}")

        days_back, endpoints_to_sync, error_response = _parse_and_validate_sync_request(request_data)
        if error_response:
            return error_response

        if not endpoints_to_sync:
            logger.warning("Request resulted in no valid endpoints to sync.")
            return jsonify({'status': 'completed', 'message': 'No valid endpoints were provided to sync.'}), 200

        logger.info(f"Validated endpoints to sync: {endpoints_to_sync}")

        results, errors = _execute_sync_for_endpoints(endpoints_to_sync, days_back)

        summary, status_code = _build_sync_summary(results, endpoints_to_sync, errors)
        return jsonify(summary), status_code

    except Exception as e:
        logger.error("A critical error occurred in the sync endpoint.", exc_info=True)
        return jsonify({'error': 'An unexpected server error occurred.', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    is_debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=is_debug)