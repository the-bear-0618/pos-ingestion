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
    A definitive, simple function to convert complex PascalCase and
    snake_case combinations into pure snake_case.
    e.g., 'Account_ObjectId' -> 'account_object_id'
    """
    # Add an underscore before any uppercase letter to break apart words
    # e.g., 'UserSession' -> 'User_Session'
    name = re.sub(r'(?<!^)(?=[A-Z])', '_', name)
    # Now, replace any existing underscores with a space, then convert the whole
    # string to lowercase and split it into a list of words.
    # e.g., 'Account_Object_Id' -> 'account object id' -> ['account', 'object', 'id']
    words = name.replace('_', ' ').lower().split()
    # Join the words back together with a single underscore.
    return '_'.join(words)