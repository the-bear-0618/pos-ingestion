import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import requests

# Import the functions we want to test
from pos_poller.poller import transform_odata_record, sync_endpoint
from pos_poller.utils import to_snake_case, parse_microsoft_date

# --- Unit Tests for Utility Functions ---

@pytest.mark.parametrize("input_name, expected_output", [
    ("PascalCase", "pascal_case"),
    ("camelCase", "camel_case"),
    ("already_snake", "already_snake"),
    ("AnObjectId", "an_object_id"),
    ("AnID", "an_id"),
    ("AmountUSD", "amount_usd"),
])
def test_to_snake_case(input_name, expected_output):
    """Tests the snake_case conversion logic."""
    assert to_snake_case(input_name) == expected_output

@pytest.mark.parametrize("input_date, expected_output_contains", [
    ("/Date(1672531200000)/", "2023-01-01T00:00:00+00:00"),
    ("not a date", "not a date"),
    (None, None),
])
def test_parse_microsoft_date(input_date, expected_output_contains):
    """Tests the Microsoft date parsing logic."""
    assert parse_microsoft_date(input_date) == expected_output_contains


# --- Unit Test for Transformation Logic ---

def test_transform_odata_record():
    """
    Tests the main record transformation function to ensure it correctly
    converts keys and parses dates without performing other data conversions.
    """
    # This is a sample raw record from the OData API
    raw_record = {
        "ObjectId": "36b492b3-d80e-4b5f-9ac6-35125a19fa0e",
        "BusinessDate": "/Date(1672531200000)/",
        "NetSales": "25.50",  # Note: This is a string, as the API provides it
        "__metadata": {"uri": "some-uri"}
    }
    
    # This is the expected output after minimal transformation
    expected_transformed_record = {
        "object_id": "36b492b3-d80e-4b5f-9ac6-35125a19fa0e",
        "business_date": "2023-01-01T00:00:00+00:00",
        "net_sales": 25.50 # The poller SHOULD convert this to a float
    }
    
    transformed = transform_odata_record(raw_record, "Checks")
    
    assert transformed == expected_transformed_record

# --- Integration-style Tests for the Main Sync Logic ---

@pytest.fixture
def mock_sync_dependencies():
    """A fixture to mock all external dependencies for sync_endpoint tests."""
    with patch('pos_poller.poller.get_api_credentials') as mock_get_creds, \
         patch('pos_poller.poller.publish_records') as mock_publish, \
         patch('pos_poller.poller.fetch_odata_page') as mock_fetch:
        
        # Set a default return value for credentials to be used by all tests.
        mock_get_creds.return_value = ('dummy_site_id', 'dummy_token')
        
        yield {
            "fetch": mock_fetch,
            "publish": mock_publish,
            "get_creds": mock_get_creds
        }

def test_sync_endpoint_single_page(mock_sync_dependencies):
    """
    Tests the sync_endpoint function for the simple case:
    - The API returns one page of data.
    - Ensures the data is fetched once and published once.
    """
    # --- Arrange ---
    mock_fetch = mock_sync_dependencies["fetch"]
    mock_publish = mock_sync_dependencies["publish"]
    # Configure the mock for fetch_odata_page.
    # When called, it will return a list with two records and indicate no more pages.
    sample_records = [{"Id": 1}, {"Id": 2}]
    
    # --- Act ---
    # Run the main sync function for a single endpoint.
    sync_endpoint('Checks', days_back=0)
    
    # --- Assert ---
    # Check that our mock fetch function was called exactly once.
    mock_fetch.assert_called_once()
    
    # Check that our mock publish function was called exactly once with the correct data.
    mock_publish.assert_called_once_with(sample_records, 'Checks', mock_publish.call_args[0][2]) # Arg 2 is the dynamic sync_id

def test_sync_endpoint_with_pagination(mock_sync_dependencies):
    """
    Tests that the sync_endpoint correctly handles pagination
    when the API indicates more data is available.
    """
    # --- Arrange ---
    mock_fetch = mock_sync_dependencies["fetch"]
    mock_publish = mock_sync_dependencies["publish"]
    # Configure the mock fetch to simulate multiple pages.
    # The first time it's called, it returns a full page of records.
    # The second time, it returns a smaller page, which signals the end of pagination.
    mock_fetch.side_effect = [
        [{"Id": i} for i in range(1000)],      # Page 1 (full page)
        [{"Id": i} for i in range(1000, 1050)]  # Page 2 (partial page)
    ]
    
    # --- Act ---

    sync_endpoint('ItemSales', days_back=0)
    
    # --- Assert ---
    # We expect fetch to be called twice (once for each page).
    assert mock_fetch.call_count == 2
    
    # We expect publish to be called twice as well.
    assert mock_publish.call_count == 2
    # Check that the second call to publish had the 50 records from the second page.
    assert len(mock_publish.call_args[0][0]) == 50

def test_sync_endpoint_api_error(mock_sync_dependencies):
    """
    Tests that if the API call fails, the process handles it gracefully
    and does not attempt to publish any data.
    """
    # --- Arrange ---
    mock_fetch = mock_sync_dependencies["fetch"]
    mock_publish = mock_sync_dependencies["publish"]
    # Configure the mock fetch function to raise an exception when called.
    mock_fetch.side_effect = requests.exceptions.RequestException("API is down")
    
    # --- Act ---
    # Run the sync function. The internal try/except should catch the error.
    sync_endpoint('Payments', days_back=0)
    
    # --- Assert ---
    # The fetch was attempted once.
    mock_fetch.assert_called_once()
    
    # CRUCIALLY, the publish function should never have been called.
    mock_publish.assert_not_called()