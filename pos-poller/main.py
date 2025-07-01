"""
Flask application entry point for the POS Poller service.
Handles HTTP requests and delegates to the poller logic.
"""
import os
import logging
from datetime import datetime, timezone
from flask import Flask, request, jsonify

# Import the core logic from our new poller module
from poller import sync_endpoint
from config import ODATA_ENDPOINTS

# Initialize Flask app and logging
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.route('/', methods=['GET'])
def health_check():
    """A simple health check endpoint to confirm the service is running."""
    return jsonify({
        'status': 'healthy',
        'service': 'pos-data-poller',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200

@app.route('/sync', methods=['POST'])
def sync():
    """
    Main sync endpoint. Accepts a JSON payload to trigger a sync for
    specific endpoints and a given number of days.
    """
    try:
        request_data = request.get_json() or {}
        days_back = int(request_data.get('days_back', 7))
        endpoints_req = request_data.get('endpoints', list(ODATA_ENDPOINTS.keys()))

        if not 1 <= days_back <= 365:
            return jsonify({'error': 'days_back must be an integer between 1 and 365'}), 400

        if isinstance(endpoints_req, list):
            endpoints_to_sync = [ep for ep in endpoints_req if ep in ODATA_ENDPOINTS]
        else:
            return jsonify({'error': 'endpoints must be a list of valid endpoint names'}), 400

        results = {}
        errors = []

        for endpoint in endpoints_to_sync:
            try:
                record_count = sync_endpoint(endpoint, days_back)
                results[endpoint] = {'status': 'success', 'records_published': record_count}
            except Exception as e:
                logger.error(f"Sync failed for endpoint '{endpoint}': {e}", exc_info=True)
                results[endpoint] = {'status': 'error', 'message': str(e)}
                errors.append(endpoint)

        status_code = 200 if not errors else 207  # 207 Multi-Status for partial success
        return jsonify({
            'status': 'completed' if not errors else 'completed_with_errors',
            'results': results,
            'summary': {
                'total_requested': len(endpoints_to_sync),
                'successful': len(endpoints_to_sync) - len(errors),
                'failed': len(errors)
            },
            'completed_at': datetime.now(timezone.utc).isoformat()
        }), status_code

    except Exception as e:
        logger.error("A critical error occurred in the sync endpoint.", exc_info=True)
        return jsonify({'error': 'An unexpected server error occurred.', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)