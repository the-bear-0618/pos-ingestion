import os
import json
import logging
import hashlib
import re
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional

from google.cloud import pubsub_v1, secretmanager
import requests
from requests.adapters import HTTPAdapter, Retry

from config import ODATA_ENDPOINTS
from utils import parse_microsoft_date, to_snake_case

logger = logging.getLogger(__name__)

# --- Constants & Global Clients ---
API_PAGE_SIZE = 1000
API_TIMEOUT_SECONDS = 60
MAX_RETRIES = 3
BACKOFF_FACTOR = 1

publisher = pubsub_v1.PublisherClient()
secret_client = secretmanager.SecretManagerServiceClient()

http_session = requests.Session()
retries = Retry(total=MAX_RETRIES, backoff_factor=BACKOFF_FACTOR, status_forcelist=[500, 502, 503, 504])
http_session.mount('https://', HTTPAdapter(max_retries=retries))

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
TOPIC_ID = os.environ.get("TOPIC_ID")
API_BASE_URL = os.environ.get("API_BASE_URL")

IS_LOCAL_ENVIRONMENT = os.environ.get("PUBSUB_EMULATOR_HOST") is not None

if IS_LOCAL_ENVIRONMENT:
    logger.info("Running in LOCAL environment, using secrets directly from .env file.")
    SITE_ID = os.environ.get("SITE_ID")
    API_ACCESS_TOKEN = os.environ.get("API_ACCESS_TOKEN")
else:
    logger.info("Running in CLOUD environment, fetching secrets from Secret Manager.")
    SITE_ID_SECRET_ID = os.environ.get("SITE_ID_SECRET_ID")
    API_ACCESS_TOKEN_SECRET_ID = os.environ.get("API_ACCESS_TOKEN_SECRET_ID")
    
    def get_secret(secret_id: str, version: str = "latest") -> str:
        name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version}"
        response = secret_client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")

    SITE_ID = get_secret(SITE_ID_SECRET_ID) if SITE_ID_SECRET_ID else None
    API_ACCESS_TOKEN = get_secret(API_ACCESS_TOKEN_SECRET_ID) if API_ACCESS_TOKEN_SECRET_ID else None

# --- Core Functions ---

def transform_odata_record(record: Dict[str, Any], entity_name: str) -> Dict[str, Any]:
    """
    Transforms OData record with a master list of all numeric fields
    that require string-to-number conversion.
    """
    # A comprehensive set of all fields from all schemas that should be numeric.
    NUMERIC_FIELDS = {
        'Id', 'PartyInfo_Id', 'CheckId', 'ItemSaleId', 'ItemExternalCode', 
        'AdjustedByUserExternalCode', 'AdjustmentReasonExternalCode', 'EmployeeNumber', 
        'EmployeeNumber2', 'JobNumber', 'ShiftNumber', 'LaborCategoryNumber',
        'UnPaidBreakCounts', 'UnPaidBreakMinutes', 'ExternalCode', 'PaymentNumber', 
        'CheckNumber', 'DaypartExternalCode', 'RevenueCenterExternalCode', 'TenderType', 
        'TenderOption', 'TransactionType', 'PlacementLocationTag',
        'CoverCount', 'GrossSales', 'NetSales', 'NonRevenueSales', 'Tax', 'Discounts', 
        'Comps', 'Surcharges', 'GrossAdjustments', 'NonGrossAdjustments', 'GiftCardsSold', 
        'DepositsReceived', 'DonationsReceived', 'CashCollected', 'CreditSalesCollected', 
        'CreditTipsCollected', 'AlternatePaymentsCollected', 'AlternateTipsCollected', 
        'MediaCollected', 'Paidouts', 'TaxCollected', 'TaxForgiven', 'TaxOwed', 
        'Gratuities', 'Voids', 'CheckGratuities', 'CheckTaxes', 'DepositSalesCollected', 
        'GiftCardSalesCollected', 'GiftCardTipsCollected',
        'BasePrice', 'Price', 'ExtendedPrice', 'NetPrice', 'CompAmount', 
        'PromoAmount', 'TaxAmount', 'VoidAmount', 'SurchargeAmount',
        'Quantity', 'AdjustmentAmount', 'Weight', 'TaxRate', 'AppliedAdjustmentAmount',
        'ExtendedAppliedAdjustmentAmount', 'Rate', 'Amount', 'Forgiven',
        'PaymentAmount', 'TotalAmount', 'TipAmount', 'AutoTipAmount', 'ChangeDue', 'TenderAmount',
        'HoursWorked', 'HourlyRate', 'RegularPayRate', 'TotalHours',
        'RegularHours', 'OvertimePayRate', 'OvertimeHours', 'OvertimeWages',
        'DoubletimeHours', 'DoubletimeWages', 'CreditCardTips', 'DeclaredTips',
        'Sales', 'RegularWages', 'TotalHoursUnrounded', 'RegularHoursUnrounded',
        'OvertimeHoursUnrounded', 'DoubletimeHoursUnrounded'
    }

    transformed = {}
    for key, value in record.items():
        if key.startswith('__') or (isinstance(value, dict) and '__deferred' in value):
            continue
        
        if key in NUMERIC_FIELDS and isinstance(value, str):
            try:
                if '.' in value:
                    value = float(value)
                else:
                    value = int(value)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert string '{value}' to a number for key '{key}'.")
        
        new_key = to_snake_case(key)
        value = parse_microsoft_date(value)
        
        if value == "" or value == "null": 
            value = None
            
        transformed[new_key] = value
    
    return transformed

def publish_records(records: List[Dict[str, Any]], endpoint_name: str, sync_id: str):
    topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)
    table_name = ODATA_ENDPOINTS[endpoint_name]['table_name']
    event_type = f"pos.{table_name.replace('pos_', '')}"
    publish_futures = []
    for record in records:
        transformed_record = transform_odata_record(record, endpoint_name)
        record_key = str(transformed_record.get('object_id') or transformed_record.get('id'))
        record_hash = hashlib.md5(record_key.encode()).hexdigest()[:12]
        message_payload = {
            'record_id': record_hash, 'sync_id': sync_id, 'event_type': event_type,
            'table_name': table_name, 'data': transformed_record,
            'processed_at': datetime.now(timezone.utc).isoformat()
        }
        message_bytes = json.dumps(message_payload).encode('utf-8')
        future = publisher.publish(topic_path, message_bytes)
        publish_futures.append(future)
    for future in publish_futures:
        future.result()

def fetch_odata_page(url: str, params: dict) -> List[Dict[str, Any]]:
    headers = {'Authorization': f'AccessToken={API_ACCESS_TOKEN}', 'Accept': 'application/json'}
    req = requests.Request('GET', url, params=params, headers=headers)
    prepared = http_session.prepare_request(req)
    response = http_session.send(prepared, timeout=API_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json().get('d', [])

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

    url = f"{API_BASE_URL}/{endpoint_name}"
    total_records = 0
    
    date_field = endpoint_config.get('date_field')
    if date_field:
        CHICAGO_TZ = ZoneInfo("America/Chicago")
        end_date = datetime.now(CHICAGO_TZ)
        date_range_to_process = [end_date - timedelta(days=i) for i in range(days_back + 1)]
    else:
        date_range_to_process = [None] 

    for target_date in date_range_to_process:
        if target_date:
            logger.info(f"[{sync_id}] Processing date: {target_date.strftime('%Y-%m-%d')} (America/Chicago)")
        
        skip = 0
        has_more = True
        while has_more:
            filter_parts = []
            site_field = endpoint_config.get('site_field')

            if date_field and target_date:
                day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                filter_parts.append(f"{date_field} eq datetime'{day_start.strftime('%Y-%m-%dT00:00:00')}'")
            
            if site_field and SITE_ID:
                filter_parts.append(f"{site_field} eq guid'{SITE_ID}'")

            params = {'$top': API_PAGE_SIZE, '$skip': skip, '$orderby': 'Id', '$format': 'json'}
            if filter_parts:
                params['$filter'] = " and ".join(filter_parts)

            try:
                records = fetch_odata_page(url, params)
                if records:
                    publish_records(records, endpoint_name, sync_id)
                    total_records += len(records)
                    skip += API_PAGE_SIZE
                    has_more = len(records) == API_PAGE_SIZE
                else:
                    has_more = False
            except Exception as e:
                logger.error(f"[{sync_id}] Failed to process page for {endpoint_name}. Error: {e}")
                break
    
    logger.info(f"[{sync_id}] Completed sync for {endpoint_name}. Total records: {total_records}")
    return total_records