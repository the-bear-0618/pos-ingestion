"""
Handles loading and validating messages against JSON schemas.
"""
import os
import json
import logging
from functools import lru_cache
from typing import Optional, Tuple
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_schema_store() -> dict:
    """
    Loads all JSON schemas from the 'schemas' directory into a store.
    """
    store = {}
    schema_dir_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'schemas'))
    logger.info(f"Attempting to load schemas from absolute path: {schema_dir_path}")
    try:
        filenames = os.listdir(schema_dir_path)
        logger.info(f"Found files in schema directory: {filenames}")
    except FileNotFoundError:
        logger.error(f"FATAL: Schema directory not found at {schema_dir_path}")
        return {}

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
    return store

def validate_message(message: dict) -> Tuple[bool, Optional[str]]:
    """
    Validates an incoming message against the appropriate JSON schema.
    """
    try:
        event_type = message.get('event_type')
        if not event_type:
            return False, "Message missing 'event_type' field."

        schema_name = f"https://schemas.crownpointrestaurant.com/pos/{event_type.replace('pos.', '')}.json"
        
        schema_store = get_schema_store()
        
        logger.info(f"Attempting to validate against schema ID: {schema_name}")

        if schema_name not in schema_store:
            return False, f"No schema found for event_type '{event_type}' (expected ID: {schema_name})"

        main_schema = schema_store[schema_name]
        
        # Create a registry of all known schemas, allowing for $ref resolution.
        registry = Registry().with_resources(
            (resource["$id"], Resource.from_contents(resource))
            for resource in schema_store.values()
        )
        
        validator = Draft202012Validator(main_schema, registry=registry)
        errors = sorted(validator.iter_errors(message), key=lambda e: e.path)

        if not errors:
            return True, None

        e = errors[0]
        error_path = "->".join(map(str, e.path)) if e.path else "root"
        error_message = f"Validation Error at '{error_path}': {e.message}"
        logger.warning(error_message)
        return False, error_message
    except Exception as e:
        logger.error(f"Unexpected validation error: {e}", exc_info=True)
        return False, "An unexpected error occurred during validation."