import re
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def parse_microsoft_date(date_str: str) -> Optional[str]:
    """Parse Microsoft JSON date format /Date(1234567890000)/"""
    if isinstance(date_str, str) and date_str.startswith('/Date('):
        try:
            timestamp_ms = int(re.search(r'\d+', date_str).group())
            return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()
        except (AttributeError, ValueError) as e:
            logger.warning(f"Could not parse Microsoft date '{date_str}': {e}")
    return date_str

def to_snake_case(name: str) -> str:
    """
    Converts a string from PascalCase or camelCase to snake_case,
    correctly handling acronyms (e.g., 'AnID' -> 'an_id').
    """
    if not name:
        return ""
    # Insert underscores before uppercase letters, but not at the start.
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    # Handle cases like 'AmountUSD' -> 'Amount_USD'
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()