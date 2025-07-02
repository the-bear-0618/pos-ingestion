"""
Central configuration for the POS Processor service.
"""

# A map defining how to normalize fields for specific tables.
# This provides a centralized and extensible way to handle data type transformations.
NORMALIZATION_RULES = {
    "pos_paidouts": {
        "business_date": "DATE"
    },
    "pos_time_records": {
        "business_date": "DATE",
        "in_time": "DATETIME",
        "out_time": "DATETIME",
        "modified_on": "DATETIME"
    }
    # Add other table-specific rules here as needed.
}