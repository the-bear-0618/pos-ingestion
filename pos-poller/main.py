# pos-poller/main.py
"""
Flask application entry point for the POS Poller service.
Handles HTTP requests and delegates to the poller logic.
"""
import os
import json
import logging
from datetime import datetime, timezone
from flask import Flask, request, jsonify

# Import the core logic from our poller module
from poller import sync_endpoint
from config import ODATA_ENDPOINTS

# --- THIS IS THE CRITICAL LOGGING SETUP ---
# This simple configuration sends INFO level logs and above to standard output,
# which is what Cloud Run automatically captures and displays in Log Explorer.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)


@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint to confirm the service is up."""
    logger.info("Health check endpoint was called.")
    return jsonify({'status': 'healthy', 'service': 'pos-poller'}), 200


@app.route('/sync', methods=['POST'])
def sync():
    """Main sync endpoint, now with enhanced logging."""
    try:
        # Use silent=True to prevent crashes if the body isn't JSON
        request_data = request.get_json(silent=True) or {}

        # --- THIS IS THE NEW DEBUGGING LOG LINE ---
        # It will show us exactly what payload the service receives.
        logger.info(f"Sync request received. Payload: {json.dumps(request_data)}")

        days_back = int(request_data.get('days_back', 7))
        endpoints_req = request_data.get('endpoints', 'all')
        
        if not 1 <= days_back <= 365:
            logger.error(f"Invalid days_back value received: {days_back}")
            return jsonify({'error': 'days_back must be an integer between 1 and 365'}), 400
            
        if endpoints_req == 'all':
            endpoints_to_sync = list(ODATA_ENDPOINTS.keys())
        elif isinstance(endpoints_req, list):
            # Filter the requested list against our known endpoints
            endpoints_to_sync = [ep for ep in endpoints_req if ep in ODATA_ENDPOINTS]
            if len(endpoints_to_sync) != len(endpoints_req):
                 logger.warning(f"Some requested endpoints were invalid. Original: {endpoints_req}, Validated: {endpoints_to_sync}")
        else:
            logger.error(f"Invalid 'endpoints' format received: {type(endpoints_req)}")
            return jsonify({'error': 'endpoints must be "all" or a list of strings'}), 400
        
        logger.info(f"Validated endpoints to sync: {endpoints_to_sync}")
        
        results = {}
        errors = []
        
        # This part remains the same, calling your core logic
        for endpoint in endpoints_to_sync:
            try:
                record_count = sync_endpoint(endpoint, days_back)
                results[endpoint] = {'status': 'success', 'records_published': record_count}
            except Exception as e:
                logger.error(f"Sync failed for endpoint '{endpoint}': {e}", exc_info=True)
                results[endpoint] = {'status': 'error', 'message': str(e)}
                errors.append(endpoint)
        
        status_code = 200 if not errors else 207
        summary = {
            'status': 'completed' if not errors else 'completed_with_errors',
            'results': results,
            'summary': {
                'total_requested': len(endpoints_to_sync),
                'successful': len(endpoints_to_sync) - len(errors),
                'failed': len(errors)
            },
            'completed_at': datetime.now(timezone.utc).isoformat()
        }
        logger.info(f"Sync process finished. Summary: {json.dumps(summary)}")
        return jsonify(summary), status_code
        
    except Exception as e:
        logger.error("A critical error occurred in the sync endpoint.", exc_info=True)
        return jsonify({'error': 'An unexpected server error occurred.', 'message': str(e)}), 500


if __name__ == '__main__':
    # Gunicorn is used for production, but this allows direct execution for local testing
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)