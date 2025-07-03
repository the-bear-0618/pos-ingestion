resource "google_bigquery_dataset" "pos_dataset" {
  project     = var.gcp_project_id
  dataset_id  = var.dataset_id
  location    = var.dataset_location
  description = "Dataset for Crown Point restaurant POS data"
}

locals {
  # Define all tables in a map to reduce repetition
  tables = {
    pos_checks = {
      schema_path     = "../schemas/checks.json"
      partition_field = "business_date"
    }
    pos_item_sales = {
      schema_path     = "../schemas/item_sales.json"
      partition_field = "business_date"
    }
    pos_time_records = {
      schema_path     = "../schemas/time_records.json"
      partition_field = "business_date"
    }
    pos_paidouts = {
      schema_path     = "../schemas/paidouts.json"
      partition_field = "business_date"
    }
    pos_customers = {
      schema_path = "../schemas/customers.json"
    }
    pos_payments = {
      schema_path = "../schemas/payments.json"
    }
    pos_item_sale_taxes = {
      schema_path = "../schemas/item_sale_taxes.json"
    }
    pos_item_sale_components = {
      schema_path = "../schemas/item_sale_components.json"
    }
    pos_item_sale_adjustments = {
      schema_path = "../schemas/item_sale_adjustments.json"
    }
  }
}

module "bigquery_tables" {
  source = "./modules/bigquery_table"

  for_each = local.tables

  project_id      = google_bigquery_dataset.pos_dataset.project
  dataset_id      = google_bigquery_dataset.pos_dataset.dataset_id
  table_id        = each.key
  schema_path     = each.value.schema_path
  partition_field = try(each.value.partition_field, null)
  type_overrides  = try(each.value.type_overrides, {})
}