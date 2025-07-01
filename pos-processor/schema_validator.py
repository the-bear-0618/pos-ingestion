"""
Handles loading and validating messages against JSON schemas.
"""
import os
import json
import logging
from functools import lru_cache
from typing import Optional, Tuple
from jsonschema import validate, RefResolver, ValidationError

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_schema_store() -> Tuple[dict, str]:
    """
    Loads all JSON schemas from the 'schemas' directory into a store.
    """
    store = {}
    
    # --- THIS IS THE FIX ---
    # The path now correctly points directly to the 'schemas' directory, without 'v1'.
    schema_dir_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'schemas'))
    base_uri = f'file://{schema_dir_path}/'
    
    logger.info(f"Attempting to load schemas from absolute path: {schema_dir_path}")
    
    try:
        filenames = os.listdir(schema_dir_path)
        logger.info(f"Found files in schema directory: {filenames}")
    except FileNotFoundError:
        logger.error(f"FATAL: Schema directory not found at {schema_dir_path}")
        return {}, base_uri

    for filename in filenames:
        if filename.endswith('.json'):
            try:
                with open(os.path.join(schema_dir_path, filename), 'r') as f:
                    schema = json.load(f)
                    if '$id' in schema:
                        store[schema['$id']] = schema
                    else:
                        logger.warning(f"Schema file {filename} is missing a top-level '$id' property.")
            except Exception as e:
                logger.error(f"Failed to load or parse schema file {filename}: {e}")
    
    logger.info(f"SCHEMA STORE INITIALIZED. Contains IDs: {list(store.keys())}")
    
    return store, base_uri

def validate_message(message: dict) -> Tuple[bool, Optional[str]]:
    """
    Validates an incoming message against the appropriate JSON schema.
    """
    try:
        event_type = message.get('event_type')
        if not event_type:
            return False, "Message missing 'event_type' field."

        schema_name = f"https://schemas.crownpointrestaurant.com/pos/{event_type.replace('pos.', '')}.json"
        
        schema_store, base_uri = get_schema_store()
        
        logger.info(f"Attempting to validate against schema ID: {schema_name}")

        if schema_name not in schema_store:
            return False, f"No schema found for event_type '{event_type}' (expected ID: {schema_name})"

        schema_to_validate = schema_store[schema_name]
        
        resolver = RefResolver(base_uri=base_uri, referrer=schema_to_validate, store=schema_store)
        
        validate(instance=message, schema=schema_to_validate, resolver=resolver)
        
        return True, None

    except ValidationError as e:
        error_path = "->".join(map(str, e.path)) if e.path else "root"
        error_message = f"Validation Error at '{error_path}': {e.message}"
        logger.warning(error_message)
        return False, error_message
    except Exception as e:
        logger.error(f"Unexpected validation error: {e}", exc_info=True)
        return False, "An unexpected error occurred during validation."