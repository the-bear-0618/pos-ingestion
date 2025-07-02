import pytest
import json
import base64
from unittest.mock import patch, MagicMock

# Import the Flask app object from your main application file
from pos_processor.main import app

# --- Pytest Fixtures ---
# Fixtures are reusable setup functions for your tests.

@pytest.fixture
def client():
    """A test client for the Flask app."""
    with app.test_client() as client:
        yield client

def create_pubsub_envelope(data: dict) -> dict:
    """Helper function to create a mock Pub/Sub push message envelope."""
    # Encode the data payload to base64, as Pub/Sub does
    message_data = base64.b64encode(json.dumps(data).encode('utf-8'))
    return {
        "message": {
            "data": message_data,
            "messageId": "test-message-id",
            "attributes": {}
        },
        "subscription": "test-subscription"
    }

# --- Test Cases ---

@patch('pos_processor.main.get_bigquery_client')
@patch('pos_processor.main.validate_message')
def test_success_flow(mock_validate_message, mock_get_bq_client, client):
    """
    Tests the "happy path": a valid message is received, validated,
    and successfully passed to BigQuery for insertion.
    """
    # --- Arrange ---
    # A valid data payload that matches checks_final.json
    valid_data = {
        "record_id": "a1b2c3d4e5f6",
        "sync_id": "Checks_20250630_120000",
        "event_type": "pos.checks",
        "table_name": "pos_checks",
        "processed_at": "2025-06-30T12:00:00Z",
        "data": {
            "id": 123,
            "object_id": "36b492b3-d80e-4b5f-9ac6-35125a19fa0e",
            "party_info_id": 456,
            "business_date": "2025-06-30",
            "net_sales": 100.50,
            "tax_owed": 8.50,
            "gratuities": 20.00,
            "owner_id": "99999999-9999-9999-9999-999999999999"
        }
    }
    
    # Mock the BigQuery client to simulate a successful insertion (returns no errors)
    mock_bq_client = mock_get_bq_client.return_value
    mock_bq_client.insert_rows_json.return_value = []
    
    # For this test, we assume schema validation passes.
    mock_validate_message.return_value = (True, None)

    # Create the full Pub/Sub message envelope
    envelope = create_pubsub_envelope(valid_data)

    # --- Act ---
    response = client.post('/', json=envelope)

    # --- Assert ---
    # 204 No Content is the correct success response for a Pub/Sub push ack.
    assert response.status_code == 204
    
    # Ensure the BigQuery client was called exactly once.
    mock_bq_client.insert_rows_json.assert_called_once()
    
    # Check that it was called with the correct table and row data.
    call_args = mock_bq_client.insert_rows_json.call_args
    assert "pos_checks" in call_args[0][0] # Check table name
    assert call_args[0][1] == [valid_data['data']] # Check row data

@patch('pos_processor.main.get_bigquery_client')
def test_schema_validation_failure(mock_get_bq_client, client):
    """
    Tests the failure path: an invalid message is received.
    It should be acknowledged (to go to the DLQ) and NOT sent to BigQuery.
    """
    # --- Arrange ---
    # This data is invalid because it's missing the required 'data' field.
    invalid_data = {
        "record_id": "a1b2c3d4e5f6",
        "sync_id": "Checks_20250630_120000",
        "event_type": "pos.checks",
        "table_name": "pos_checks",
        "processed_at": "2025-06-30T12:00:00Z"
        # "data" is missing
    }
    envelope = create_pubsub_envelope(invalid_data)

    # --- Act ---
    response = client.post('/', json=envelope)

    # --- Assert ---
    # The message is acknowledged with a 200 OK so Pub/Sub sends it to the DLQ.
    # It should NOT be a 5xx error, which would cause a retry.
    assert response.status_code == 200
    assert b"Validation failed" in response.data
    
    # CRUCIALLY, the BigQuery client should never be called.
    mock_get_bq_client.return_value.insert_rows_json.assert_not_called()

@patch('pos_processor.main.get_bigquery_client')
@patch('pos_processor.schema_validator.validate_message')
def test_bigquery_insertion_failure(mock_validate_message, mock_get_bq_client, client):
    """
    Tests the failure path: the message is valid, but the BigQuery API fails.
    The service should return a 5xx error to trigger a Pub/Sub retry.
    """
    # --- Arrange ---
    # We can use any valid data here.
    valid_data = {"event_type": "pos.checks", "table_name": "pos_checks", "data": {}}
    envelope = create_pubsub_envelope(valid_data)
    
    # We assume validation passes for this test.
    mock_validate_message.return_value = (True, None)

    # Mock the BigQuery client to simulate an insertion error.
    mock_bq_client = mock_get_bq_client.return_value
    mock_bq_client.insert_rows_json.return_value = [{'errors': ['BigQuery is unavailable']}]
    
    # --- Act ---
    response = client.post('/', json=envelope)
    
    # --- Assert ---
    # A 500 error tells Pub/Sub to retry delivering the message later.
    assert response.status_code == 500
    assert b"BigQuery insert failed" in response.data
    
    # The BigQuery client was still called.
    mock_bq_client.insert_rows_json.assert_called_once()

def test_malformed_pubsub_envelope(client):
    """
    Tests that the endpoint correctly handles a request that is not a valid
    Pub/Sub push message.
    """
    # --- Act ---
    # Send a request with an empty JSON body
    response = client.post('/', json={})
    
    # --- Assert ---
    # A 400 Bad Request should be returned.
    assert response.status_code == 400