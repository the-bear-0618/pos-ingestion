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
    "Payments":            {"table_name": "pos_payments",            "date_field": "BusinessDate",                "site_field": None},
    "ItemSaleAdjustments": {"table_name": "pos_item_sale_adjustments", "date_field": "BusinessDate",      "site_field": "Site_ObjectId"},
    "ItemSaleTaxes":       {"table_name": "pos_item_sale_taxes",       "date_field": "BusinessDate",      "site_field": "Site_ObjectId"},
    "ItemSaleComponents":  {"table_name": "pos_item_sale_components",  "date_field": "BusinessDate",      "site_field": "Site_ObjectId"},
}

# This can be phased out by setting APPLY_FIELD_TRANSFORMATIONS to False
APPLY_FIELD_TRANSFORMATIONS = False
FIELD_TRANSFORMATIONS = {}

# A comprehensive set of all fields from all schemas that should be numeric.
# Moving this to config makes it easier to manage without changing application logic.
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