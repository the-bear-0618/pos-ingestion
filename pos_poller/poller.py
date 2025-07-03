import os
import json
import logging
import hashlib
import re
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional, Tuple

from google.cloud import pubsub_v1, secretmanager
import requests
from requests.adapters import HTTPAdapter, Retry
from pos_poller.config import ODATA_ENDPOINTS, NUMERIC_FIELDS, STRING_FIELDS
from pos_poller.utils import parse_microsoft_date, to_snake_case

from functools import lru_cache
logger = logging.getLogger(__name__)

# --- Constants & Global Clients ---
API_PAGE_SIZE = 1000
API_TIMEOUT_SECONDS = 60
MAX_RETRIES = 3
BACKOFF_FACTOR = 1

http_session = requests.Session()
retries = Retry(total=MAX_RETRIES, backoff_factor=BACKOFF_FACTOR, status_forcelist=[500, 502, 503, 504])
http_session.mount('https://', HTTPAdapter(max_retries=retries))

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
TOPIC_ID = os.environ.get("TOPIC_ID")
API_BASE_URL = os.environ.get("API_BASE_URL")

IS_LOCAL_ENVIRONMENT = os.environ.get("PUBSUB_EMULATOR_HOST") is not None

# --- Core Functions ---

@lru_cache(maxsize=1)
def get_publisher_client() -> pubsub_v1.PublisherClient:
    """Returns a cached instance of the Pub/Sub PublisherClient."""
    return pubsub_v1.PublisherClient()

@lru_cache(maxsize=1)
def get_secret_manager_client() -> secretmanager.SecretManagerServiceClient:
    """Returns a cached instance of the SecretManagerServiceClient."""
    return secretmanager.SecretManagerServiceClient()

@lru_cache(maxsize=1)
def get_api_credentials() -> Tuple[Optional[str], Optional[str]]:
    """
    Fetches API credentials (Site ID and Access Token) either from environment
    variables (for local development) or from Google Secret Manager.
    This function is cached to prevent multiple lookups.
    """
    if IS_LOCAL_ENVIRONMENT:
        logger.info("Running in LOCAL environment, using secrets directly from env.")
        site_id = os.environ.get("SITE_ID")
        api_access_token = os.environ.get("API_ACCESS_TOKEN")
    else:
        logger.info("Running in CLOUD environment, fetching secrets from Secret Manager.")
        
        def get_secret(secret_id: str, version: str = "latest") -> Optional[str]:
            if not secret_id:
                return None
            secret_client = get_secret_manager_client()
            try:
                name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version}"
                response = secret_client.access_secret_version(request={"name": name})
                return response.payload.data.decode("UTF-8")
            except Exception as e:
                logger.error(f"Failed to access secret '{secret_id}': {e}")
                return None

        site_id = get_secret(os.environ.get("SITE_ID_SECRET_ID"))
        api_access_token = get_secret(os.environ.get("API_ACCESS_TOKEN_SECRET_ID"))

    if not site_id or not api_access_token:
        logger.critical("API credentials (Site ID or Access Token) could not be loaded. Service cannot function.")
        
    return site_id, api_access_token

def _convert_numeric_fields(record: Dict[str, Any]) -> Dict[str, Any]:
    """Iterates through a record and converts known numeric fields from string to number."""
    for key, value in record.items():
        if key in NUMERIC_FIELDS and isinstance(value, str):
            try:
                if '.' in value:
                    record[key] = float(value)
                else:
                    record[key] = int(value)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert string '{value}' to a number for key '{key}'.")
    return record

def _should_filter_field(key: str, value: Any) -> bool:
    """Determines if a field should be filtered out during transformation."""
    # 1. Filter out internal OData metadata fields and navigation properties.
    if key.startswith('__') or (isinstance(value, dict) and '__deferred' in value):
        return True
    
    # 2. NOTE: A previous, aggressive name-based filter for fields ending in '_id' or
    #    '_objectid' was removed. It was incorrectly stripping essential foreign key fields
    #    (like Site_ObjectId) from the records, causing downstream validation failures.
        
    # 3. Filter specific problematic fields that have type mismatches.
    if key in ('DeviceId', 'AreaId'):
        return True
        
    return False

def transform_odata_record(record: Dict[str, Any], entity_name: str) -> Dict[str, Any]:
    """
    Transforms an OData record by filtering unwanted fields, converting keys to
    snake_case, and normalizing data types for schema compliance.
    """
    # First, convert numeric strings to numbers. This is done on raw keys.
    record = _convert_numeric_fields(record)
    transformed = {}
    for key, value in record.items():
        if _should_filter_field(key, value):
            continue

        new_value = parse_microsoft_date(value)

        # First, handle empty/null-like strings by converting them to a proper NoneType.
        if new_value == "" or new_value == "null": 
            new_value = None

        # Now, enforce data types based on schema expectations.
        if key in STRING_FIELDS and new_value is not None:
            new_value = str(new_value)
        
        if key in NUMERIC_FIELDS and new_value is None:
            new_value = 0.0 # Coerce null numeric fields to 0.0
        
        new_key = to_snake_case(key)
        transformed[new_key] = new_value
    
    return transformed

def _create_pubsub_message_payload(record: dict, table_name: str, event_type: str, sync_id: str) -> dict:
    """Constructs the standardized message payload for Pub/Sub."""
    record_key = str(record.get('object_id') or record.get('id'))
    record_hash = hashlib.md5(record_key.encode()).hexdigest()[:12]
    return {
        'record_id': record_hash,
        'sync_id': sync_id,
        'event_type': event_type,
        'table_name': table_name,
        'data': record,
        'processed_at': datetime.now(timezone.utc).isoformat()
    }

def publish_records(records: List[Dict[str, Any]], endpoint_name: str, sync_id: str):
    publisher = get_publisher_client()
    topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)
    table_name = ODATA_ENDPOINTS[endpoint_name]['table_name']
    event_type = f"pos.{table_name.replace('pos_', '')}"
    publish_futures = []
    for record in records:
        transformed_record = transform_odata_record(record, endpoint_name)
        message_payload = _create_pubsub_message_payload(
            transformed_record, table_name, event_type, sync_id
        )
        # --- DEBUG: Log the exact payload being sent ---
        logger.info(f"PUBLISHING_PAYLOAD: {json.dumps(message_payload)}")
        message_bytes = json.dumps(message_payload).encode('utf-8')
        future = get_publisher_client().publish(topic_path, message_bytes)
        publish_futures.append(future)
    for future in publish_futures:
        future.result()

def fetch_odata_page(url: str, params: dict) -> List[Dict[str, Any]]:
    _, api_access_token = get_api_credentials()
    if not api_access_token:
        raise ValueError("API Access Token is not available to make requests.")
        
    headers = {'Authorization': f'AccessToken={api_access_token}', 'Accept': 'application/json'}
    req = requests.Request('GET', url, params=params, headers=headers)
    prepared = http_session.prepare_request(req)
    logger.info(f"Requesting URL: {prepared.url}")
    response = http_session.send(prepared, timeout=API_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json().get('d', [])

def _build_odata_params(endpoint_config: dict, site_id: str, target_date: Optional[datetime], skip: int) -> dict:
    """Builds the OData query parameters for a given request."""
    params = {'$top': API_PAGE_SIZE, '$skip': skip, '$orderby': 'Id', '$format': 'json'}
    filter_parts = []
    
    date_field = endpoint_config.get('date_field')
    if date_field and target_date:
        day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        filter_parts.append(f"{date_field} eq datetime'{day_start.strftime('%Y-%m-%dT00:00:00')}'")
    
    site_field = endpoint_config.get('site_field')
    if site_field and site_id:
        filter_parts.append(f"{site_field} eq guid'{site_id}'")
    
    if filter_parts:
        params['$filter'] = " and ".join(filter_parts)
        
    return params

def _sync_for_single_date(
    url: str,
    endpoint_name: str,
    endpoint_config: dict,
    site_id: str,
    target_date: Optional[datetime],
    sync_id: str,
) -> int:
    """Handles the pagination loop to fetch and publish records for a single date."""
    if target_date:
        logger.info(f"[{sync_id}] Processing date: {target_date.strftime('%Y-%m-%d')} (America/Chicago)")

    records_for_date = 0
    skip = 0
    has_more = True
    while has_more:
        params = _build_odata_params(endpoint_config, site_id, target_date, skip)
        try:
            records = fetch_odata_page(url, params)
            if records:
                publish_records(records, endpoint_name, sync_id)
                records_for_date += len(records)
                skip += API_PAGE_SIZE
                has_more = len(records) == API_PAGE_SIZE
            else:
                has_more = False
        except Exception as e:
            logger.error(f"[{sync_id}] Failed to process page for {endpoint_name}. Error: {e}")
            break  # Stop processing this date if a page fails
            
    if records_for_date == 0 and target_date:
        logger.info(f"[{sync_id}] Endpoint '{endpoint_name}' returned 0 records for date {target_date.strftime('%Y-%m-%d')}.")
    return records_for_date

def _get_date_range_for_sync(endpoint_config: dict, days_back: int) -> List[Optional[datetime]]:
    """
    Calculates the date range to process based on the endpoint configuration.
    Returns a list of datetime objects or a list with a single None if no date field is configured.
    """
    date_field = endpoint_config.get('date_field')
    if date_field:
        CHICAGO_TZ = ZoneInfo("America/Chicago")
        end_date = datetime.now(CHICAGO_TZ)
        return [end_date - timedelta(days=i) for i in range(days_back + 1)]
    else:
        return [None]

def sync_endpoint(endpoint_name: str, days_back: int) -> int:
    """Syncs an endpoint using the detailed configuration to build the correct filter."""
    sync_id = f"{endpoint_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    logger.info(f"[{sync_id}] Starting sync for {endpoint_name}")
    
    # Use .get() on the main dict to handle cases where an endpoint might be requested
    # but is not in our final configuration.
    endpoint_config = ODATA_ENDPOINTS.get(endpoint_name)
    if not endpoint_config:
        logger.error(f"No configuration found for endpoint '{endpoint_name}'. Skipping.")
        return 0

    site_id, _ = get_api_credentials()
    url = f"{API_BASE_URL}/{endpoint_name}"
    total_records = 0
    date_range_to_process = _get_date_range_for_sync(endpoint_config, days_back)

    for target_date in date_range_to_process:
        total_records += _sync_for_single_date(
            url, endpoint_name, endpoint_config, site_id, target_date, sync_id
        )
    
    logger.info(f"[{sync_id}] Completed sync for {endpoint_name}. Total records: {total_records}")
    return total_records