import os
import json
import logging
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# --- CONFIGURE THIS SECTION ---
API_BASE_URL = "https://ecm-nsoeservices-bethpage.cbsnorthstar.com/reportservice/salesdata.svc"
API_ACCESS_TOKEN = "xxuIsr3vablQaroh23/hxXCWfgnx9E59vHeqdyVArYl1q1qx6u+Jx6w="
SITE_ID = "d8e9313b-7e54-4bb1-950b-8cadab263f13"
DAYS_TO_QUERY = 14

# --- FIX: Using a detailed map for entity sets and their specific fields ---
# We can now control which fields, if any, are used for filtering each endpoint.
ENDPOINTS_CONFIG = {
    "Customers":           {"entity_set": "Customers",           "date_field": None, "site_field": "Site_ObjectId"},
    "TimeRecords":         {"entity_set": "TimeRecords",         "date_field": None, "site_field": "Site_ObjectId"},
    "Paidouts":            {"entity_set": "Paidouts",            "date_field": None, "site_field": "Site_ObjectId"},
    "Payments":            {"entity_set": "Payments",            "date_field": "BusinessDate", "site_field": "Site_ObjectId"}, 
    "ItemSaleAdjustments": {"entity_set": "ItemSaleAdjustments", "date_field": "BusinessDate", "site_field": "Site_ObjectId"},
    "ItemSaleTaxes":       {"entity_set": "ItemSaleTaxes",       "date_field": "BusinessDate", "site_field": "Site_ObjectId"},
    "ItemSaleComponents":  {"entity_set": "ItemSaleComponents",  "date_field": None, "site_field": "Site_ObjectId"},
    "CheckGratuities":     {"entity_set": "CheckGratuities",     "date_field": None, "site_field": "Site_ObjectId"},
}
# --------------------------------

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def capture_data(endpoint_name: str, config: dict):
    """Fetches a few records from an endpoint and saves to a file."""
    logging.info(f"Attempting to capture data for endpoint: {endpoint_name}...")
    
    entity_set = config['entity_set']
    site_field = config.get('site_field')
    date_field = config.get('date_field')

    params = {'$top': 5, '$format': 'json'}
    filter_parts = []

    # Use a single day 'eq' filter for precision
    if date_field:
        # Looking back 2 days to have a better chance of finding data
        target_date = datetime.now(ZoneInfo("America/Chicago")) - timedelta(days=2)
        filter_parts.append(f"{date_field} eq datetime'{target_date.strftime('%Y-%m-%dT00:00:00')}'")
    
    if site_field and SITE_ID:
        filter_parts.append(f"{site_field} eq guid'{SITE_ID}'")
    
    if filter_parts:
        params['$filter'] = " and ".join(filter_parts)

    headers = {'Authorization': f'AccessToken={API_ACCESS_TOKEN}', 'Accept': 'application/json'}
    url = f"{API_BASE_URL}/{entity_set}"

    try:
        req = requests.Request('GET', url, params=params, headers=headers)
        prepared = req.prepare()
        logging.info(f"Requesting URL: {prepared.url}")

        response = requests.Session().send(prepared, timeout=60)
        response.raise_for_status()
        data = response.json().get('d', [])

        if not data:
            logging.warning(f"No records found for '{endpoint_name}'.")
            return

        os.makedirs("raw_api_output", exist_ok=True)
        output_path = f"raw_api_output/{endpoint_name}.json"
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logging.info(f"SUCCESS! Saved sample data for '{endpoint_name}' to {output_path}")

    except Exception as e:
        logging.error(f"FAILED to fetch data for '{endpoint_name}'. Error: {e}")

if __name__ == "__main__":
    if "your_actual" in API_ACCESS_TOKEN:
        logging.error("Please update the placeholder credentials at the top of the script before running.")
    else:
        for name, config in ENDPOINTS_CONFIG.items():
            capture_data(name, config)
        logging.info("\nData capture complete.")