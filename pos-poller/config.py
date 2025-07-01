"""
Central configuration for the POS Poller service.
Maps endpoints to their table names and specific filter fields.
"""
ODATA_ENDPOINTS = {
    "Checks":              {"table_name": "pos_checks",              "date_field": "BusinessDate",      "site_field": "Site_ObjectId"},
    "ItemSales":           {"table_name": "pos_item_sales",          "date_field": "BusinessDate",      "site_field": "Site_ObjectId"},
    "Customers":           {"table_name": "pos_customers",           "date_field": "ModifiedOn",        "site_field": "Site_ObjectId"},
    "TimeRecords":         {"table_name": "pos_time_records",        "date_field": "BusinessDate",      "site_field": "Site_ObjectId"},
    "Paidouts":            {"table_name": "pos_paidouts",            "date_field": "BusinessDate",      "site_field": "Site_ObjectId"},
    "Payments":            {"table_name": "pos_payments",            "date_field": None,                "site_field": None},
    "ItemSaleAdjustments": {"table_name": "pos_item_sale_adjustments", "date_field": "BusinessDate",      "site_field": "Site_ObjectId"},
    "ItemSaleTaxes":       {"table_name": "pos_item_sale_taxes",       "date_field": "BusinessDate",      "site_field": "Site_ObjectId"},
    "ItemSaleComponents":  {"table_name": "pos_item_sale_components",  "date_field": "BusinessDate",      "site_field": "Site_ObjectId"},
}

# This can be phased out by setting APPLY_FIELD_TRANSFORMATIONS to False
APPLY_FIELD_TRANSFORMATIONS = False
FIELD_TRANSFORMATIONS = {}